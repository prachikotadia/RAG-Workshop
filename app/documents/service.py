"""
Document service for managing documents.

Orchestrates document ingestion pipeline (upload, parse, chunk, store, embed, index).
"""
import uuid
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, status
import logging

from app.db import models
from app.db.models import DocumentStatus
from app.config import get_settings
from app.documents.parsers import extract_text_from_file
from app.documents.chunking import chunk_text
from app.embeddings.provider import EmbeddingsProvider
from app.embeddings.image_provider import CLIPImageEmbeddingsProvider
from app.rag.image_analyzer import get_blip2_analyzer  # Returns SimpleImageAnalyzer (backward compatible)
from app.vectorstore.faiss_store import VectorStore
from pathlib import Path

logger = logging.getLogger(__name__)
settings = get_settings()


def save_upload_to_disk(upload_file: UploadFile, user: models.User) -> Path:
    """
    Save the uploaded file under a per-user directory.
    
    Creates: storage/user_{user.id}/uploads/
    Uses safe filename with timestamp/UUID prefix.
    
    Args:
        upload_file: FastAPI UploadFile object
        user: User model instance
    
    Returns:
        Path to the saved file
    """
    # Create per-user upload directory
    upload_dir = Path(settings.storage_base_dir) / f"user_{user.id}" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate safe filename with timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    original_name = upload_file.filename or "untitled"
    safe_filename = f"{timestamp}_{unique_id}_{original_name}"
    
    file_path = upload_dir / safe_filename
    
    # Save file
    with open(file_path, "wb") as buffer:
        content = upload_file.file.read()
        buffer.write(content)
    
    logger.info(f"Saved uploaded file for user {user.id}: {file_path}")
    return file_path


