"""
Webhook management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import secrets

from app.db.base import get_db
from app.db import models
from app.admin.webhooks import Webhook, trigger_webhook
from app.auth.dependencies import get_current_user

router = APIRouter()


class WebhookCreate(BaseModel):
    """Request model for creating a webhook."""
    url: str
    events: List[str]  # e.g., ["document.uploaded", "chat.message"]
    secret: Optional[str] = None


class WebhookUpdate(BaseModel):
    """Request model for updating a webhook."""
    url: Optional[str] = None
    events: Optional[List[str]] = None
    active: Optional[bool] = None


@router.post("/webhooks", status_code=status.HTTP_201_CREATED)
async def create_webhook(
    webhook_data: WebhookCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new webhook."""
    # Generate secret if not provided
    secret = webhook_data.secret or secrets.token_urlsafe(32)
    
    webhook = Webhook(
        user_id=current_user.id,
        url=webhook_data.url,
        events=webhook_data.events,
        secret=secret,
        active=True,
    )
    
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    
    return {
        "id": webhook.id,
        "url": webhook.url,
        "events": webhook.events,
        "active": webhook.active,
        "created_at": webhook.created_at.isoformat() if webhook.created_at else None,
    }


@router.get("/webhooks")
async def list_webhooks(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all webhooks for the current user."""
    webhooks = (
        db.query(Webhook)
        .filter(Webhook.user_id == current_user.id)
        .all()
    )
    
    return [
        {
            "id": w.id,
            "url": w.url,
            "events": w.events,
            "active": w.active,
            "created_at": w.created_at.isoformat() if w.created_at else None,
            "last_triggered": w.last_triggered.isoformat() if w.last_triggered else None,
        }
        for w in webhooks
    ]


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a webhook."""
    webhook = (
        db.query(Webhook)
        .filter(
            Webhook.id == webhook_id,
            Webhook.user_id == current_user.id
        )
        .first()
    )
    
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )
    
    db.delete(webhook)
    db.commit()
    
    return {"message": "Webhook deleted"}

