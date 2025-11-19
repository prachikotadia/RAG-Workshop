"""
Document routes for FastAPI.

Phase 4 spec: API endpoints for document upload, listing, retrieval, and deletion.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from app.db.base import get_db
from app.db import models
from app.db.schemas import DocumentRead
from app.auth.dependencies import get_current_user
from app.documents.service import (
    process_and_index_document,
    list_user_documents,
    get_user_document,
    delete_user_document
)
from app.embeddings.provider import EmbeddingsProvider, get_embeddings_provider
from app.vectorstore.faiss_store import VectorStore, get_vector_store as get_vector_store_di
from app.utils.validation import validate_file_extension, validate_file_size, validate_mime_type

router = APIRouter()


def get_vector_store(user: models.User = Depends(get_current_user)) -> VectorStore:
    """
    FastAPI dependency to get vector store for the current user.
    
    Note: VectorStore is shared, but methods take user_id parameter.
    This dependency is kept for consistency with Phase 4, but the actual
    user_id is passed to VectorStore methods.
    
    Args:
        user: Current authenticated user (from dependency)
    
    Returns:
        VectorStore instance (shared, per Phase 5 spec)
    """
    return get_vector_store_di()


@router.post("/upload", response_model=List[DocumentRead], status_code=status.HTTP_201_CREATED)
async def upload_documents(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    embeddings_provider: EmbeddingsProvider = Depends(get_embeddings_provider),
    vector_store: VectorStore = Depends(get_vector_store),
):
    """
    Upload one or more documents.
    
    For each file:
    - Saves to disk
    - Parses text
    - Chunks text
    - Stores in database
    - Generates embeddings
    - Indexes in vector store
    
    Args:
        files: List of uploaded files
        db: Database session
        current_user: Current authenticated user
        embeddings_provider: Embeddings provider instance
        vector_store: Vector store instance for the user
    
    Returns:
        List of DocumentRead schemas
    """
    documents = []
    import logging
    logger = logging.getLogger(__name__)
    
    # Wrap entire upload in try/except to ensure we always return a response
    try:
        for file in files:
            # Validate file extension BEFORE processing
            if not file.filename:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Filename is required"
                )
            
            is_valid_ext, ext_error = validate_file_extension(file.filename)
            if not is_valid_ext:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ext_error
                )
            
            # Validate file size (read content to check size)
            try:
                file_content = await file.read()
                await file.seek(0)  # Reset file pointer for processing
                
                is_valid_size, size_error = validate_file_size(len(file_content))
                if not is_valid_size:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=size_error
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error reading file {file.filename}: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Error reading file: {str(e)}"
                )
            
            # Validate MIME type (if provided)
            if file.content_type:
                is_valid_mime, mime_error = validate_mime_type(file.content_type, file.filename)
                if not is_valid_mime:
                    # For images, be lenient - just log warning
                    if not file.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.heic', '.heif', '.tiff', '.tif', '.svg', '.ico')):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=mime_error
                        )
            
            # Process document - process_and_index_document handles ALL status updates internally
            # It GUARANTEES status will be READY or FAILED
            document = None
            try:
                document = await process_and_index_document(
                    db=db,
                    user=current_user,
                    upload_file=file,
                    embeddings_provider=embeddings_provider,
                    vector_store=vector_store
                )
                # Document status is already READY or FAILED at this point
                documents.append(document)
                logger.info(f"Document {document.id} processed with status: {document.status}")
            except HTTPException as http_exc:
                # HTTPException from process_and_index_document means document is already marked as FAILED
                # Re-raise to return proper error to client
                logger.warning(f"HTTPException during document processing: {http_exc.detail}")
                raise
            except Exception as e:
                # CRITICAL: Always return a proper HTTP response, never let the connection close empty
                logger.error(f"Unexpected error processing {file.filename}: {e}", exc_info=True)
                
                # If document was created but processing failed, it should already be marked as FAILED
                # But we need to ensure we return a proper response
                error_detail = str(e)
                if len(error_detail) > 200:
                    error_detail = error_detail[:200] + "..."
                
                # Ensure database session is in good state
                try:
                    db.rollback()  # Rollback any partial transaction
                except Exception as rollback_error:
                    logger.error(f"Error during rollback: {rollback_error}", exc_info=True)
                
                # Return proper HTTP error response
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error processing {file.filename}: {error_detail}"
                )
        
        # Return successfully processed documents
        return [DocumentRead.model_validate(doc) for doc in documents]
    
    except HTTPException:
        # Re-raise HTTPExceptions (they already have proper responses)
        raise
    except Exception as e:
        # CRITICAL: Catch any unexpected errors and return proper response
        logger.critical(f"CRITICAL: Unexpected error in upload endpoint: {e}", exc_info=True)
        try:
            db.rollback()
        except:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during upload: {str(e)[:200]}"
        )


@router.get("", response_model=List[DocumentRead])
def list_documents(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    List all documents for the current user.
    
    Args:
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        List of DocumentRead schemas
    """
    documents = list_user_documents(db, current_user)
    return [DocumentRead.model_validate(doc) for doc in documents]


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get a specific document by ID.
    
    Args:
        document_id: Document ID to fetch
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        DocumentRead schema
    
    Raises:
        HTTPException: 404 if document not found or not owned by user
    """
    document = get_user_document(db, current_user, document_id)
    return DocumentRead.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    vector_store: VectorStore = Depends(get_vector_store),
):
    """
    Delete a document and its associated chunks.
    
    Also removes entries from the vector store.
    
    Args:
        document_id: Document ID to delete
        db: Database session
        current_user: Current authenticated user
        vector_store: Vector store instance for the user
    
    Raises:
        HTTPException: 404 if document not found or not owned by user
    """
    delete_user_document(db, current_user, document_id, vector_store)
    return None