def create_document_record(
    db: Session,
    user: models.User,
    upload_file: UploadFile,
    file_path: Path
) -> models.Document:
    """
    Create a Document row in the database.
    
    Args:
        db: Database session
        user: User model instance
        upload_file: Uploaded file object
        file_path: Path to saved file (with safe filename)
    
    Returns:
        Created Document model instance
    """
    # Use original filename without extension as title
    title = Path(upload_file.filename or "Untitled").stem
    
    # Store the safe filename (from file_path) so we can delete it later
    safe_filename = file_path.name
    
    doc = models.Document(
        user_id=user.id,
        title=title,
        original_filename=safe_filename,  # Store safe filename for deletion
        status=DocumentStatus.UPLOADING
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


async def process_and_index_document(
    db: Session,
    user: models.User,
    upload_file: UploadFile,
    embeddings_provider: EmbeddingsProvider,
    vector_store: VectorStore,
) -> models.Document:
    """
    End-to-end pipeline for a single uploaded document.
    
    CRITICAL: This function GUARANTEES that the document status will be either READY or FAILED.
    It is FORBIDDEN for this function to exit with status UPLOADING or INDEXING.
    
    Flow:
    1. Save file to disk
    2. Create Document row with status=UPLOADING
    3. Set status=INDEXING, commit
    4. Extract text and metadata from file
    5. Chunk the text
    6. Create DocumentChunk rows for each chunk
    7. Compute embeddings for each chunk's text
    8. Add chunk embeddings to the user's FAISS index
    9. Update document.num_chunks and status=READY, commit
    
    Args:
        db: Database session
        user: User model instance
        upload_file: FastAPI UploadFile object
        embeddings_provider: Embeddings provider instance
        vector_store: Vector store instance for the user
    
    Returns:
        Document model instance with status=READY
    
    Raises:
        HTTPException: On failure, document is marked as FAILED
    """
    document = None
    file_path = None
    
    try:
        # Step 1: Save file to disk
        try:
            file_path = save_upload_to_disk(upload_file, user)
        except Exception as e:
            logger.error(f"Failed to save file to disk: {e}", exc_info=True)
            raise ValueError(f"Failed to save uploaded file: {str(e)}")
        
        # Step 2: Create Document record with status=UPLOADING
        try:
            document = create_document_record(db, user, upload_file, file_path)
            logger.info(f"Created document record {document.id} with status UPLOADING")
        except Exception as e:
            logger.error(f"Failed to create document record: {e}", exc_info=True)
            raise ValueError(f"Failed to create document record: {str(e)}")
        
        # Step 3: Update status to INDEXING and commit immediately
        try:
            document.status = DocumentStatus.INDEXING
            db.commit()
            db.refresh(document)
            logger.info(f"📄 [INDEXING] Document {document.id} ('{document.title}') - Status changed to INDEXING")
            logger.info(f"📄 [INDEXING] Document {document.id} - Starting indexing process...")
        except Exception as e:
            logger.error(f"Failed to set status to INDEXING: {e}", exc_info=True)
            # Try to set FAILED as fallback
            try:
                document.status = DocumentStatus.FAILED
                db.commit()
            except:
                db.rollback()
            raise ValueError(f"Failed to update document status: {str(e)}")
        
        # Extract text and metadata
        try:
            logger.info(f"📄 [INDEXING] Document {document.id} - Step 1/5: Extracting text and metadata...")
            text, file_metadata = extract_text_from_file(file_path)
            if not text or not text.strip():
                logger.error(f"Extracted text is empty for document {document.id}")
                raise ValueError("Extracted text is empty or invalid")
            logger.info(f"📄 [INDEXING] Document {document.id} - ✓ Extracted {len(text)} characters from file")
        except Exception as e:
            logger.error(f"Failed to extract text from file for document {document.id}: {e}", exc_info=True)
            raise ValueError(f"Failed to parse file: {str(e)}")
        
        # Check if this is an image file
        is_image = file_metadata.get("file_type") == "image"
        
        # Process image or text
        if is_image:
            logger.info(f"📄 [INDEXING] Document {document.id} - Step 2/5: Analyzing image file...")
            logger.info(f"📄 [INDEXING] Document {document.id} - Image path: {file_path}")
            
            import asyncio
            try:
                async def process_image_with_timeout():
                    caption_generated = False
                    processed_text = text
                    
                    try:
                        # Use the new comprehensive scan function (more stable and faster)
                        from app.rag.image_analyzer import scan_image_comprehensively
                        
                        logger.info(f"📄 [INDEXING] Document {document.id} - Attempting image analysis (OpenAI → Local → Metadata)...")
                        try:
                            # Use comprehensive scan with fast timeout
                            # Prioritize speed - fail fast to metadata
                            scan_result = await asyncio.wait_for(
                                scan_image_comprehensively(file_path),
                                timeout=8.0  # Reduced to 8s - fail fast
                            )
                            logger.info(f"📄 [INDEXING] Document {document.id} - ✓ Image analysis completed")
                            
                            # Extract information from scan result
                            scan_text = scan_result.get('scan_text', '')
                            caption = scan_result.get('caption', '')
                            description = scan_result.get('description', '')
                            
                            # Build processed text from scan
                            processed_text = f"""Image: {document.title}

{scan_text}

=== Image Metadata ===
{text}"""
                            
                            file_metadata['scan_complete'] = True
                            file_metadata['basic_caption'] = caption
                            file_metadata['detailed_description'] = description
                            file_metadata['analysis_source'] = scan_result.get('analysis_source', 'Unknown')
                            
                            caption_generated = True
                            analysis_source = scan_result.get('analysis_source', 'Unknown')
                            logger.info(f"📄 [INDEXING] Document {document.id} - ✓ Image analysis completed using: {analysis_source}")
                        
                        except asyncio.TimeoutError:
                            logger.warning(f"📄 [INDEXING] Document {document.id} - ⚠ Image analysis timed out, falling back to metadata")
                        except Exception as e:
                            logger.warning(f"📄 [INDEXING] Document {document.id} - ⚠ Image analysis failed: {e}, falling back to metadata", exc_info=True)
                    except Exception as e:
                        logger.warning(f"[IMAGE] Image scanner initialization failed for document {document.id}: {e}, using basic metadata", exc_info=True)
                    
                    if not caption_generated:
                        # Ensure we have valid text even if image analysis failed
                        if not processed_text or not processed_text.strip():
                            processed_text = f"Image: {document.title}\n\nMetadata: {file_metadata}"
                    
                    logger.info(f"[IMAGE] Image processing completed for document {document.id}, text length: {len(processed_text)}")
                    return processed_text
                
                # Execute with fast timeout - prioritize speed
                # If analysis takes too long, use metadata fallback immediately
                timeout = 10.0  # Reduced to 10s - fail fast to metadata
                
                logger.info(f"📄 [INDEXING] Document {document.id} - Starting image processing with {timeout}s timeout...")
                text = await asyncio.wait_for(process_image_with_timeout(), timeout=timeout)
                logger.info(f"[IMAGE] Image processing completed successfully for document {document.id}, text length: {len(text)}")
                
            except asyncio.TimeoutError as timeout_err:
                logger.warning(f"📄 [INDEXING] Document {document.id} - ⚠ Image processing timed out, using metadata")
                # Use basic metadata if everything times out - don't fail, just use metadata
                if not text or not text.strip():
                    text = f"Image: {document.title}\n\nMetadata: {file_metadata}"
                logger.info(f"[IMAGE] Using fallback text for document {document.id} after timeout - continuing with metadata")
                # Don't raise error - continue with metadata instead of failing
            except Exception as e:
                logger.warning(f"Image processing failed for document {document.id}: {e}")
                # Use basic metadata if processing fails - don't fail the document
                if not text or not text.strip():
                    text = f"Image: {document.title}\n\nMetadata: {file_metadata}"
                logger.info(f"[IMAGE] Using fallback text for document {document.id} after error - continuing with metadata")
                # Don't raise error - continue with metadata instead of failing
            
            # Ensure we have valid text before chunking
            if not text or not text.strip():
                logger.warning(f"No text available for document {document.id} after all processing attempts - using minimal text")
                text = f"Image: {document.title}\n\nMetadata: {file_metadata}"
                # Don't raise error - use minimal text instead
            
            # Chunk the image description
            # If comprehensive scan is present, keep it as ONE chunk to preserve all scan data
            try:
                logger.info(f"📄 [INDEXING] Document {document.id} - Step 3/5: Chunking text ({len(text)} chars)...")
                if "COMPREHENSIVE IMAGE SCAN" in text:
                    # For comprehensive scans, keep as single chunk to preserve all sections together
                    chunks_info = [{
                        "chunk_index": 0,
                        "text": text,
                        "token_count": len(text.split())
                    }]
                    logger.info(f"📄 [INDEXING] Document {document.id} - Using single chunk for comprehensive scan")
                else:
                    # For regular image analysis, use chunking
                    chunks_info = chunk_text(text, max_words=500, overlap_words=0)
                
                if not chunks_info or len(chunks_info) == 0:
                    logger.error(f"No chunks generated for document {document.id}")
                    raise ValueError("No chunks generated from image text")
                logger.info(f"📄 [INDEXING] Document {document.id} - ✓ Created {len(chunks_info)} chunk(s)")
            except Exception as e:
                logger.error(f"Failed to chunk image text for document {document.id}: {e}", exc_info=True)
                raise ValueError(f"Failed to chunk image text: {str(e)}")
        else:
            # For text documents: normal processing
            if not text or not text.strip():
                raise ValueError("Extracted text is empty")
            
            # Step 3: Chunk the text
            logger.info(f"📄 [INDEXING] Document {document.id} - Step 3/5: Chunking text ({len(text)} chars)...")
            try:
                chunks_info = chunk_text(text, max_words=200, overlap_words=50)
                logger.info(f"📄 [INDEXING] Document {document.id} - ✓ Created {len(chunks_info)} chunk(s)")
            except Exception as e:
                logger.error(f"Failed to chunk text: {e}", exc_info=True)
                raise ValueError(f"Failed to chunk document text: {str(e)}")
        
        if not chunks_info or len(chunks_info) == 0:
            logger.error(f"No chunks generated for document {document.id}")
            raise ValueError("No chunks generated from text")
        
        # Create DocumentChunk rows
        logger.info(f"📄 [INDEXING] Document {document.id} - Step 4/5: Saving chunks to database...")
        chunk_objects = []
        try:
            for chunk_data in chunks_info:
                # For images, ensure file path is stored in metadata
                chunk_meta = {**file_metadata, **chunk_data}
                if is_image and file_path:
                    chunk_meta['source_path'] = str(file_path)
                    chunk_meta['file_type'] = 'image'
                
                chunk = models.DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk_data["chunk_index"],
                    text=chunk_data["text"],
                    token_count=chunk_data["token_count"],
                    chunk_metadata=chunk_meta  # Merge file metadata with chunk data
                )
                db.add(chunk)
                chunk_objects.append(chunk)
            
            db.commit()
            logger.info(f"📄 [INDEXING] Document {document.id} - ✓ Saved {len(chunk_objects)} chunk(s) to database")
        except Exception as e:
            logger.error(f"Failed to create document chunks for document {document.id}: {e}", exc_info=True)
            db.rollback()
            raise ValueError(f"Failed to create document chunks: {str(e)}")
        
        # Compute embeddings
        logger.info(f"📄 [INDEXING] Document {document.id} - Step 5/5: Generating embeddings for {len(chunk_objects)} chunk(s)...")
        embeddings = None
        try:
            if is_image:
                # For images: Use text embeddings to ensure dimension compatibility with existing FAISS index
                # CLIP embeddings have different dimensions (512) than text embeddings (1536/384),
                # which causes FAISS dimension mismatch errors when mixing them in the same index.
                # We use the image description text to generate embeddings that match the text embedding dimension.
                import asyncio
                
                # Always use text embeddings for images to avoid dimension mismatches
                # The image description text (from metadata analysis) will be embedded using the same
                # provider as text documents, ensuring consistent dimensions.
                chunk_texts = [chunk.text for chunk in chunk_objects]
                try:
                    logger.info(f"📄 [INDEXING] Document {document.id} - Generating text embeddings for {len(chunk_texts)} image description chunk(s)...")
                    embeddings = await asyncio.wait_for(
                        embeddings_provider.embed_documents(chunk_texts),
                        timeout=15.0  # Reduced from 30s to 15s for faster processing
                    )
                    if embeddings and len(embeddings) > 0:
                        emb_dim = len(embeddings[0]) if embeddings else 0
                        logger.info(f"📄 [INDEXING] Document {document.id} - ✓ Generated {len(embeddings)} embedding(s) (dimension: {emb_dim})")
                    else:
                        logger.error(f"No embeddings generated for document {document.id}")
                        raise ValueError("No embeddings generated")
                except asyncio.TimeoutError:
                    logger.error(f"📄 [INDEXING] Document {document.id} - ✗ Embedding generation timed out after 15 seconds")
                    raise ValueError("Embedding generation timed out")
                except Exception as e:
                    logger.error(f"📄 [INDEXING] Document {document.id} - ✗ Embedding generation failed: {e}", exc_info=True)
                    raise ValueError(f"Failed to generate embeddings: {str(e)}")
            else:
                # For text: Use text embeddings
                chunk_texts = [chunk.text for chunk in chunk_objects]
                logger.info(f"📄 [INDEXING] Document {document.id} - Generating embeddings for {len(chunk_texts)} text chunk(s)...")
                try:
                    embeddings = await asyncio.wait_for(
                        embeddings_provider.embed_documents(chunk_texts),
                        timeout=30.0  # 30 seconds timeout for text embeddings
                    )
                    logger.info(f"📄 [INDEXING] Document {document.id} - ✓ Generated {len(embeddings)} embedding(s)")
                except asyncio.TimeoutError:
                    logger.error(f"📄 [INDEXING] Document {document.id} - ✗ Embedding generation timed out after 30 seconds")
                    raise ValueError("Embedding generation timed out")
                except Exception as e:
                    logger.error(f"📄 [INDEXING] Document {document.id} - ✗ Embedding generation failed: {e}", exc_info=True)
                    raise ValueError(f"Failed to generate embeddings: {str(e)}")
            
            if not embeddings or len(embeddings) == 0:
                logger.error(f"No embeddings generated for document {document.id}")
                raise ValueError("No embeddings generated")
            if len(embeddings) != len(chunk_objects):
                logger.error(f"Embedding count mismatch for document {document.id}: {len(embeddings)} embeddings for {len(chunk_objects)} chunks")
                raise ValueError(f"Embedding count mismatch: {len(embeddings)} embeddings for {len(chunk_objects)} chunks")
        except Exception as e:
            logger.error(f"Failed to generate embeddings for document {document.id}: {e}", exc_info=True)
            raise ValueError(f"Failed to generate embeddings: {str(e)}")
        
        # Add to vector store
        logger.info(f"📄 [INDEXING] Document {document.id} - Adding {len(chunk_objects)} chunk(s) to vector store...")
        try:
            chunk_ids = [chunk.id for chunk in chunk_objects]
            vector_store.add_document_chunks(
                user_id=user.id,
                document_id=document.id,
                embeddings=embeddings,
                chunk_ids=chunk_ids
            )
            logger.info(f"📄 [INDEXING] Document {document.id} - ✓ Added {len(chunk_ids)} chunk(s) to vector store")
        except Exception as e:
            logger.error(f"Failed to add chunks to vector store for document {document.id}: {e}", exc_info=True)
            raise ValueError(f"Failed to index document in vector store: {str(e)}")
        
        # Update document to READY status
        try:
            document.num_chunks = len(chunks_info)
            document.status = DocumentStatus.READY
            db.commit()
            db.refresh(document)
            logger.info(f"✅ [INDEXING] Document {document.id} ('{document.title}') - Status changed to READY")
            logger.info(f"✅ [INDEXING] Document {document.id} - Indexing completed successfully! ({len(chunks_info)} chunk(s))")
        except Exception as e:
            logger.error(f"CRITICAL: Failed to update document {document.id} status to READY: {e}", exc_info=True)
            # This is critical - try to set FAILED as fallback
            try:
                document.status = DocumentStatus.FAILED
                db.commit()
                logger.info(f"Document {document.id} marked as FAILED after READY update failure")
            except Exception as commit_error:
                logger.critical(f"CRITICAL: Could not mark document {document.id} as FAILED after READY update failure: {commit_error}", exc_info=True)
                db.rollback()
                # Try one more time
                try:
                    db.refresh(document)
                    document.status = DocumentStatus.FAILED
                    db.commit()
                    logger.info(f"Document {document.id} marked as FAILED on retry")
                except Exception as final_error:
                    logger.critical(f"CRITICAL: Final attempt to mark document {document.id} as FAILED also failed: {final_error}", exc_info=True)
            raise ValueError(f"Failed to update document status: {str(e)}")
        
        # Final verification: document status MUST be READY at this point
        if document.status != DocumentStatus.READY:
            logger.critical(f"CRITICAL: Document {document.id} status is {document.status} instead of READY after processing!")
            raise ValueError(f"Document status is {document.status} instead of READY")
        
        return document
        
    except ValueError as e:
        # ValueErrors are expected validation errors - mark as FAILED
        logger.error(f"Validation error processing document {document.id if document else 'unknown'}: {e}", exc_info=True)
        if document:
            try:
                document.status = DocumentStatus.FAILED
                db.commit()
                logger.info(f"Document {document.id} marked as FAILED due to validation error")
            except Exception as commit_error:
                logger.error(f"Failed to mark document as FAILED: {commit_error}", exc_info=True)
                db.rollback()
                # Try one more time
                try:
                    db.refresh(document)
                    document.status = DocumentStatus.FAILED
                    db.commit()
                    logger.info(f"Document {document.id} marked as FAILED on retry")
                except Exception as final_error:
                    logger.critical(f"CRITICAL: Could not mark document {document.id} as FAILED: {final_error}", exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process document: {str(e)}"
        )
        
    except Exception as e:
        # Any other exception - mark as FAILED
        logger.error(f"Unexpected error processing document {document.id if document else 'unknown'}: {e}", exc_info=True)
        
        # Ensure document status is set to FAILED
        if document:
            try:
                document.status = DocumentStatus.FAILED
                db.commit()
                logger.info(f"Document {document.id} marked as FAILED due to unexpected error")
            except Exception as commit_error:
                logger.error(f"Failed to mark document as FAILED: {commit_error}", exc_info=True)
                # Try one more time with rollback
                try:
                    db.rollback()
                    db.refresh(document)
                    document.status = DocumentStatus.FAILED
                    db.commit()
                    logger.info(f"Document {document.id} marked as FAILED on retry")
                except Exception as final_error:
                    logger.critical(f"CRITICAL: Could not mark document {document.id} as FAILED: {final_error}", exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )


