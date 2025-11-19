"""
RAG chain implementation.

Core orchestrator for RAG pipeline (embed → search → context → LLM).
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Any
from sqlalchemy.orm import Session
import logging
from functools import lru_cache

from app.embeddings.provider import EmbeddingsProvider
from app.vectorstore.faiss_store import VectorStore, VectorHit
from app.rag.context_builder import build_context
from app.rag.prompts import build_messages
from app.rag.image_analyzer import analyze_image, scan_image_comprehensively
from app.db import models
from app.chat.history import get_recent_messages
from app.config import get_settings
from app.utils.retry import retry_async
from pathlib import Path

logger = logging.getLogger(__name__)


class LlmClient(ABC):
    """Abstract interface for LLM calls."""
    
    @abstractmethod
    async def generate(self, messages: List[Dict[str, str]]) -> str:
        """
        Given chat messages, return the assistant response text.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
        
        Returns:
            Assistant response text as string
        """
        pass


class OpenAILlmClient(LlmClient):
    """OpenAI LLM client implementation."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        Initialize OpenAI LLM client.
        
        Args:
            api_key: OpenAI API key
            model: Model name (default: gpt-4o-mini)
        """
        self._api_key = api_key
        self._model = model
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self._api_key)
            except ImportError:
                raise ImportError("openai package not installed. Install with: pip install openai")
        return self._client
    
    async def generate(self, messages: List[Dict[str, str]]) -> str:
        """
        Generate a response from OpenAI chat completion API.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
        
        Returns:
            Assistant response text
        """
        client = self._get_client()
        
        async def _generate():
            import asyncio
            # OpenAI client is synchronous, so we need to run it in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model=self._model,
                    messages=messages,  # Already in correct format
                    temperature=0.8,  # Slightly higher for more natural, human-like responses
                    top_p=0.9  # Nucleus sampling for better quality
                )
            )
            return response.choices[0].message.content
        
        try:
            return await retry_async(_generate, max_retries=3, exceptions=(Exception,))
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            raise


class RagChain:
    """
    RAG chain orchestrator.
    
    Phase 6 spec: Full RAG pipeline from question to answer with citations.
    """
    
    def __init__(
        self,
        embeddings_provider: EmbeddingsProvider,
        vector_store: VectorStore,
        llm_client: LlmClient,
    ):
        """
        Initialize RAG chain with required providers.
        
        Args:
            embeddings_provider: Provider for generating embeddings
            vector_store: Vector store for similarity search
            llm_client: LLM client for generating responses
        """
        self._embeddings = embeddings_provider
        self._vector_store = vector_store
        self._llm = llm_client
    
    async def answer_question(
        self,
        db: Session,
        user: models.User,
        session: models.ChatSession,
        question: str,
        top_k: int = 10,
        exclude_message_id: int | None = None,
    ) -> Tuple[str, List[Dict], Dict[str, Any]]:
        """
        Run the full RAG pipeline:
        - Embed the user's question
        - Search the user's vector store for top-k chunks
        - Fetch corresponding DocumentChunk rows
        - Build context + citations
        - Fetch recent chat history for this session
        - Build LLM messages
        - Call LLM and get answer text
        - Return (answer, citations)
        
        Args:
            db: Database session
            user: User model instance
            session: Chat session model instance
            question: User's question string
            top_k: Number of top chunks to retrieve
            exclude_message_id: Optional message ID to exclude from history (prevents duplicating current question)
        
        Returns:
            Tuple of (answer_text, citations_list, analysis_info)
            analysis_info contains image analysis data if images were analyzed
        """
        # 1. Embed query
        logger.debug(f"Embedding query for user {user.id}, session {session.id}")
        query_vec = await self._embeddings.embed_query(question)
        logger.debug(f"Generated query embedding (dimension: {len(query_vec)})")
        
        # 2. Search vector store
        logger.debug(f"Searching vector store for user {user.id} with top_k={top_k}")
        hits = self._vector_store.search(
            user_id=user.id,
            query_vector=query_vec,
            k=top_k
        )
        logger.info(f"Found {len(hits)} relevant chunks for user {user.id}")
        
        if not hits:
            # If no chunks found but question is about images, try to find any image documents
            # Use same strict criteria as main image question detection
            is_image_question = any(keyword in question.lower() for keyword in [
                "image", "picture", "photo", "photograph", "screenshot", "gif", "animation",
                "describe the image", "describe the picture", "describe the photo", "describe the gif",
                "what's in the image", "what's in the picture", "what's in the photo", "what's in the gif",
                "what is in the image", "what is in the picture", "what is in the photo", "what is in the gif",
                "analyze the image", "analyze the picture", "analyze the photo", "analyze the gif"
            ])
            if is_image_question:
                logger.info(f"No chunks found, but image question detected. Searching for image documents...")
                # Try to find image documents even if not fully indexed
                # First, try to find documents with image chunks
                image_docs_with_chunks = (
                    db.query(models.Document)
                    .join(models.DocumentChunk)
                    .filter(
                        models.Document.user_id == user.id,
                        models.DocumentChunk.chunk_metadata.contains({"file_type": "image"})
                    )
                    .distinct()
                    .limit(3)
                    .all()
                )
                
                # Also find documents that are image files (by extension) even if no chunks yet
                image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.heic', '.heif', '.tiff', '.tif', '.svg', '.ico']
                image_docs_by_ext = (
                    db.query(models.Document)
                    .filter(
                        models.Document.user_id == user.id,
                        models.Document.status.in_([models.DocumentStatus.INDEXING, models.DocumentStatus.READY])
                    )
                    .all()
                )
                # Filter by extension
                image_docs_by_ext = [
                    doc for doc in image_docs_by_ext 
                    if any(doc.original_filename.lower().endswith(ext) for ext in image_extensions)
                ][:3]
                
                # Combine and deduplicate
                all_image_docs = {doc.id: doc for doc in image_docs_with_chunks}
                for doc in image_docs_by_ext:
                    if doc.id not in all_image_docs:
                        all_image_docs[doc.id] = doc
                
                image_docs = list(all_image_docs.values())[:3]
                
                if image_docs:
                    logger.info(f"Found {len(image_docs)} image documents, attempting BLIP-2 analysis")
                    try:
                        from app.rag.image_analyzer import get_blip2_analyzer
                        from app.config import get_settings
                        blip2 = get_blip2_analyzer()
                        settings = get_settings()
                        image_analyses = []
                        
                        for doc in image_docs:
                            # Try to reconstruct file path
                            file_path = None
                            # Check if we can find the file
                            storage_dir = Path(settings.storage_base_dir) / f"user_{user.id}" / "uploads"
                            if storage_dir.exists():
                                # Find file matching the document
                                for file in storage_dir.glob(f"*{doc.original_filename}"):
                                    file_path = file
                                    break
                            
                            if file_path and file_path.exists():
                                try:
                                    # Use lightweight comprehensive analysis
                                    logger.info(f"Performing lightweight image analysis for {doc.title}")
                                    deep_analysis = await scan_image_comprehensively(file_path)
                                    
                                    # Build comprehensive analysis text
                                    analysis_text = f"""=== Image Analysis: {doc.title} ===

