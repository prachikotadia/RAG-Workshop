# Document API routes
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional
import traceback

from app.db.base import get_db
from app.db import models
from app.db.schemas import DocumentRead
from app.auth.dependencies import get_current_user
from app.documents.service import (
    process_and_index_document,
    list_user_documents,
    get_user_document,
    delete_user_document,
    cleanup_stuck_documents
)
from app.documents.fulltext_search import search_documents_fulltext, search_within_document
from app.utils.cache import invalidate_user_cache
from app.embeddings.provider import EmbeddingsProvider, get_embeddings_provider
from app.vectorstore.faiss_store import VectorStore, get_vector_store as get_vector_store_di
from app.utils.validation import validate_file_extension, validate_file_size, validate_mime_type

router = APIRouter()


@router.post("/upload/debug")
async def debug_upload(
    request: Request,
):
    # Debug endpoint - no auth required
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🔍 DEBUG UPLOAD ENDPOINT CALLED")
    logger.info(f"Method: {request.method}")
    logger.info(f"URL: {request.url}")
    logger.info(f"Headers: {dict(request.headers)}")
    
    try:
        content_type = request.headers.get("content-type", "")
        logger.info(f"Content-Type: {content_type}")
        
        if "multipart/form-data" in content_type:
            form_data = await request.form()
            logger.info(f"Form data keys: {list(form_data.keys())}")
            for key in form_data.keys():
                value = form_data[key]
                logger.info(f"  Key '{key}': type={type(value)}, value={value}")
                if hasattr(value, 'filename'):
                    logger.info(f"    -> File: {value.filename}, type: {value.content_type}")
        else:
            body = await request.body()
            logger.info(f"Body (first 500 chars): {body[:500]}")
    except Exception as e:
        logger.error(f"Error reading request: {e}", exc_info=True)
    
    return {
        "status": "debug_complete",
        "message": "Check server logs for details"
    }


def get_vector_store(user: models.User = Depends(get_current_user)) -> VectorStore:
    # Get vector store instance
    return get_vector_store_di()


