"""
Answer quality feedback endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.base import get_db
from app.db import models
from app.db.feedback_models import AnswerFeedback, FeedbackType
from app.auth.dependencies import get_current_user

router = APIRouter()


class FeedbackCreate(BaseModel):
    """Request model for creating feedback."""
    feedback_type: FeedbackType
    rating: Optional[int] = None  # 1-5 scale
    comment: Optional[str] = None


@router.post("/messages/{message_id}/feedback", response_model=dict)
async def create_feedback(
    message_id: int,
    feedback: FeedbackCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submit feedback on an answer.
    
    Args:
        message_id: Chat message ID
        feedback: Feedback data
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Created feedback
    """
    # Verify message exists and belongs to user
    message = (
        db.query(models.ChatMessage)
        .join(models.ChatSession)
        .filter(
            models.ChatMessage.id == message_id,
            models.ChatSession.user_id == current_user.id
        )
        .first()
    )
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Validate rating
    if feedback.rating is not None and (feedback.rating < 1 or feedback.rating > 5):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be between 1 and 5"
        )
    
    # Get confidence score from message metadata if available
    # (would need to store in message metadata)
    confidence_score = None
    
    # Create feedback
    answer_feedback = AnswerFeedback(
        message_id=message_id,
        user_id=current_user.id,
        feedback_type=feedback.feedback_type,
        rating=feedback.rating,
        comment=feedback.comment,
        confidence_score=confidence_score,
    )
    
    db.add(answer_feedback)
    db.commit()
    db.refresh(answer_feedback)
    
    return {
        "id": answer_feedback.id,
        "message_id": answer_feedback.message_id,
        "feedback_type": answer_feedback.feedback_type.value,
        "rating": answer_feedback.rating,
        "created_at": answer_feedback.created_at.isoformat() if answer_feedback.created_at else None,
    }


@router.get("/feedback/stats")
async def get_feedback_stats(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get feedback statistics for the user.
    
    Returns:
        Feedback statistics
    """
    feedbacks = (
        db.query(AnswerFeedback)
        .filter(AnswerFeedback.user_id == current_user.id)
        .all()
    )
    
    total = len(feedbacks)
    positive = len([f for f in feedbacks if f.feedback_type == FeedbackType.POSITIVE])
    negative = len([f for f in feedbacks if f.feedback_type == FeedbackType.NEGATIVE])
    neutral = len([f for f in feedbacks if f.feedback_type == FeedbackType.NEUTRAL])
    
    ratings = [f.rating for f in feedbacks if f.rating is not None]
    avg_rating = sum(ratings) / len(ratings) if ratings else None
    
    return {
        "total_feedback": total,
        "positive": positive,
        "negative": negative,
        "neutral": neutral,
        "average_rating": round(avg_rating, 2) if avg_rating else None,
    }

