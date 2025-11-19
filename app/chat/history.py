"""
Chat history management.

Phase 7 spec: Fetch recent chat messages for RAG context.
"""
from typing import List, Dict
from sqlalchemy.orm import Session
from app.db import models


def get_recent_messages_for_session(
    db: Session,
    session: models.ChatSession,
    limit: int = 10,
    exclude_message_id: int | None = None,
) -> List[Dict[str, str]]:
    """
    Fetch the most recent messages for a chat session and convert them into
    a list of dicts with 'role' and 'content' keys, suitable for LLM prompts.
    
    Messages should be ordered chronologically and truncated to the last `limit`.
    Optionally exclude a specific message by ID (useful to exclude the current user message).
    
    Args:
        db: Database session
        session: Chat session model instance
        limit: Maximum number of messages to fetch
        exclude_message_id: Optional message ID to exclude from history
    
    Returns:
        List of message dicts with 'role' and 'content' keys
        Ordered chronologically (oldest first)
    """
    # Query all messages for the session, ordered chronologically
    query = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session.id)
    )
    
    # Exclude specific message if provided
    if exclude_message_id is not None:
        query = query.filter(models.ChatMessage.id != exclude_message_id)
    
    messages = query.order_by(models.ChatMessage.created_at.asc()).all()
    
    # Slice to last `limit` messages
    messages = messages[-limit:] if len(messages) > limit else messages
    
    # Convert to list of dicts
    history = [
        {"role": m.role.value, "content": m.content}
        for m in messages
    ]
    
    return history


# Backward compatibility alias
def get_recent_messages(
    db: Session,
    session: models.ChatSession,
    limit: int = 10,
    exclude_message_id: int | None = None,
) -> List[Dict[str, str]]:
    """Backward compatibility alias for get_recent_messages_for_session."""
    return get_recent_messages_for_session(db, session, limit, exclude_message_id)

