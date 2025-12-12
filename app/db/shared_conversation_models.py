"""
Database models for shareable conversation links.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import enum

from app.db.base import Base


class ShareStatus(str, enum.Enum):
    """Status of a shared conversation link."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class SharedConversation(Base):
    """
    Model for shareable conversation links.
    
    Each shared conversation has a unique token that can be used to
    access a read-only view of the conversation.
    """
    __tablename__ = "shared_conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    token = Column(String(64), unique=True, nullable=False, index=True)
    status = Column(Enum(ShareStatus), default=ShareStatus.ACTIVE)
    expires_at = Column(DateTime, nullable=True)  # None = never expires
    created_at = Column(DateTime, default=datetime.utcnow)
    access_count = Column(Integer, default=0)  # Track how many times it was accessed
    
    # Relationship to chat session (lazy import to avoid circular dependency)
    # session = relationship("ChatSession", backref="shared_links")