@router.post("/upload", response_model=List[DocumentRead], status_code=status.HTTP_201_CREATED)
async def upload_documents(
    request: Request,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    embeddings_provider: EmbeddingsProvider = Depends(get_embeddings_provider),
    vector_store: VectorStore = Depends(get_vector_store),
):
    # Upload and process documents
    documents = []
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Log request details for debugging
        logger.info("Upload endpoint called")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request URL: {request.url}")
        logger.info(f"Content-Type: {request.headers.get('content-type', 'NOT SET')}")
        logger.info(f"Content-Length: {request.headers.get('content-length', 'NOT SET')}")
        logger.info(f"Files parameter type: {type(files)}, length: {len(files) if files else 0}")
        logger.info(f"User ID: {current_user.id}, Email: {current_user.email}")
        
        # Validate files parameter
        if not files or len(files) == 0:
            logger.error("❌ Upload request failed: No files provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "no_files_provided",
                    "message": "No files were uploaded. Please select at least one file."
                }
            )
        
        logger.info(f"📤 Upload request received: {len(files)} file(s)")
        
        # Log each file's details
        for i, f in enumerate(files):
            try:
                logger.debug(f"File {i+1}: filename={f.filename}, content_type={f.content_type}, size={f.size if hasattr(f, 'size') else 'unknown'}")
            except Exception as log_err:
                logger.warning(f"Could not log file {i+1} details: {log_err}")
        
        # Wrap entire upload in try/except to ensure we always return a response
        try:
            for idx, file in enumerate(files, 1):
                logger.info(f"Processing file {idx}/{len(files)}: {file.filename}")
                
                # Validate file extension BEFORE processing
                if not file.filename:
                    error_msg = "Filename is required"
                    logger.error(f"❌ File {idx} validation failed: {error_msg}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "error": "validation_failed",
                            "message": error_msg,
                            "field": "filename",
                            "file_index": idx
                        }
                    )
                
                logger.debug(f"Validating file extension for: {file.filename}")
                is_valid_ext, ext_error = validate_file_extension(file.filename)
                if not is_valid_ext:
                    logger.error(f"❌ File {idx} ({file.filename}) extension validation failed: {ext_error}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "error": "invalid_file_extension",
                            "message": ext_error,
                            "filename": file.filename,
                            "file_index": idx
                        }
                    )
                logger.debug(f"✓ File extension validation passed: {file.filename}")
                
                # Validate file size (read content to check size)
                try:
                    logger.debug(f"Reading file content to validate size: {file.filename}")
                    file_content = await file.read()
                    await file.seek(0)  # Reset file pointer for processing
                    
                    file_size = len(file_content)
                    logger.debug(f"File size: {file_size} bytes ({file_size / (1024*1024):.2f}MB)")
                    
                    is_valid_size, size_error = validate_file_size(file_size)
                    if not is_valid_size:
                        logger.error(f"❌ File {idx} ({file.filename}) size validation failed: {size_error}")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail={
                                "error": "file_too_large",
                                "message": size_error,
                                "filename": file.filename,
                                "file_size_bytes": file_size,
                                "file_index": idx
                            }
                        )
                    logger.debug(f"✓ File size validation passed: {file_size} bytes")
                except HTTPException:
                    raise
                except Exception as e:
                    error_msg = f"Error reading file: {str(e)}"
                    logger.error(f"❌ File {idx} ({file.filename}) read error: {error_msg}", exc_info=True)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "error": "file_read_error",
                            "message": error_msg,
                            "filename": file.filename,
                            "file_index": idx
                        }
                    )
                
                # Validate MIME type (if provided) - NEVER REJECT, only log warnings
                if file.content_type:
                    logger.debug(f"Validating MIME type: {file.content_type} for {file.filename}")
                    is_valid_mime, mime_error = validate_mime_type(file.content_type, file.filename)
                    if not is_valid_mime:
                        # This should never happen now (validate_mime_type always returns True for valid extensions)
                        # But if it does, log and continue anyway
                        logger.warning(f"⚠️ MIME type validation returned False for {file.filename}: {mime_error} - continuing anyway")
                    else:
                        logger.debug(f"✓ MIME type validation passed: {file.content_type}")
                else:
                    logger.debug(f"No content_type provided for {file.filename} - skipping MIME validation")
                
                # Process document - process_and_index_document handles ALL status updates internally
                # It GUARANTEES status will be READY or FAILED
                document = None
                try:
                    import asyncio
                    logger.info(f"🚀 Starting document processing for: {file.filename}")
                    # Add hard timeout wrapper to prevent hanging
                    try:
                        # Increased timeout to 90s to allow full processing (image analysis + embeddings)
                        # Large images or complex documents may need more time
                        document = await asyncio.wait_for(
                            process_and_index_document(
                                db=db,
                                user=current_user,
                                upload_file=file,
                                embeddings_provider=embeddings_provider,
                                vector_store=vector_store
                            ),
                            timeout=90.0  # 90s to allow full processing pipeline (increased from 60s)
                        )
                        # Document status is already READY or FAILED at this point
                        documents.append(document)
                        logger.info(f"Document {document.id} processed: {document.status}")
                        # Invalidate user's query cache after document upload
                        invalidate_user_cache(current_user.id)
                    except asyncio.TimeoutError:
                        file_size_mb = len(file_content) / (1024 * 1024) if 'file_content' in locals() else 0
                        error_msg = f"Document processing timed out after 90 seconds for {file.filename}. "
                        if file_size_mb > 10:
                            error_msg += f"The file is large ({file_size_mb:.1f}MB) and may need more time. "
                        error_msg += "The document may still be processing in the background. Please refresh the page to check status."
                        logger.error(f"❌ CRITICAL: {error_msg}")
                        # Find the document and mark it as FAILED
                        try:
                            from app.db import models
                            from app.db.schemas import DocumentStatus
                            stuck_doc = db.query(models.Document).filter(
                                models.Document.user_id == current_user.id,
                                models.Document.status == DocumentStatus.INDEXING
                            ).order_by(models.Document.created_at.desc()).first()
                            if stuck_doc:
                                stuck_doc.status = DocumentStatus.FAILED
                                db.commit()
                                logger.info(f"Marked stuck document {stuck_doc.id} as FAILED due to timeout")
                        except Exception as fix_error:
                            logger.error(f"Failed to fix stuck document: {fix_error}", exc_info=True)
                        raise HTTPException(
                            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                            detail={
                                "error": "processing_timeout",
                                "message": error_msg,
                                "filename": file.filename,
                                "file_index": idx,
                                "timeout_seconds": 90,
                                "file_size_mb": round(file_size_mb, 2) if file_size_mb > 0 else None
                            }
                        )
                except HTTPException as http_exc:
                    # HTTPException from process_and_index_document means document is already marked as FAILED
                    # Re-raise to return proper error to client
                    logger.warning(f"⚠️ HTTPException during document processing for {file.filename}: {http_exc.detail}")
                    # Ensure detail is a dict for consistent JSON response
                    if isinstance(http_exc.detail, str):
                        http_exc.detail = {
                            "error": "processing_failed",
                            "message": http_exc.detail,
                            "filename": file.filename,
                            "file_index": idx
                        }
                    raise
                except Exception as e:
                    # CRITICAL: Always return a proper HTTP response, never let the connection close empty
                    error_msg = str(e)
                    logger.error(f"❌ Unexpected error processing {file.filename}: {error_msg}", exc_info=True)
                    
                    # If document was created but processing failed, it should already be marked as FAILED
                    # But we need to ensure we return a proper response
                    if len(error_msg) > 200:
                        error_msg = error_msg[:200] + "..."
                    
                    # Ensure database session is in good state
                    try:
                        db.rollback()  # Rollback any partial transaction
                    except Exception as rollback_error:
                        logger.error(f"Error during rollback: {rollback_error}", exc_info=True)
                    
                    # Return proper HTTP error response with clean JSON
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail={
                            "error": "processing_error",
                            "message": f"Error processing {file.filename}: {error_msg}",
                            "filename": file.filename,
                            "file_index": idx
                        }
                    )
        
            # Return successfully processed documents
            logger.info(f"Upload completed: {len(documents)} document(s) processed")
            return [DocumentRead.model_validate(doc) for doc in documents]
        except HTTPException:
            # Re-raise HTTPExceptions from inner loop
            raise
        except Exception as inner_e:
            # Catch any errors from the file processing loop
            logger.error(f"❌ Error in file processing loop: {inner_e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "file_processing_error",
                    "message": f"Error processing files: {str(inner_e)[:200]}"
                }
            )
    
    except HTTPException as http_exc:
        # Re-raise HTTPExceptions (they already have proper responses)
        # Ensure detail is a dict for consistent JSON response
        if isinstance(http_exc.detail, str):
            http_exc.detail = {
                "error": "upload_failed",
                "message": http_exc.detail
            }
        logger.error(f"❌ Upload failed with HTTPException: {http_exc.detail}")
        raise
    except RequestValidationError as validation_err:
        # FastAPI validation error - happens before our code runs
        logger.error(f"❌ Request validation error: {validation_err.errors()}")
        logger.error(f"Request body/params issue - this happens before route handler")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "request_validation_failed",
                "message": "Invalid request format. Please ensure files are sent correctly.",
                "validation_errors": validation_err.errors()
            }
        )
    except Exception as e:
        # CRITICAL: Catch any unexpected errors and return proper response
        error_msg = str(e)
        error_trace = traceback.format_exc()
        logger.critical(f"❌ CRITICAL: Unexpected error in upload endpoint: {error_msg}")
        logger.critical(f"Traceback: {error_trace}")
        try:
            db.rollback()
        except:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "unexpected_error",
                "message": f"Unexpected error during upload: {error_msg[:200]}"
            }
        )


