"""Admin and statistics endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.base import get_db
from app.db import models
from app.auth.dependencies import get_current_user

router = APIRouter()


@router.get("/stats")
async def get_user_stats(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get statistics for the current user."""
    # Document stats
    doc_stats = (
        db.query(
            func.count(models.Document.id).label("total_documents"),
            func.sum(models.Document.num_chunks).label("total_chunks"),
            func.sum(func.cast(models.Document.status == models.DocumentStatus.READY, models.Integer)).label("ready_documents")
        )
        .filter(models.Document.user_id == current_user.id)
        .first()
    )
    
    # Session stats
    session_count = (
        db.query(func.count(models.ChatSession.id))
        .filter(models.ChatSession.user_id == current_user.id)
        .scalar()
    )
    
    # Message stats
    message_count = (
        db.query(func.count(models.ChatMessage.id))
        .join(models.ChatSession)
        .filter(models.ChatSession.user_id == current_user.id)
        .scalar()
    )
    
    return {
        "user_id": current_user.id,
        "documents": {
            "total": doc_stats.total_documents or 0,
            "ready": doc_stats.ready_documents or 0,
            "total_chunks": doc_stats.total_chunks or 0
        },
        "chat_sessions": session_count or 0,
        "chat_messages": message_count or 0
    }


@router.post("/documents/bulk-delete", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_delete_documents(
    document_ids: list[int],
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bulk delete multiple documents."""
    documents = (
        db.query(models.Document)
        .filter(
            models.Document.id.in_(document_ids),
            models.Document.user_id == current_user.id
        )
        .all()
    )
    
    if len(documents) != len(document_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Some documents not found or not owned by user"
        )
    
    from app.documents.service import delete_user_document
    from app.vectorstore.faiss_store import get_vector_store
    
    vector_store = get_vector_store()
    for document in documents:
        delete_user_document(db, current_user, document.id, vector_store)
    
    return None

