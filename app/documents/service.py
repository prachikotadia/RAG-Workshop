# Document upload and processing service
import uuid
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, status
import logging

from app.db import models
from app.db.models import DocumentStatus
from app.config import get_settings
from app.documents.parsers import extract_text_from_file
from app.documents.chunking import chunk_text
from app.documents.semantic_chunking import semantic_chunk_text
from app.embeddings.provider import EmbeddingsProvider
from app.vectorstore.faiss_store import VectorStore

logger = logging.getLogger(__name__)
settings = get_settings()


def save_upload_to_disk(upload_file: UploadFile, user: models.User) -> Path:
    # Save uploaded file to user's directory with a safe filename
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
    # Create database record for the uploaded document
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
    # Process uploaded document: save, extract text, chunk, embed, and index
    # Always ends with status READY or FAILED
    document = None
    file_path = None
    
    try:
        try:
            file_path = save_upload_to_disk(upload_file, user)
        except Exception as e:
            logger.error(f"Failed to save file: {e}", exc_info=True)
            raise ValueError(f"Failed to save uploaded file: {str(e)}")
        
        try:
            document = create_document_record(db, user, upload_file, file_path)
            logger.info(f"Created document {document.id}")
        except Exception as e:
            logger.error(f"Failed to create document record: {e}", exc_info=True)
            raise ValueError(f"Failed to create document record: {str(e)}")
        
        try:
            document.status = DocumentStatus.INDEXING
            db.commit()
            db.refresh(document)
            logger.info(f"Document {document.id} - Starting indexing")
        except Exception as e:
            logger.error(f"Failed to set status to INDEXING: {e}", exc_info=True)
            try:
                document.status = DocumentStatus.FAILED
                db.commit()
            except:
                db.rollback()
            raise ValueError(f"Failed to update document status: {str(e)}")
        
        try:
            text, file_metadata = extract_text_from_file(file_path)
            if not text or not text.strip():
                logger.error(f"Extracted text is empty for document {document.id}")
                raise ValueError("Extracted text is empty or invalid")
            logger.info(f"Document {document.id} - Extracted {len(text)} characters")
            
            if file_path.exists():
                document.file_size = file_path.stat().st_size
            document.file_type = file_metadata.get("mime_type") or file_metadata.get("file_type") or upload_file.content_type
            db.commit()
        except Exception as e:
            logger.error(f"Failed to extract text: {e}", exc_info=True)
            raise ValueError(f"Failed to parse file: {str(e)}")
        
        is_image = file_metadata.get("file_type") == "image"
        
        if is_image:
            logger.info(f"Document {document.id} - Processing image")
            
            try:
                async def process_image_with_timeout():
                    caption_generated = False
                    processed_text = text
                    
                    try:
                        # Use the new comprehensive scan function (more stable and faster)
                        from app.rag.image_analyzer import scan_image_comprehensively
                        
                        logger.info(f"Document {document.id} - Analyzing image")
                        try:
                            scan_result = await asyncio.wait_for(
                                scan_image_comprehensively(file_path),
                                timeout=35.0
                            )
                            logger.info(f"Document {document.id} - Image analysis completed")
                            
                            # Extract information from scan result
                            scan_text = scan_result.get('scan_text', '')
                            caption = scan_result.get('caption', '')
                            description = scan_result.get('description', '')
                            
                            # Build processed text from scan (includes both BLIP and CLIP info)
                            processed_text = f"""Image: {document.title}

{scan_text}

=== Image Metadata ===
{text}"""
                            
                            file_metadata['scan_complete'] = True
                            file_metadata['basic_caption'] = caption
                            file_metadata['detailed_description'] = description
                            file_metadata['analysis_source'] = scan_result.get('analysis_source', 'Unknown')
                            
                            # Store CLIP embedding in metadata for image similarity search
                            # CLIP embeddings (512 dim) are stored separately from text embeddings (1536/384 dim)
                            # to enable image-to-image similarity search using CLIP
                            clip_embedding = scan_result.get('clip_embedding')
                            if clip_embedding:
                                file_metadata['clip_embedding'] = clip_embedding
                                file_metadata['clip_embedding_dim'] = scan_result.get('clip_embedding_dim', 0)
                                logger.info(f"Document {document.id} - Stored CLIP embedding")
                            else:
                                logger.info(f"Document {document.id} - CLIP embedding not available")
                            
                            caption_generated = True
                            analysis_source = scan_result.get('analysis_source', 'Unknown')
                            logger.info(f"Document {document.id} - Image analysis done: {analysis_source}")
                        
                        except asyncio.TimeoutError:
                            logger.warning(f"Document {document.id} - Image analysis timed out")
                        except Exception as e:
                            logger.warning(f"Document {document.id} - Image analysis failed: {e}", exc_info=True)
                    except Exception as e:
                        logger.warning(f"[IMAGE] Image scanner initialization failed for document {document.id}: {e}, using basic metadata", exc_info=True)
                    
                    if not caption_generated:
                        # Ensure we have valid text even if image analysis failed
                        if not processed_text or not processed_text.strip():
                            processed_text = f"Image: {document.title}\n\nMetadata: {file_metadata}"
                    
                    logger.info(f"[IMAGE] Image processing completed for document {document.id}, text length: {len(processed_text)}")
                    return processed_text
                
                # Execute with reasonable timeout - allow OpenAI Vision to complete
                # If analysis takes too long, use metadata fallback
                timeout = 35.0  # 35s for image analysis (matches scan_image_comprehensively timeout)
                
                logger.info(f"Document {document.id} - Processing image")
                text = await asyncio.wait_for(process_image_with_timeout(), timeout=timeout)
                logger.info(f"Document {document.id} - Image processing done, {len(text)} chars")
                
            except asyncio.TimeoutError as timeout_err:
                logger.warning(f"Document {document.id} - Image processing timed out")
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
                logger.info(f"Document {document.id} - Chunking text ({len(text)} chars)")
                if "COMPREHENSIVE IMAGE SCAN" in text:
                    chunks_info = [{
                        "chunk_index": 0,
                        "text": text,
                        "token_count": len(text.split())
                    }]
                    logger.info(f"Document {document.id} - Using single chunk for scan")
                else:
                    if getattr(settings, 'enable_semantic_chunking', True):
                        chunks_info = semantic_chunk_text(
                            text,
                            max_chunk_size=500,
                            min_chunk_size=50,
                            overlap_size=0,
                            preserve_structure=True
                        )
                    else:
                        chunks_info = chunk_text(text, max_words=500, overlap_words=0)
                
                if not chunks_info or len(chunks_info) == 0:
                    logger.error(f"No chunks generated for document {document.id}")
                    raise ValueError("No chunks generated from image text")
                logger.info(f"Document {document.id} - Created {len(chunks_info)} chunks")
            except Exception as e:
                logger.error(f"Failed to chunk image text: {e}", exc_info=True)
                raise ValueError(f"Failed to chunk image text: {str(e)}")
        else:
            if not text or not text.strip():
                raise ValueError("Extracted text is empty")
            
            try:
                if getattr(settings, 'enable_semantic_chunking', True):
                    chunks_info = semantic_chunk_text(
                        text,
                        max_chunk_size=200,
                        min_chunk_size=50,
                        overlap_size=50,
                        preserve_structure=True
                    )
                    logger.info(f"Document {document.id} - Created {len(chunks_info)} semantic chunks")
                else:
                    chunks_info = chunk_text(text, max_words=200, overlap_words=50)
                    logger.info(f"Document {document.id} - Created {len(chunks_info)} chunks")
            except Exception as e:
                logger.error(f"Failed to chunk text: {e}", exc_info=True)
                raise ValueError(f"Failed to chunk document text: {str(e)}")
        
        if not chunks_info or len(chunks_info) == 0:
            logger.error(f"No chunks generated for document {document.id}")
            raise ValueError("No chunks generated from text")
        
        logger.info(f"Document {document.id} - Saving chunks to database")
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
            logger.info(f"Document {document.id} - Saved {len(chunk_objects)} chunks")
        except Exception as e:
            logger.error(f"Failed to create chunks: {e}", exc_info=True)
            db.rollback()
            raise ValueError(f"Failed to create document chunks: {str(e)}")
        
        embeddings = None
        try:
            if is_image:
                chunk_texts = [chunk.text for chunk in chunk_objects]
                try:
                    logger.info(f"Document {document.id} - Generating embeddings for {len(chunk_texts)} chunks")
                    embeddings = await asyncio.wait_for(
                        embeddings_provider.embed_documents(chunk_texts),
                        timeout=15.0
                    )
                    if embeddings and len(embeddings) > 0:
                        logger.info(f"Document {document.id} - Generated {len(embeddings)} embeddings")
                    else:
                        logger.error(f"No embeddings generated for document {document.id}")
                        raise ValueError("No embeddings generated")
                except asyncio.TimeoutError:
                    logger.error(f"Document {document.id} - Embedding generation timed out")
                    raise ValueError("Embedding generation timed out")
                except Exception as e:
                    logger.error(f"Document {document.id} - Embedding generation failed: {e}", exc_info=True)
                    raise ValueError(f"Failed to generate embeddings: {str(e)}")
            else:
                chunk_texts = [chunk.text for chunk in chunk_objects]
                logger.info(f"Document {document.id} - Generating embeddings for {len(chunk_texts)} chunks")
                try:
                    embeddings = await asyncio.wait_for(
                        embeddings_provider.embed_documents(chunk_texts),
                        timeout=30.0
                    )
                    logger.info(f"Document {document.id} - Generated {len(embeddings)} embeddings")
                except asyncio.TimeoutError:
                    logger.error(f"Document {document.id} - Embedding generation timed out")
                    raise ValueError("Embedding generation timed out")
                except Exception as e:
                    logger.error(f"Document {document.id} - Embedding generation failed: {e}", exc_info=True)
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
        
        try:
            chunk_ids = [chunk.id for chunk in chunk_objects]
            vector_store.add_document_chunks(
                user_id=user.id,
                document_id=document.id,
                embeddings=embeddings,
                chunk_ids=chunk_ids
            )
            logger.info(f"Document {document.id} - Added {len(chunk_ids)} chunks to vector store")
        except Exception as e:
            logger.error(f"Failed to add chunks to vector store for document {document.id}: {e}", exc_info=True)
            raise ValueError(f"Failed to index document in vector store: {str(e)}")
        
        # Update document to READY status
        try:
            document.num_chunks = len(chunks_info)
            document.status = DocumentStatus.READY
            db.commit()
            db.refresh(document)
            logger.info(f"Document {document.id} - Status changed to READY")
            logger.info(f"Document {document.id} - Indexing completed ({len(chunks_info)} chunks)")
        except Exception as e:
            logger.error(f"Failed to update document {document.id} status to READY: {e}", exc_info=True)
            # This is critical - try to set FAILED as fallback
            try:
                document.status = DocumentStatus.FAILED
                db.commit()
                logger.info(f"Document {document.id} marked as FAILED after READY update failure")
            except Exception as commit_error:
                logger.error(f"Could not mark document {document.id} as FAILED: {commit_error}", exc_info=True)
                db.rollback()
                # Try one more time
                try:
                    db.refresh(document)
                    document.status = DocumentStatus.FAILED
                    db.commit()
                    logger.info(f"Document {document.id} marked as FAILED on retry")
                except Exception as final_error:
                    logger.error(f"Final attempt to mark document {document.id} as FAILED failed: {final_error}", exc_info=True)
            raise ValueError(f"Failed to update document status: {str(e)}")
        
        if document.status != DocumentStatus.READY:
            logger.error(f"Document {document.id} status is {document.status} instead of READY")
            raise ValueError(f"Document status is {document.status} instead of READY")
        
        # Trigger webhook for document upload (after successful processing)
        try:
            from app.admin.webhooks import trigger_webhook
            await trigger_webhook(
                db=db,
                user_id=user.id,
                event_type="document.uploaded",
                payload={
                    "document_id": document.id,
                    "title": document.title,
                    "filename": document.original_filename,
                    "status": document.status.value if document.status else None,
                    "num_chunks": document.num_chunks,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to trigger webhook for document upload: {e}")
        
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
        
        error_msg = str(e)
        logger.error(f"ValueError in process_and_index_document: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "document_processing_failed",
                "message": f"Failed to process document: {error_msg}",
                "document_id": document.id if document else None
            }
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
        
        error_msg = str(e)
        logger.error(f"Unexpected error in process_and_index_document: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "document_processing_error",
                "message": f"Failed to process document: {error_msg}",
                "document_id": document.id if document else None
            }
        )


def list_user_documents(
    db: Session,
    user: models.User,
    tag_ids: Optional[List[int]] = None,
    category_id: Optional[int] = None,
    file_type: Optional[str] = None,
    min_size: Optional[int] = None,
    max_size: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> List[models.Document]:
    """
    Return all documents belonging to the user with optional filters.
    
    Args:
        db: Database session
        user: User model instance
        tag_ids: Optional list of tag IDs to filter by
        category_id: Optional category ID to filter by
        file_type: Optional file type filter (MIME type or extension)
        min_size: Optional minimum file size in bytes
        max_size: Optional maximum file size in bytes
        date_from: Optional start date filter
        date_to: Optional end date filter
    
    Returns:
        List of Document model instances
    """
    from sqlalchemy.orm import joinedload
    
    # Simple query - new columns are commented out in model
    query = db.query(models.Document).filter(models.Document.user_id == user.id)
    
    # Filter by tags (if tables exist)
    if tag_ids:
        try:
            from app.db.tag_models import Tag, document_tags
            query = query.join(document_tags).join(Tag).filter(Tag.id.in_(tag_ids))
        except (ImportError, Exception):
            # Tags tables might not exist yet, skip filter
            pass
    
    # Filter by category (if column exists)
    if category_id:
        try:
            query = query.filter(models.Document.category_id == category_id)
        except Exception:
            # Column might not exist yet, skip filter
            pass
    
    # Filter by file type (if column exists)
    if file_type:
        try:
            query = query.filter(models.Document.file_type.ilike(f'%{file_type}%'))
        except Exception:
            # Column might not exist yet, skip filter
            pass
    
    # Filter by file size (if column exists)
    if min_size is not None:
        try:
            query = query.filter(models.Document.file_size >= min_size)
        except Exception:
            # Column might not exist yet, skip filter
            pass
    if max_size is not None:
        try:
            query = query.filter(models.Document.file_size <= max_size)
        except Exception:
            # Column might not exist yet, skip filter
            pass
    
    # Filter by date range
    if date_from:
        query = query.filter(models.Document.created_at >= date_from)
    if date_to:
        query = query.filter(models.Document.created_at <= date_to)
    
    # Eagerly load tags to avoid N+1 queries (if tags relationship exists)
    try:
        if hasattr(models.Document, 'tags'):
            query = query.options(joinedload(models.Document.tags))
    except Exception:
        # Tags relationship might not exist yet, continue without eager loading
        pass
    
    return query.order_by(models.Document.created_at.desc()).all()


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
            detail={
                "error": "document_not_found",
                "message": "Document not found or you don't have permission to access it"
            }
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


def cleanup_stuck_documents(
    db: Session,
    user: Optional[models.User] = None,
    max_age_minutes: int = 5
) -> int:
    # Find and fix documents stuck in INDEXING status
    # Documents stuck for more than max_age_minutes are marked as FAILED
    from datetime import datetime, timedelta, timezone
    
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
    
    query = db.query(models.Document).filter(
        models.Document.status == DocumentStatus.INDEXING,
        models.Document.created_at < cutoff_time
    )
    
    if user:
        query = query.filter(models.Document.user_id == user.id)
    
    stuck_docs = query.all()
    fixed_count = 0
    
    for doc in stuck_docs:
        try:
            from datetime import datetime, timezone
            age_minutes = (datetime.now(timezone.utc) - doc.created_at.replace(tzinfo=timezone.utc)).total_seconds() / 60
            logger.warning(f"Found stuck document {doc.id} (created {doc.created_at}, status: {doc.status}, age: {age_minutes:.1f} min)")
            doc.status = DocumentStatus.FAILED
            db.commit()
            fixed_count += 1
            logger.info(f"Marked stuck document {doc.id} as FAILED")
        except Exception as e:
            logger.error(f"Failed to fix stuck document {doc.id}: {e}", exc_info=True)
            db.rollback()
            try:
                db.refresh(doc)
                doc.status = DocumentStatus.FAILED
                db.commit()
                fixed_count += 1
                logger.info(f"Marked stuck document {doc.id} as FAILED on retry")
            except Exception as retry_error:
                logger.error(f"Failed to fix stuck document {doc.id} on retry: {retry_error}", exc_info=True)
    
    if fixed_count > 0:
        logger.info(f"Cleaned up {fixed_count} stuck document(s)")
    
    return fixed_count