@router.get("/{document_id}/related")
def get_related_documents(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    limit: int = 5,
):
    # Get related documents based on entity overlap
    from app.rag.document_relationships import build_document_graph, get_related_documents as get_related
    
    # Get the target document
    target_doc = get_user_document(db, current_user, document_id)
    
    # Get all user documents and chunks
    all_docs = list_user_documents(db, current_user)
    all_chunks = []
    
    for doc in all_docs:
        chunks = db.query(models.DocumentChunk).filter(
            models.DocumentChunk.document_id == doc.id
        ).all()
        for chunk in chunks:
            all_chunks.append({
                "document_id": chunk.document_id,
                "text": chunk.text,
            })
    
    # Build document dicts
    doc_dicts = [{
        "id": doc.id,
        "title": doc.title,
        "text": doc.title,  # Use title as text for entity extraction
    } for doc in all_docs]
    
    # Add chunk text to document text
    for chunk in all_chunks:
        doc_id = chunk["document_id"]
        for doc_dict in doc_dicts:
            if doc_dict["id"] == doc_id:
                doc_dict["text"] += " " + chunk["text"]
                break
    
    # Build graph
    graph = build_document_graph(doc_dicts, all_chunks)
    
    # Get related documents
    related = get_related(document_id, graph, limit=limit)
    
    # Fetch full document info
    related_docs = []
    for rel_info in related:
        rel_doc_id = rel_info["document_id"]
        try:
            rel_doc = get_user_document(db, current_user, rel_doc_id)
            related_docs.append({
                "document": DocumentRead.model_validate(rel_doc),
                "similarity": rel_info["similarity"],
            })
        except HTTPException:
            continue  # Skip documents user doesn't have access to
    
    return related_docs


