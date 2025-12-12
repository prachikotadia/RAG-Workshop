"""
GDPR compliance endpoints for data export and deletion.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.responses import Response
from datetime import datetime
import json

from app.db.base import get_db
from app.db import models
from app.auth.dependencies import get_current_user
from app.utils.audit_log import log_audit_event

router = APIRouter()


@router.get("/gdpr/export")
async def export_user_data(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Export all user data in JSON format (GDPR compliance).
    
    Includes:
    - User profile
    - All documents
    - All chat sessions and messages
    - Audit logs
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        JSON file with all user data
    """
    # Collect all user data
    user_data = {
        "export_date": datetime.utcnow().isoformat(),
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        },
        "documents": [],
        "chat_sessions": [],
        "audit_logs": [],
    }
    
    # Export documents
    documents = (
        db.query(models.Document)
        .filter(models.Document.user_id == current_user.id)
        .all()
    )
    for doc in documents:
        chunks = (
            db.query(models.DocumentChunk)
            .filter(models.DocumentChunk.document_id == doc.id)
            .all()
        )
        user_data["documents"].append({
            "id": doc.id,
            "title": doc.title,
            "original_filename": doc.original_filename,
            "status": doc.status.value if doc.status else None,
            "num_chunks": doc.num_chunks,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "chunks": [
                {
                    "id": chunk.id,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    "token_count": chunk.token_count,
                    "metadata": chunk.chunk_metadata,
                }
                for chunk in chunks
            ],
        })
    
    # Export chat sessions
    sessions = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.user_id == current_user.id)
        .all()
    )
    for session in sessions:
        messages = (
            db.query(models.ChatMessage)
            .filter(models.ChatMessage.session_id == session.id)
            .order_by(models.ChatMessage.created_at)
            .all()
        )
        user_data["chat_sessions"].append({
            "id": session.id,
            "title": session.title,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role.value if msg.role else None,
                    "content": msg.content,
                    "retrieved_chunks": msg.retrieved_chunks,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                }
                for msg in messages
            ],
        })
    
    # Export audit logs
    from app.utils.audit_log import AuditLog
    audit_logs = (
        db.query(AuditLog)
        .filter(AuditLog.user_id == current_user.id)
        .order_by(AuditLog.created_at)
        .all()
    )
    for log in audit_logs:
        user_data["audit_logs"].append({
            "id": log.id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "endpoint": log.endpoint,
            "method": log.method,
            "ip_address": log.ip_address,
            "metadata": log.event_metadata,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })
    
    # Log the export action
    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="gdpr_data_export",
        endpoint="/admin/gdpr/export",
        method="GET",
        metadata={"export_date": user_data["export_date"]},
    )
    
    # Return as JSON file
    json_content = json.dumps(user_data, indent=2, default=str)
    return Response(
        content=json_content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="user_data_export_{current_user.id}_{datetime.utcnow().strftime("%Y%m%d")}.json"'
        }
    )


@router.delete("/gdpr/delete-account")
async def delete_user_account_gdpr(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete all user data (GDPR right to be forgotten).
    
    This permanently deletes:
    - User account
    - All documents and chunks
    - All chat sessions and messages
    - All audit logs
    
    WARNING: This action cannot be undone!
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Confirmation message
    """
    from app.auth.service import delete_user_account
    from app.documents.service import list_user_documents, delete_user_document
    from app.vectorstore.faiss_store import get_vector_store
    
    user_id = current_user.id
    
    # Log the deletion request
    log_audit_event(
        db=db,
        user_id=user_id,
        action="gdpr_account_deletion_requested",
        endpoint="/admin/gdpr/delete-account",
        method="DELETE",
        metadata={"user_id": user_id, "email": current_user.email},
    )
    
    # Delete all user data
    # 1. Delete documents (this also deletes chunks and vector store entries)
    vector_store = get_vector_store()
    documents = list_user_documents(db, current_user)
    for doc in documents:
        try:
            delete_user_document(db, current_user, doc.id, vector_store)
        except Exception as e:
            # Log but continue
            import logging
            logging.getLogger(__name__).error(f"Error deleting document {doc.id}: {e}")
    
    # 2. Delete chat sessions (cascade deletes messages)
    from app.chat.service import list_chat_sessions_for_user, delete_chat_session
    sessions = list_chat_sessions_for_user(db, current_user)
    for session in sessions:
        try:
            delete_chat_session(db, current_user, session.id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error deleting session {session.id}: {e}")
    
    # 3. Delete audit logs
    from app.utils.audit_log import AuditLog
    db.query(AuditLog).filter(AuditLog.user_id == user_id).delete()
    
    # 4. Delete user account (this should be last)
    delete_user_account(db, current_user)
    
    db.commit()
    
    return {
        "message": "All user data has been permanently deleted",
        "user_id": user_id,
        "deleted_at": datetime.utcnow().isoformat(),
    }