def list_user_documents(db: Session, user: models.User) -> List[models.Document]:
    """
    Return all documents belonging to the user.
    
    Args:
        db: Database session
        user: User model instance
    
    Returns:
        List of Document model instances
    """
    return (
        db.query(models.Document)
        .filter(models.Document.user_id == user.id)
        .order_by(models.Document.created_at.desc())
        .all()
    )


def get_user_document(
    db: Session,
    user: models.User,
    document_id: int
) -> models.Document:
    """
    Load a document by id, ensuring it belongs to the given user.
    
    Args:
        db: Database session
        user: User model instance
        document_id: Document ID to fetch
    
    Returns:
        Document model instance
    
    Raises:
        HTTPException: 404 if not found or not owned by user
    """
    document = (
        db.query(models.Document)
        .filter(
            models.Document.id == document_id,
            models.Document.user_id == user.id
        )
        .first()
    )
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return document


def delete_user_document(
    db: Session,
    user: models.User,
    document_id: int,
    vector_store: VectorStore,
) -> None:
    """
    Delete a document and its chunks for the user.
    
    Also removes its entries from the vector store.
    Uses cascades in SQLAlchemy for chunks.
    
    Args:
        db: Database session
        user: User model instance
        document_id: Document ID to delete
        vector_store: Vector store instance for the user
    
    Raises:
        HTTPException: 404 if document not found or not owned by user
    """
    document = get_user_document(db, user, document_id)
    
    # Get chunk IDs before deletion
    chunk_ids = [chunk.id for chunk in document.chunks]
    
    # Remove from vector store
    if chunk_ids:
        try:
            vector_store.remove_document_chunks(
                user_id=user.id,
                document_chunk_ids=chunk_ids
            )
        except Exception as e:
            logger.error(f"Error removing chunks from vector store: {e}")
    
    # Delete file from disk
    file_path = Path(settings.storage_base_dir) / f"user_{user.id}" / "uploads" / document.original_filename
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as e:
            logger.warning(f"Error deleting file {file_path}: {e}")
    
    # Delete from database (cascade will handle chunks)
    db.delete(document)
    db.commit()
    
    logger.info(f"Deleted document {document_id} for user {user.id}")