@router.get("/search")
def search_documents(
    query: str,
    document_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Full-text search across document content with highlighting
    from app.documents.fulltext_search import search_documents_fulltext
    
    results = search_documents_fulltext(
        db=db,
        user_id=current_user.id,
        query=query,
        document_id=document_id,
        limit=limit,
    )
    
    return {
        "query": query,
        "results": results,
        "total_results": len(results),
    }


@router.post("/cleanup-stuck", status_code=status.HTTP_200_OK)
def cleanup_stuck(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    max_age_minutes: int = 5,
):
    # Clean up documents stuck in INDEXING status
    fixed_count = cleanup_stuck_documents(db, user=current_user, max_age_minutes=max_age_minutes)
    return {
        "message": f"Cleaned up {fixed_count} stuck document(s)",
        "fixed_count": fixed_count
    }


@router.get("", response_model=List[DocumentRead])
def list_documents(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    search: Optional[str] = None,
    tag_ids: Optional[str] = None,  # Comma-separated tag IDs
    category_id: Optional[int] = None,
    file_type: Optional[str] = None,
    min_size: Optional[int] = None,
    max_size: Optional[int] = None,
    date_from: Optional[str] = None,  # ISO format date string
    date_to: Optional[str] = None,  # ISO format date string
):
    # List documents with optional filters
    # Auto-cleanup stuck documents before listing
    cleanup_stuck_documents(db, user=current_user, max_age_minutes=5)
    
    from datetime import datetime
    
    # Parse tag IDs
    tag_id_list = None
    if tag_ids:
        try:
            tag_id_list = [int(tid.strip()) for tid in tag_ids.split(',') if tid.strip()]
        except ValueError:
            tag_id_list = None
    
    # Parse dates
    date_from_obj = None
    date_to_obj = None
    if date_from:
        try:
            date_from_obj = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        except ValueError:
            pass
    if date_to:
        try:
            date_to_obj = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
        except ValueError:
            pass
    
    documents = list_user_documents(
        db,
        current_user,
        tag_ids=tag_id_list,
        category_id=category_id,
        file_type=file_type,
        min_size=min_size,
        max_size=max_size,
        date_from=date_from_obj,
        date_to=date_to_obj,
    )
    
    # Apply search filter if provided (title/filename only for backward compatibility)
    if search:
        search_lower = search.lower()
        documents = [
            doc for doc in documents
            if search_lower in doc.title.lower() or search_lower in doc.original_filename.lower()
        ]
    
    return [DocumentRead.model_validate(doc) for doc in documents]


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Get document by ID
    document = get_user_document(db, current_user, document_id)
    return DocumentRead.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    vector_store: VectorStore = Depends(get_vector_store),
):
    # Delete document and remove from vector store
    delete_user_document(db, current_user, document_id, vector_store)
    # Invalidate cache after document deletion
    invalidate_user_cache(current_user.id)
    return None


@router.post("/bulk-delete", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_delete_documents(
    document_ids: List[int],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    vector_store: VectorStore = Depends(get_vector_store),
):
    # Delete multiple documents
    from app.documents.service import delete_user_document
    
    for doc_id in document_ids:
        try:
            delete_user_document(db, current_user, doc_id, vector_store)
        except HTTPException:
            # Skip documents that don't exist or aren't owned by user
            pass
    
    # Invalidate cache after bulk deletion
    invalidate_user_cache(current_user.id)
    return None


@router.get("/{document_id}/export")
async def export_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Export document content as text file
    document = get_user_document(db, current_user, document_id)
    
    # Get all chunks for the document
    chunks = (
        db.query(models.DocumentChunk)
        .filter(models.DocumentChunk.document_id == document_id)
        .order_by(models.DocumentChunk.chunk_index)
        .all()
    )
    
    # Combine chunks
    content = "\n\n".join(chunk.text for chunk in chunks)
    
    from fastapi.responses import Response
    return Response(
        content=content,
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="{document.title}.txt"'
        }
    )