Caption: {deep_analysis.get('basic_caption', 'N/A')}

Detailed Description: {deep_analysis.get('detailed_description', 'N/A')}

Detected Objects: {', '.join(deep_analysis.get('objects', [])) if deep_analysis.get('objects') else 'None detected'}

Detected Colors: {', '.join(deep_analysis.get('colors', [])) if deep_analysis.get('colors') else 'None detected'}

Scene Type: {deep_analysis.get('scene_type', 'Unknown')}

CLIP Embedding: Generated ({deep_analysis.get('clip_embedding_dim', 0)} dimensions)"""
                                    
                                    # If user asked a specific question, also get direct answer
                                    if "caption" not in question.lower() and "describe" not in question.lower() and "scan" not in question.lower():
                                        try:
                                            direct_answer = await blip2.answer_question_about_image(file_path, question)
                                            analysis_text += f"\n\nDirect Answer to Question '{question}': {direct_answer}"
                                        except Exception as e:
                                            logger.warning(f"Failed to get direct answer for question: {e}")
                                    
                                    image_analyses.append(analysis_text)
                                    logger.info(f"Generated deep CLIP + BLIP-2 analysis for image: {doc.title}")
                                except Exception as e:
                                    logger.warning(f"Deep analysis failed for {doc.title}, trying basic: {e}")
                                    # Fallback to basic
                                    try:
                                        if "caption" in question.lower() or "describe" in question.lower() or "scan" in question.lower():
                                            analysis = await blip2.generate_detailed_description(file_path)
                                        else:
                                            analysis = await blip2.answer_question_about_image(file_path, question)
                                        image_analyses.append(f"Image: {doc.title}\n{analysis}")
                                    except Exception as e2:
                                        logger.warning(f"Basic analysis also failed for {doc.title}: {e2}")
                        
                        if image_analyses:
                            context = "\n\n".join(image_analyses)
                            messages = build_messages(context=context, history=[], question=question)
                            answer = await self._llm.generate(messages)
                            # Return analysis info
                            analysis_info = {
                                "image_analyses": [{"analysis_text": analysis} for analysis in image_analyses],
                                "has_analysis": True
                            }
                            return answer, [], analysis_info
                    except Exception as e:
                        logger.warning(f"Error processing image documents: {e}, falling back to default response")
            
            logger.warning(f"No relevant chunks found for user {user.id}, question: {question[:50]}...")
            # Even without documents, we can still use the LLM to answer general questions
            # Fetch recent chat history for context
            history_messages = get_recent_messages(db, session, limit=10, exclude_message_id=exclude_message_id)
            logger.debug(f"Fetched {len(history_messages)} history messages for session {session.id} (no document context)")
            
            # Build messages without document context but with chat history
            messages = build_messages(context="", history=history_messages, question=question)
            logger.info(f"Calling LLM without document context for user {user.id}, session {session.id}")
            
            try:
                answer = await self._llm.generate(messages)
                logger.info(f"Generated answer ({len(answer)} chars) without document context for user {user.id}")
                # Add a note that this answer wasn't based on documents
                if not answer.strip().endswith(".") and not answer.strip().endswith("!") and not answer.strip().endswith("?"):
                    answer += "."
                answer = answer + " (Note: This response was generated without reference to your uploaded documents. Upload documents to get answers based on your content.)"
                return answer, [], {}
            except Exception as e:
                logger.error(f"Error generating LLM response without context: {e}", exc_info=True)
                return (
                    "I couldn't find any relevant information in your documents to answer this question. Please upload some documents or try asking a general question.",
                    [],
                    {}
                )
        
        # 3. Fetch chunks from DB
        chunk_ids = [h.chunk_id for h in hits]
        chunks: List[models.DocumentChunk] = (
            db.query(models.DocumentChunk)
            .filter(models.DocumentChunk.id.in_(chunk_ids))
            .join(models.Document)
            .filter(models.Document.user_id == user.id)
            .all()
        )
        
        if not chunks:
            logger.warning(f"Chunks not found in DB for user {user.id}, chunk_ids: {chunk_ids}")
            return (
                "I couldn't find any relevant information in your documents to answer this question.",
                [],
                {}
            )
        
        # 4. Build context and check for images
        logger.debug(f"Building context from {len(chunks)} chunks for user {user.id}")
        context, citations = build_context(db=db, chunks=chunks, hits=hits)
        logger.debug(f"Built context ({len(context)} chars) with {len(citations)} citations")
        
        # Check if any chunks are from images - check both metadata and text content
        image_chunks = [
            chunk for chunk in chunks 
            if chunk.chunk_metadata.get("file_type") == "image" 
            or "COMPREHENSIVE IMAGE SCAN" in chunk.text
            or "BLIP-2 Analysis" in chunk.text 
            or "BLIP-2 Caption" in chunk.text
            or "Image:" in chunk.text
        ]
        # Only trigger image analysis for EXPLICIT image questions (not generic "what is in" or "tell me about")
        # This prevents slow image analysis on every chat message
        is_image_question = any(keyword in question.lower() for keyword in [
            "image", "picture", "photo", "photograph", "screenshot", "gif", "animation",
            "caption", "describe the image", "describe the picture", "describe the photo", "describe the gif",
            "what's in the image", "what's in the picture", "what's in the photo", "what's in the gif",
            "what is in the image", "what is in the picture", "what is in the photo", "what is in the gif",
            "analyze the image", "analyze the picture", "analyze the photo", "analyze the gif",
            "scan the image", "scan the picture", "scan the photo", "scan the gif",
            "show me the image", "show me the picture", "show me the photo", "show me the gif",
            "what does the gif show", "what's happening in the gif", "what happens in the gif"
        ])
        
        # If we have image chunks and it's an EXPLICIT image question, perform REAL vision analysis
        if image_chunks and is_image_question:
            logger.info(f"Found {len(image_chunks)} image chunks - performing REAL vision analysis")
            
            # Use REAL analyze_image function (OpenAI → Local → Metadata fallback)
            try:
                from app.config import get_settings
                settings = get_settings()
                
                # Get the first image file path
                image_doc = None
                image_file_path = None
                
                for chunk in image_chunks[:1]:  # Use first image
                    doc = db.query(models.Document).filter(models.Document.id == chunk.document_id).first()
                    if doc and doc.original_filename:
                        # Try to find the file path
                        file_path_str = chunk.chunk_metadata.get("source_path")
                        if not file_path_str:
                            # Reconstruct path
                            storage_dir = Path(settings.storage_base_dir) / f"user_{user.id}" / "uploads"
                            if storage_dir.exists():
                                for file in storage_dir.glob(f"*{doc.original_filename}"):
                                    file_path_str = str(file)
                                    break
                        
                        if file_path_str:
                            file_path = Path(file_path_str)
                            if file_path.exists():
                                image_doc = doc
                                image_file_path = file_path
                                break
                
                if image_file_path and image_file_path.exists():
                    logger.info(f"Performing image analysis for {image_doc.title}")
                    try:
                        analysis = await analyze_image(
                            image_path=image_file_path,
                            question=question if is_image_question else None
                        )
                        analysis_source = analysis.get('analysis_source', 'Unknown')
                        model_used = analysis.get('model_used', 'N/A')
                        description = analysis.get('description', 'N/A')
                        caption = analysis.get('caption', 'N/A')
                        objects = analysis.get('objects', [])
                        colors = analysis.get('colors', [])
                        scene_type = analysis.get('scene_type', 'unknown')
                        mood = analysis.get('mood', [])
                        tags = analysis.get('tags', [])
                        
                        vision_text = f"""📸 IMAGE ANALYSIS ({analysis_source})

