"""
Webhook system for notifying external systems of events.
"""
import logging
import httpx
from typing import List, Dict, Any, Optional
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.base import Base

logger = logging.getLogger(__name__)


class Webhook(Base):
    """Webhook configuration model."""
    __tablename__ = "webhooks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    url = Column(String(500), nullable=False)
    events = Column(JSON, default=[])  # List of event types to subscribe to
    secret = Column(String(255), nullable=True)  # Secret for signing payloads
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_triggered = Column(DateTime, nullable=True)


async def trigger_webhook(
    db: Session,
    user_id: int,
    event_type: str,
    payload: Dict[str, Any]
) -> None:
    """
    Trigger webhooks for a user and event type.
    
    Args:
        db: Database session
        user_id: User ID
        event_type: Event type (e.g., "document.uploaded", "chat.message")
        payload: Event payload
    """
    webhooks = (
        db.query(Webhook)
        .filter(
            Webhook.user_id == user_id,
            Webhook.active == True
        )
        .all()
    )
    
    for webhook in webhooks:
        # Check if webhook subscribes to this event
        if event_type not in webhook.events:
            continue
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    webhook.url,
                    json={
                        "event": event_type,
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": payload,
                    },
                    headers={
                        "X-Webhook-Event": event_type,
                        "User-Agent": "RAG-Workspace-Webhook/1.0",
                    }
                )
                
                if response.status_code < 400:
                    logger.info(f"Webhook {webhook.id} triggered successfully for {event_type}")
                    webhook.last_triggered = datetime.utcnow()
                    db.commit()
                else:
                    logger.warning(f"Webhook {webhook.id} returned {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Failed to trigger webhook {webhook.id}: {e}", exc_info=True)

