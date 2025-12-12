# Chat API endpoints
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime
import json

from app.db.base import get_db
from app.db import models
from app.db.schemas import ChatSessionRead, ChatMessageRead
from app.auth.dependencies import get_current_user
from app.embeddings.provider import EmbeddingsProvider, get_embeddings_provider
from app.vectorstore.faiss_store import VectorStore, get_vector_store
from app.rag.chain import RagChain, LlmClient, get_llm_client
from app.chat.service import (
    create_chat_session,
    list_chat_sessions_for_user,
    get_chat_session_for_user,
    list_messages_for_session,
    get_all_chat_messages_for_user,
    delete_chat_session,
    delete_all_chat_history_for_user,
    handle_user_message,
)
from app.utils.cache import get_cached_result, set_cached_result, invalidate_user_cache, get_cache_stats
from app.rag.question_suggestions import generate_question_suggestions
from app.utils.query_analytics import record_query_metric
import time

router = APIRouter()


# Request models
class ChatSessionCreate(BaseModel):
    title: str | None = None


class ChatMessageCreate(BaseModel):
    content: str


@router.post("/sessions", response_model=ChatSessionRead, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Create a new chat session.
    
    Args:
        payload: ChatSessionCreate with optional title
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        ChatSessionRead with created session details
    """
    session = create_chat_session(db, current_user, title=payload.title)
    return ChatSessionRead.model_validate(session)


@router.get("/sessions", response_model=List[ChatSessionRead])
def list_sessions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    List all chat sessions for the current user.
    
    Args:
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        List of ChatSessionRead schemas
    """
    sessions = list_chat_sessions_for_user(db, current_user)
    return [ChatSessionRead.model_validate(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=List[ChatMessageRead])
def get_session_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get all messages for a specific chat session.
    
    Args:
        session_id: Chat session ID
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        List of ChatMessageRead schemas
    
    Raises:
        HTTPException: 404 if session not found or not owned by user
    """
    messages = list_messages_for_session(db, current_user, session_id)
    return [ChatMessageRead.model_validate(m) for m in messages]


@router.patch("/sessions/{session_id}/title", response_model=ChatSessionRead)
def update_session_title(
    session_id: int,
    title: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Update the title of a chat session.
    
    Args:
        session_id: Chat session ID
        title: New title for the session
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        Updated ChatSessionRead
    
    Raises:
        HTTPException: 404 if session not found or not owned by user
    """
    from app.chat.service import get_chat_session_for_user
    session = get_chat_session_for_user(db, current_user, session_id)
    session.title = title
    db.commit()
    db.refresh(session)
    return ChatSessionRead.model_validate(session)


@router.get("/messages/all", response_model=List[ChatMessageRead])
def get_all_messages(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get all chat messages across all sessions for the current user.
    
    This endpoint returns all messages from all chat sessions, ordered chronologically.
    
    Args:
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        List of ChatMessageRead schemas from all sessions
    """
    messages = get_all_chat_messages_for_user(db, current_user)
    return [ChatMessageRead.model_validate(m) for m in messages]


@router.delete("/sessions/all")
def delete_all_chat_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Delete all chat history (sessions and messages) for the current user.
    
    WARNING: This action cannot be undone. All chat sessions and messages will be permanently deleted.
    
    Args:
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        Dictionary with deletion summary
    """
    result = delete_all_chat_history_for_user(db, current_user)
    return result


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Delete a specific chat session and all its messages.
    
    Args:
        session_id: Chat session ID to delete
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        Dictionary with deletion summary
    
    Raises:
        HTTPException: 404 if session not found or not owned by user
    """
    result = delete_chat_session(db, current_user, session_id)
    return result


@router.post(
    "/sessions/{session_id}/message",
    response_model=ChatMessageRead,
)
async def send_message(
    session_id: int,
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    embeddings_provider: EmbeddingsProvider = Depends(get_embeddings_provider),
    vector_store: VectorStore = Depends(get_vector_store),
    llm_client: LlmClient = Depends(get_llm_client),
):
    """
    Send a message to a chat session and get a RAG-powered response.
    
    This endpoint:
    1. Creates a user message in the session
    2. Runs the RAG pipeline to generate an answer
    3. Creates an assistant message with the answer and citations
    4. Returns the assistant message
    
    Args:
        session_id: Chat session ID
        payload: ChatMessageCreate with message content
        db: Database session
        current_user: Current authenticated user
        embeddings_provider: Embeddings provider instance
        vector_store: Vector store instance
        llm_client: LLM client instance
    
    Returns:
        ChatMessageRead with assistant response and citations
    
    Raises:
        HTTPException: 404 if session not found or not owned by user
    """
    import logging
    import asyncio
    logger = logging.getLogger(__name__)
    
    # Validate input
    if not payload.content or not payload.content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty"
        )
    
    try:
        # Create RAG chain
        rag_chain = RagChain(
            embeddings_provider=embeddings_provider,
            vector_store=vector_store,
            llm_client=llm_client,
        )
        
        # Check cache first (only for non-image questions)
        question_lower = payload.content.lower()
        is_image_question = any(keyword in question_lower for keyword in [
            "image", "picture", "photo", "describe", "analyze", "what's in", "gif"
        ])
        
        cached_result = None
        start_time = time.time()
        if not is_image_question:
            cached_result = get_cached_result(payload.content.strip(), current_user.id, top_k=10, ttl=3600)
            if cached_result:
                logger.info(f"Returning cached result for user {current_user.id}")
                _, assistant_msg, _, analysis_info = cached_result
                
                # Record cached query metric
                latency_ms = (time.time() - start_time) * 1000
                token_count = len(payload.content) // 4 + len(assistant_msg.content) // 4
                # Get citations from cached result
                _, _, citations_from_cache, _ = cached_result
                citations_list = citations_from_cache if citations_from_cache else []
                
                record_query_metric(
                    user_id=current_user.id,
                    session_id=session_id,
                    query=payload.content.strip(),
                    latency_ms=latency_ms,
                    token_count=token_count,
                    cache_hit=True,
                    strategy="cached",
                    confidence_score=analysis_info.get("confidence_score") if isinstance(analysis_info, dict) else None,
                    num_citations=len(citations_list),
                )
                
                # Return cached response
                response = ChatMessageRead.model_validate(assistant_msg)
                if analysis_info and isinstance(analysis_info, dict) and "confidence_score" in analysis_info:
                    response_dict = response.model_dump()
                    response_dict["confidence_score"] = analysis_info["confidence_score"]
                    return ChatMessageRead(**response_dict)
                return response
        
        # Handle user message through RAG pipeline with timeout
        analysis_info = {}
        start_time = time.time()
        strategy = "default"  # Track which RAG strategy was used
        
        try:
            # Determine strategy based on settings
            from app.config import get_settings
            settings = get_settings()
            if settings.enable_hybrid_search and settings.enable_reranking:
                strategy = "hybrid_reranked"
            elif settings.enable_hybrid_search:
                strategy = "hybrid"
            elif settings.enable_reranking:
                strategy = "reranked"
            else:
                strategy = "vector_only"
            
            result = await asyncio.wait_for(
                handle_user_message(
                    db=db,
                    user=current_user,
                    session_id=session_id,
                    question=payload.content.strip(),
                    rag_chain=rag_chain,
                ),
                timeout=60.0  # 60 second timeout for RAG processing
            )
            _, assistant_msg, _, analysis_info = result
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Estimate token count (rough approximation: ~4 chars per token)
            token_count = len(payload.content) // 4 + len(assistant_msg.content) // 4
            
            # Record query metric
            citations_list = analysis_info.get("citations", []) if isinstance(analysis_info, dict) else []
            if not citations_list and isinstance(analysis_info, dict):
                # Try to get citations from the result tuple
                _, _, citations_from_result, _ = result
                citations_list = citations_from_result if citations_from_result else []
            
            record_query_metric(
                user_id=current_user.id,
                session_id=session_id,
                query=payload.content.strip(),
                latency_ms=latency_ms,
                token_count=token_count,
                cache_hit=False,  # This is a fresh query (not cached)
                strategy=strategy,
                confidence_score=analysis_info.get("confidence_score") if isinstance(analysis_info, dict) else None,
                num_citations=len(citations_list),
            )
            
            # Cache the result (only for non-image questions)
            if not is_image_question:
                set_cached_result(payload.content.strip(), current_user.id, result)
        except asyncio.TimeoutError:
            logger.error(f"RAG processing timed out for session {session_id}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Request timed out. The question may be too complex or the system is busy. Please try again with a simpler question."
            )
        
        # Validate response
        if not assistant_msg or not assistant_msg.content:
            logger.error(f"Empty assistant message returned for session {session_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate response"
            )
        
        # Create response with confidence score from analysis_info
        response = ChatMessageRead.model_validate(assistant_msg)
        # Add confidence score if available (will be in response metadata for frontend)
        if analysis_info and isinstance(analysis_info, dict) and "confidence_score" in analysis_info:
            # Store in a way that frontend can access
            # For now, we'll add it as a custom attribute (Pydantic allows this)
            response_dict = response.model_dump()
            response_dict["confidence_score"] = analysis_info["confidence_score"]
            return ChatMessageRead(**response_dict)
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions (they already have proper responses)
        raise
    except asyncio.TimeoutError:
        # Timeout errors should already be caught above, but catch here as well
        logger.error(f"Timeout in send_message endpoint for session {session_id}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again with a simpler question."
        )
    except RuntimeError as e:
        # RuntimeError usually means missing configuration (API keys, etc.)
        logger.error(f"Configuration error in send_message endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Configuration error: {str(e)}. Please check your .env file and ensure API keys are set."
        )
    except Exception as e:
        # Catch-all for any other exceptions - ensure we always return a response
        logger.error(f"Unexpected error in send_message endpoint: {e}", exc_info=True)
        error_msg = str(e)
        if len(error_msg) > 200:
            error_msg = error_msg[:200] + "..."
        # Always return a proper HTTP response, never let connection close empty
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {error_msg}"
        )


@router.post("/sessions/{session_id}/message/stream")
async def send_message_stream(
    session_id: int,
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    embeddings_provider: EmbeddingsProvider = Depends(get_embeddings_provider),
    vector_store: VectorStore = Depends(get_vector_store),
    llm_client: LlmClient = Depends(get_llm_client),
):
    """
    Send a message to a chat session and get a streaming RAG-powered response.
    
    This endpoint streams the LLM response in real-time as tokens are generated.
    The response format is Server-Sent Events (SSE) with JSON chunks.
    
    Args:
        session_id: Chat session ID
        payload: ChatMessageCreate with message content
        db: Database session
        current_user: Current authenticated user
        embeddings_provider: Embeddings provider instance
        vector_store: Vector store instance
        llm_client: LLM client instance
    
    Returns:
        StreamingResponse with SSE format
    
    Raises:
        HTTPException: 404 if session not found or not owned by user
    """
    import logging
    import asyncio
    logger = logging.getLogger(__name__)
    
    # Validate input
    if not payload.content or not payload.content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty"
        )
    
    async def generate_stream():
        try:
            # Verify session
            from app.chat.service import get_chat_session_for_user
            session = get_chat_session_for_user(db, current_user, session_id)
            
            # Create user message
            user_msg = models.ChatMessage(
                session_id=session.id,
                role=models.ChatRole.USER,
                content=payload.content.strip(),
                created_at=datetime.utcnow()
            )
            db.add(user_msg)
            db.commit()
            db.refresh(user_msg)
            
            # Create RAG chain
            rag_chain = RagChain(
                embeddings_provider=embeddings_provider,
                vector_store=vector_store,
                llm_client=llm_client,
            )
            
            # Run RAG pipeline to get context (without LLM call)
            try:
                context, citations, analysis_info = await asyncio.wait_for(
                    rag_chain.get_context_for_question(
                        db=db,
                        user=current_user,
                        session=session,
                        question=payload.content.strip(),
                        top_k=10,
                        exclude_message_id=user_msg.id,
                    ),
                    timeout=60.0
                )
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'type': 'error', 'content': 'Request timed out. Please try again.'})}\n\n"
                return
            
            # Build messages for LLM
            from app.chat.history import get_recent_messages
            from app.rag.prompts import build_messages
            history = get_recent_messages(db, session, limit=10, exclude_message_id=user_msg.id)
            messages = build_messages(context=context, history=history, question=payload.content.strip())
            
            # Stream LLM response
            full_response = ""
            async for chunk in llm_client.stream(messages):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
            
            # Calculate confidence score for streaming response
            from app.rag.confidence import calculate_confidence_score
            from app.vectorstore.faiss_store import VectorHit
            
            # Create dummy hits for confidence calculation (we don't have hits in streaming)
            dummy_hits = [VectorHit(chunk_id=c.get('chunk_id', 0), score=0.5) for c in citations if isinstance(c, dict)]
            confidence = calculate_confidence_score(dummy_hits, citations, full_response, payload.content.strip())
            
            # Save assistant message
            assistant_msg = models.ChatMessage(
                session_id=session.id,
                role=models.ChatRole.ASSISTANT,
                content=full_response,
                retrieved_chunks=citations,
                created_at=datetime.utcnow()
            )
            db.add(assistant_msg)
            db.commit()
            
            # Send final message with citations and confidence
            yield f"data: {json.dumps({'type': 'done', 'citations': citations, 'message_id': assistant_msg.id, 'confidence_score': confidence})}\n\n"
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in streaming endpoint: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
    
    from datetime import datetime
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("/sessions/{session_id}/suggestions")
async def get_question_suggestions(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get AI-generated question suggestions based on conversation history.
    
    Args:
        session_id: Chat session ID
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        List of suggested questions
    """
    from app.chat.service import get_chat_session_for_user, list_messages_for_session
    
    session = get_chat_session_for_user(db, current_user, session_id)
    messages = list_messages_for_session(db, current_user, session_id)
    
    if not messages:
        return {"suggestions": []}
    
    # Build conversation history
    conversation_history = [
        {"role": msg.role.value if hasattr(msg.role, 'value') else str(msg.role), "content": msg.content}
        for msg in messages[-10:]  # Last 10 messages for context
    ]
    
    # Get last assistant message
    last_answer = ""
    for msg in reversed(messages):
        if msg.role == models.ChatRole.ASSISTANT or (hasattr(msg.role, 'value') and msg.role.value == "assistant"):
            last_answer = msg.content
            break
    
    if not last_answer:
        return {"suggestions": []}
    
    # Generate suggestions
    try:
        suggestions = await generate_question_suggestions(
            conversation_history=conversation_history,
            last_answer=last_answer,
            max_suggestions=5
        )
        return {"suggestions": suggestions}
    except Exception as e:
        logger.error(f"Failed to generate suggestions: {e}", exc_info=True)
        return {"suggestions": []}


@router.get("/sessions/{session_id}/export")
async def export_conversation(
    session_id: int,
    format: str = "markdown",  # "markdown" or "pdf"
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Export a conversation as Markdown or PDF.
    
    Args:
        session_id: Chat session ID
        format: Export format ("markdown" or "pdf")
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        Exported conversation file
    """
    from app.chat.service import get_chat_session_for_user, list_messages_for_session
    
    session = get_chat_session_for_user(db, current_user, session_id)
    messages = list_messages_for_session(db, current_user, session_id)
    
    # Build markdown content
    markdown = f"# {session.title or 'Chat Conversation'}\n\n"
    markdown += f"**Date:** {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    markdown += "---\n\n"
    
    for msg in messages:
        role_emoji = "👤" if msg.role == models.ChatRole.USER else "🤖"
        role_label = "User" if msg.role == models.ChatRole.USER else "Assistant"
        markdown += f"## {role_emoji} {role_label}\n\n"
        markdown += f"{msg.content}\n\n"
        
        if msg.retrieved_chunks and len(msg.retrieved_chunks) > 0:
            markdown += "**Sources:**\n"
            for citation in msg.retrieved_chunks:
                if isinstance(citation, dict):
                    doc_title = citation.get('document_title', 'Unknown')
                    markdown += f"- {doc_title}\n"
            markdown += "\n"
        
        markdown += "---\n\n"
    
    if format == "markdown":
        from fastapi.responses import Response
        return Response(
            content=markdown,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="conversation_{session_id}.md"'
            }
        )
    else:
        # PDF export would require a library like reportlab or weasyprint
        # For now, return markdown
        from fastapi.responses import Response
        return Response(
            content=markdown,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="conversation_{session_id}.md"'
            }
        )
