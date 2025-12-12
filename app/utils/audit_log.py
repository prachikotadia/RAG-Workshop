"""
Audit logging system to track all user actions.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text
from fastapi import Request

from app.db.base import Base

logger = logging.getLogger(__name__)


class AuditLog(Base):
    """Audit log model for tracking user actions."""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)  # e.g., "document_upload", "chat_message", "document_delete"
    resource_type = Column(String(50), nullable=True)  # e.g., "document", "chat_session", "user"
    resource_id = Column(Integer, nullable=True)  # ID of the affected resource
    endpoint = Column(String(255), nullable=False)  # API endpoint
    method = Column(String(10), nullable=False)  # HTTP method
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    event_metadata = Column(JSON, default={})  # Additional context (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Additional fields for GDPR compliance
    data_accessed = Column(JSON, default=[])  # What data was accessed
    data_modified = Column(JSON, default=[])  # What data was modified
    data_deleted = Column(JSON, default=[])  # What data was deleted


def log_audit_event(
    db: Session,
    user_id: int,
    action: str,
    endpoint: str,
    method: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    data_accessed: Optional[list] = None,
    data_modified: Optional[list] = None,
    data_deleted: Optional[list] = None,
) -> None:
    """
    Log an audit event to the database.
    
    Args:
        db: Database session
        user_id: User ID performing the action
        action: Action name (e.g., "document_upload", "chat_message")
        endpoint: API endpoint path
        method: HTTP method
        resource_type: Type of resource affected
        resource_id: ID of resource affected
        ip_address: Client IP address
        user_agent: User agent string
        metadata: Additional metadata
        data_accessed: List of data items accessed
        data_modified: List of data items modified
        data_deleted: List of data items deleted
    """
    try:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            endpoint=endpoint,
            method=method,
            ip_address=ip_address,
            user_agent=user_agent,
            event_metadata=metadata or {},
            data_accessed=data_accessed or [],
            data_modified=data_modified or [],
            data_deleted=data_deleted or [],
        )
        db.add(audit_log)
        db.commit()
        
        # Also log to application logger
        logger.info(
            f"AUDIT: user_id={user_id} action={action} "
            f"resource={resource_type}:{resource_id} endpoint={method} {endpoint}"
        )
    except Exception as e:
        logger.error(f"Failed to log audit event: {e}", exc_info=True)
        # Don't fail the request if audit logging fails
        db.rollback()


class AuditLogMiddleware:
    """Middleware to automatically log audit events."""
    
    @staticmethod
    async def log_request(
        request: Request,
        db: Session,
        user_id: Optional[int],
        action: Optional[str] = None,
    ) -> None:
        """
        Log a request as an audit event.
        
        Args:
            request: FastAPI request object
            db: Database session
            user_id: User ID (if authenticated)
            action: Optional action name override
        """
        if not user_id:
            return  # Don't log unauthenticated requests
        
        # Determine action from endpoint
        if action is None:
            path = request.url.path
            if "/documents/upload" in path:
                action = "document_upload"
            elif "/documents/" in path and request.method == "DELETE":
                action = "document_delete"
            elif "/chat/sessions" in path and "/message" in path:
                action = "chat_message"
            elif "/auth/login" in path:
                action = "user_login"
            elif "/auth/signup" in path:
                action = "user_signup"
            else:
                action = f"{request.method.lower()}_{path.split('/')[-1]}"
        
        # Extract resource info
        resource_type = None
        resource_id = None
        path_parts = request.url.path.split("/")
        if len(path_parts) >= 3:
            resource_type = path_parts[1]  # e.g., "documents", "chat"
            try:
                resource_id = int(path_parts[2])
            except (ValueError, IndexError):
                pass
        
        # Get client info
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        log_audit_event(
            db=db,
            user_id=user_id,
            action=action,
            endpoint=request.url.path,
            method=request.method,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

