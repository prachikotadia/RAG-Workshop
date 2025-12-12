"""
Document preview routes for fetching chunk content and document files.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from pathlib import Path
from typing import Optional
import logging

from app.db.base import get_db
from app.db import models
from app.auth.dependencies import get_current_user
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


@router.get("/{document_id}/chunk/{chunk_index}")
def get_chunk_content(
    document_id: int,
    chunk_index: int,
    query: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get chunk content with optional query highlighting.
    
    Args:
        document_id: Document ID
        chunk_index: Chunk index (0-based)
        query: Optional query string to highlight in the chunk
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        JSON with chunk content, document info, and highlighted text
    """
    # Verify document ownership
    document = db.query(models.Document).filter(
        models.Document.id == document_id,
        models.Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Get chunk
    chunk = db.query(models.DocumentChunk).filter(
        models.DocumentChunk.document_id == document_id,
        models.DocumentChunk.chunk_index == chunk_index
    ).first()
    
    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunk not found"
        )
    
    # Highlight query terms if provided
    highlighted_text = chunk.text
    if query:
        import re
        # Escape special regex characters
        query_escaped = re.escape(query)
        # Find all words in query
        query_words = query.split()
        if query_words:
            # Create pattern to match any query word (case-insensitive)
            pattern = '|'.join(re.escape(word) for word in query_words)
            # Highlight matches
            def highlight_match(match):
                return f'<mark class="bg-yellow-200 dark:bg-yellow-800 px-1 rounded">{match.group(0)}</mark>'
            highlighted_text = re.sub(
                pattern,
                highlight_match,
                chunk.text,
                flags=re.IGNORECASE
            )
    
    return {
        "document_id": document.id,
        "document_title": document.title,
        "chunk_index": chunk.chunk_index,
        "text": chunk.text,
        "highlighted_text": highlighted_text,
        "token_count": chunk.token_count,
        "metadata": chunk.chunk_metadata or {},
    }


@router.get("/{document_id}/file")
def get_document_file(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get the original document file (for images/PDFs).
    
    Args:
        document_id: Document ID
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        File response with the document file
    """
    # Verify document ownership
    document = db.query(models.Document).filter(
        models.Document.id == document_id,
        models.Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Get file path from first chunk metadata or construct from storage
    file_path = None
    chunks = db.query(models.DocumentChunk).filter(
        models.DocumentChunk.document_id == document_id
    ).limit(1).all()
    
    if chunks and chunks[0].chunk_metadata:
        file_path = chunks[0].chunk_metadata.get('source_path')
    
    if not file_path:
        # Construct path from storage directory
        file_path = Path(settings.storage_base_dir) / str(current_user.id) / document.original_filename
    
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found"
        )
    
    # Determine media type
    media_type = "application/octet-stream"
    if file_path.suffix.lower() in ['.jpg', '.jpeg']:
        media_type = "image/jpeg"
    elif file_path.suffix.lower() == '.png':
        media_type = "image/png"
    elif file_path.suffix.lower() == '.gif':
        media_type = "image/gif"
    elif file_path.suffix.lower() == '.pdf':
        media_type = "application/pdf"
    
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=document.original_filename
    )