Image: {image_doc.title}
Model: {model_used}

DETAILED DESCRIPTION:
{description}

SHORT CAPTION:
{caption}

DETECTED OBJECTS:
{', '.join(objects) if objects else 'None detected'}

DETECTED COLORS:
{', '.join(colors) if colors else 'None detected'}

SCENE TYPE: {scene_type}

MOOD/ATMOSPHERE: {', '.join(mood) if mood else 'Not specified'}

TAGS: {', '.join(tags) if tags else 'None'}"""
                        
                        # Add vision analysis to context
                        context = f"{context}\n\n{vision_text}"
                        logger.info(f"Added image analysis to context for {image_doc.title}")
                        
                        # Store for return
                        if not hasattr(self, '_enhanced_analyses'):
                            self._enhanced_analyses = []
                        self._enhanced_analyses.append(vision_text)
                        
                    except Exception as e:
                        logger.error(f"Image analysis failed: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Image analysis setup failed: {e}", exc_info=True)
            
            has_comprehensive_scan = "COMPREHENSIVE IMAGE SCAN" in context or "IMAGE ANALYSIS" in context
            has_analysis = has_comprehensive_scan or "BLIP-2 Analysis" in context or "BLIP-2 Caption" in context
            
            if has_comprehensive_scan:
                logger.info(f"Context already contains image analysis")
            
            if is_image_question and "IMAGE ANALYSIS" not in context and not has_analysis:
                logger.info(f"Enhancing image context with image analysis")
                try:
                    settings = get_settings()  # Get settings for storage path
                    image_analyses = []
                    
                    for chunk in image_chunks[:1]:  # Only first image for speed
                        # Get document to find file path
                        doc = db.query(models.Document).filter(models.Document.id == chunk.document_id).first()
                        if doc and doc.original_filename:
                            # Try to find the file path from metadata or reconstruct it
                            file_path_str = chunk.chunk_metadata.get("source_path")
                            if not file_path_str:
                                # Try to reconstruct path from storage directory
                                storage_dir = Path(settings.storage_base_dir) / f"user_{user.id}" / "uploads"
                                if storage_dir.exists():
                                    for file in storage_dir.glob(f"*{doc.original_filename}"):
                                        file_path_str = str(file)
                                        break
                            
                            if file_path_str:
                                file_path = Path(file_path_str)
                                if file_path.exists():
                                    try:
                                        logger.info(f"Performing image analysis for {doc.title}")
                                        analysis = await analyze_image(
                                            image_path=file_path,
                                            question=question if is_image_question else None
                                        )
                                        
                                        analysis_source = analysis.get('analysis_source', 'Unknown')
                                        description = analysis.get('description', 'N/A')
                                        caption = analysis.get('caption', 'N/A')
                                        objects = analysis.get('objects', [])
                                        colors = analysis.get('colors', [])
                                        scene_type = analysis.get('scene_type', 'unknown')
                                        mood = analysis.get('mood', [])
                                        tags = analysis.get('tags', [])
                                        
                                        analysis_text = f"""📸 IMAGE ANALYSIS ({analysis_source})

