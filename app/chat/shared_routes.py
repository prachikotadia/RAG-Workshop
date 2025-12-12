"""
Routes for shareable conversation links.
"""
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db import models
from app.db.shared_conversation_models import SharedConversation, ShareStatus
from app.db.schemas import ChatSessionRead, ChatMessageRead
from app.auth.dependencies import get_current_user, get_optional_user
from app.chat.service import get_chat_session_for_user

logger = logging.getLogger(__name__)
router = APIRouter()


def generate_share_token() -> str:
    """Generate a unique token for sharing."""
    return secrets.token_urlsafe(32)


@router.post("/sessions/{session_id}/share")
def create_share_link(
    session_id: int,
    expires_in_days: Optional[int] = Query(None, description="Number of days until expiration (None = never expires)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Create a shareable link for a conversation.
    
    Args:
        session_id: Chat session ID to share
        expires_in_days: Optional expiration in days (None = never expires)
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        Share link information with token
    """
    # Verify session ownership
    session = get_chat_session_for_user(db, current_user, session_id)
    
    # Generate unique token
    token = generate_share_token()
    
    # Calculate expiration
    expires_at = None
    if expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
    
    # Create shared conversation record
    shared = SharedConversation(
        session_id=session.id,
        token=token,
        status=ShareStatus.ACTIVE,
        expires_at=expires_at,
    )
    db.add(shared)
    db.commit()
    db.refresh(shared)
    
    logger.info(f"Created share link for session {session_id} with token {token[:8]}...")
    
    return {
        "token": token,
        "share_url": f"/shared/{token}",
        "expires_at": expires_at.isoformat() if expires_at else None,
        "created_at": shared.created_at.isoformat(),
    }


@router.get("/shared/{token}")
def get_shared_conversation(
    token: str,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_user),
):
    """
    Get a shared conversation by token (read-only, no auth required).
    
    Args:
        token: Share token
        db: Database session
        current_user: Optional current user (for tracking access)
    
    Returns:
        Conversation data (read-only)
    """
    # Find shared conversation
    shared = db.query(SharedConversation).filter(
        SharedConversation.token == token
    ).first()
    
    if not shared:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found"
        )
    
    # Check if expired
    if shared.expires_at and shared.expires_at < datetime.utcnow():
        shared.status = ShareStatus.EXPIRED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Share link has expired"
        )
    
    # Check if revoked
    if shared.status == ShareStatus.REVOKED:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Share link has been revoked"
        )
    
    # Get session and messages
    session = db.query(models.ChatSession).filter(
        models.ChatSession.id == shared.session_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Get messages directly (no ownership check needed for shared conversations)
    messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session.id)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )
    
    # Increment access count
    shared.access_count += 1
    db.commit()
    
    return {
        "session": ChatSessionRead.model_validate(session),
        "messages": [ChatMessageRead.model_validate(msg) for msg in messages],
        "is_shared": True,
        "access_count": shared.access_count,
        "created_at": shared.created_at.isoformat(),
        "expires_at": shared.expires_at.isoformat() if shared.expires_at else None,
    }


@router.delete("/sessions/{session_id}/share/{token}")
def revoke_share_link(
    session_id: int,
    token: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Revoke a share link (only the owner can revoke).
    
    Args:
        session_id: Chat session ID
        token: Share token to revoke
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        Success message
    """
    # Verify session ownership
    session = get_chat_session_for_user(db, current_user, session_id)
    
    # Find and revoke shared conversation
    shared = db.query(SharedConversation).filter(
        SharedConversation.token == token,
        SharedConversation.session_id == session.id,
    ).first()
    
    if not shared:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found"
        )
    
    shared.status = ShareStatus.REVOKED
    db.commit()
    
    logger.info(f"Revoked share link {token[:8]}... for session {session_id}")
    
    return {"message": "Share link revoked successfully"}


@router.get("/sessions/{session_id}/share")
def list_share_links(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    List all share links for a conversation.
    
    Args:
        session_id: Chat session ID
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        List of share links
    """
    # Verify session ownership
    session = get_chat_session_for_user(db, current_user, session_id)
    
    # Get all share links for this session
    shared_links = db.query(SharedConversation).filter(
        SharedConversation.session_id == session.id
    ).all()
    
    return [
        {
            "token": link.token,
            "share_url": f"/shared/{link.token}",
            "status": link.status.value,
            "expires_at": link.expires_at.isoformat() if link.expires_at else None,
            "created_at": link.created_at.isoformat(),
            "access_count": link.access_count,
        }
        for link in shared_links
    ]
