"""
Feedback models for answer quality rating.
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base import Base


class FeedbackType(str, enum.Enum):
    """Feedback type enum."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class AnswerFeedback(Base):
    """Model for storing user feedback on answers."""
    __tablename__ = "answer_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    feedback_type = Column(Enum(FeedbackType), nullable=False)
    rating = Column(Integer, nullable=True)  # 1-5 scale
    comment = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)  # Confidence score at time of feedback
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships (using string references to avoid circular imports)
    # message = relationship("ChatMessage", backref="feedback")
    # user = relationship("User", backref="feedback")