Image: {doc.title}

DETAILED DESCRIPTION:
{description}

SHORT CAPTION: {caption}

DETECTED OBJECTS: {', '.join(objects) if objects else 'None detected'}

DETECTED COLORS: {', '.join(colors) if colors else 'None detected'}

SCENE TYPE: {scene_type}

MOOD/ATMOSPHERE: {', '.join(mood) if mood else 'Not specified'}

TAGS: {', '.join(tags) if tags else 'None'}"""
                                        
                                        image_analyses.append(analysis_text)
                                        logger.info(f"Added image analysis for {doc.title}")
                                    except Exception as e:
                                        logger.warning(f"REAL comprehensive analysis failed for {doc.title}: {e}")
                                else:
                                    # File not found, but we have stored analysis in chunk text
                                    if "BLIP-2" in chunk.text:
                                        logger.info(f"Using stored analysis from chunk for {doc.title}")
                                        image_analyses.append(f"=== Stored Image Analysis: {doc.title} ===\n{chunk.text}")
                    
                    if image_analyses:
                        enhanced_analysis_text = "\n\n".join(image_analyses)
                        context = f"{context}\n\n--- Enhanced Deep Image Analysis ---\n{enhanced_analysis_text}"
                        logger.info(f"Enhanced context with {len(image_analyses)} image analyses")
                        # Store enhanced analyses for return
                        if not hasattr(self, '_enhanced_analyses'):
                            self._enhanced_analyses = []
                        self._enhanced_analyses = image_analyses
                except Exception as e:
                    logger.warning(f"Image analysis enhancement failed: {e}, using existing context with stored analysis")
            elif has_analysis:
                logger.info(f"Context already contains BLIP-2/CLIP analysis, using stored analysis")
        
        # 5. Fetch recent chat history (excluding current user message if provided)
        history_messages = get_recent_messages(db, session, limit=10, exclude_message_id=exclude_message_id)
        logger.debug(f"Fetched {len(history_messages)} history messages for session {session.id} (excluded message_id: {exclude_message_id})")
        
        # 6. Build LLM messages
        messages = build_messages(
            context=context,
            history=history_messages,
            question=question
        )
        logger.debug(f"Built {len(messages)} messages for LLM call")
        
        # 7. Call LLM
        logger.info(f"Calling LLM for user {user.id}, session {session.id}")
        answer = await self._llm.generate(messages)
        logger.info(f"Generated answer ({len(answer)} chars) for user {user.id}")
        
        # 8. Collect image analysis info if images were analyzed
        analysis_info = {}
        
        if image_chunks:
            # Check if we have enhanced analyses from the enhancement section
            enhanced_analyses = getattr(self, '_enhanced_analyses', [])
            
            # Extract from stored chunks - prioritize comprehensive scan data
            stored_analyses = []
            for chunk in image_chunks[:3]:
                # Check if chunk contains comprehensive scan or analysis
                chunk_has_scan = "COMPREHENSIVE IMAGE SCAN" in chunk.text or "BLIP-2 Analysis" in chunk.text or "BLIP-2 Caption" in chunk.text or "CLIP Analysis" in chunk.text
                
                if chunk_has_scan:
                    doc = db.query(models.Document).filter(models.Document.id == chunk.document_id).first()
                    if doc:
                        # Use the full chunk text which contains the comprehensive scan
                        stored_analyses.append({
                            "document_title": doc.title,
                            "analysis_text": chunk.text,
                            "is_comprehensive_scan": "COMPREHENSIVE IMAGE SCAN" in chunk.text
                        })
                elif chunk.chunk_metadata.get("file_type") == "image":
                    # Even if analysis isn't in text, try to extract from context
                    doc = db.query(models.Document).filter(models.Document.id == chunk.document_id).first()
                    if doc and ("COMPREHENSIVE IMAGE SCAN" in context or "BLIP-2" in context):
                        # Extract relevant section from context
                        doc_title_in_context = f"Image: {doc.title}" in context or doc.title in context
                        if doc_title_in_context:
                            # Find the section in context related to this document
                            context_parts = context.split("\n\n")
                            relevant_parts = [part for part in context_parts if doc.title in part or "COMPREHENSIVE IMAGE SCAN" in part or "BLIP-2" in part]
                            if relevant_parts:
                                stored_analyses.append({
                                    "document_title": doc.title,
                                    "analysis_text": "\n\n".join(relevant_parts),
                                    "is_comprehensive_scan": "COMPREHENSIVE IMAGE SCAN" in "\n\n".join(relevant_parts)
                                })
            
            # Prefer comprehensive scans, then enhanced analyses, then stored analyses
            comprehensive_scans = [a for a in stored_analyses if a.get("is_comprehensive_scan")]
            if comprehensive_scans:
                analysis_info["image_analyses"] = comprehensive_scans
                analysis_info["has_analysis"] = True
                analysis_info["is_comprehensive_scan"] = True
            elif enhanced_analyses:
                analysis_info["image_analyses"] = [{"analysis_text": analysis} for analysis in enhanced_analyses]
                analysis_info["has_analysis"] = True
            elif stored_analyses:
                analysis_info["image_analyses"] = stored_analyses
                analysis_info["has_analysis"] = True
            
            # Clean up attribute
            if hasattr(self, '_enhanced_analyses'):
                delattr(self, '_enhanced_analyses')
        
        # 9. Return answer + citations + analysis_info
        return answer, citations, analysis_info


# DI helpers for FastAPI dependency injection
@lru_cache
def _build_llm_client() -> LlmClient:
    """
    Build LLM client instance (cached).
    
    Returns:
        LlmClient instance
    
    Raises:
        RuntimeError: If no LLM client is configured
    """
    settings = get_settings()
    
    # Check provider setting
    if settings.llm_provider == "groq":
        if not settings.groq_api_key:
            raise RuntimeError("Groq API key not configured. Set GROQ_API_KEY in .env")
        from app.rag.groq_client import GroqLlmClient
        return GroqLlmClient(
            api_key=settings.groq_api_key,
            model=settings.groq_model
        )
    elif settings.llm_provider == "local":
        if not settings.local_llm_base_url:
            raise RuntimeError("Local LLM base URL not configured. Set LOCAL_LLM_BASE_URL in .env")
        from app.rag.groq_client import LocalLlmClient
        return LocalLlmClient(
            base_url=settings.local_llm_base_url,
            model=settings.local_llm_model
        )
    elif settings.llm_provider == "openai" or settings.llm_provider == "default":
        if not settings.openai_api_key:
            raise RuntimeError("OpenAI API key not configured. Set OPENAI_API_KEY in .env")
        return OpenAILlmClient(
            api_key=settings.openai_api_key,
            model=settings.llm_model
        )
    else:
        # Default fallback: try OpenAI first, then Groq
        if settings.openai_api_key:
            return OpenAILlmClient(
                api_key=settings.openai_api_key,
                model=settings.llm_model
            )
        elif settings.groq_api_key:
            from app.rag.groq_client import GroqLlmClient
            return GroqLlmClient(
                api_key=settings.groq_api_key,
                model=settings.groq_model
            )
        raise RuntimeError("No LLM client configured. Set LLM_PROVIDER and corresponding API key in .env")


def get_llm_client() -> LlmClient:
    """
    FastAPI dependency to get LLM client.
    
    Returns:
        LlmClient instance (cached singleton)
    
    Raises:
        HTTPException: If LLM client cannot be configured
    """
    try:
        return _build_llm_client()
    except RuntimeError as e:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM client configuration error: {str(e)}"
        )

