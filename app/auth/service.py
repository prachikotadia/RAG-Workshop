"""
Authentication service for user management and password handling.

Phase 3 spec: Business logic for signup, login, and password operations.
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import timedelta
import bcrypt
from app.db import models
from app.db.schemas import UserCreate
from app.auth.jwt import create_access_token
from app.config import get_settings

settings = get_settings()


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt directly.
    
    Args:
        password: Plain text password (will be truncated to 72 bytes if needed)
    
    Returns:
        Hashed password string
    """
    # Bcrypt has a 72-byte limit, so truncate if necessary
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    # Generate salt and hash
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
    
    Returns:
        True if password matches, False otherwise
    """
    try:
        password_bytes = plain_password.encode('utf-8')
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


def get_user_by_email(db: Session, email: str) -> models.User | None:
    """
    Get user by email (case-insensitive).
    
    Gmail and most email providers treat emails as case-insensitive,
    so we normalize to lowercase for consistent matching.
    """
    email_lower = email.lower().strip()
    return db.query(models.User).filter(models.User.email.ilike(email_lower)).first()


def create_user(db: Session, user_in: UserCreate) -> models.User:
    """
    Create a new user account.
    
    Checks if email already exists (case-insensitive), hashes password, and creates user.
    Email is normalized to lowercase for consistent storage and matching.
    
    Args:
        db: Database session
        user_in: UserCreate schema with email and password
    
    Returns:
        Created User model instance
    
    Raises:
        HTTPException: If email already exists (400)
    """
    # Normalize email to lowercase (Gmail and most providers are case-insensitive)
    email_normalized = user_in.email.lower().strip()
    
    # Check if email already exists (case-insensitive)
    existing = db.query(models.User).filter(models.User.email.ilike(email_normalized)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered. Please use a different email or try logging in."
        )
    
    # Hash password
    hashed_password = get_password_hash(user_in.password)
    
    # Create user with normalized email
    db_user = models.User(
        email=email_normalized,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, email: str, password: str) -> models.User | None:
    """
    Authenticate a user by email and password.
    
    Email matching is case-insensitive (Gmail and most providers treat emails as case-insensitive).
    
    Args:
        db: Database session
        email: User email (will be normalized to lowercase)
        password: Plain text password
    
    Returns:
        User model instance if credentials are valid, None otherwise
    """
    # Normalize email for case-insensitive matching
    email_normalized = email.lower().strip()
    user = get_user_by_email(db, email_normalized)
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    return user


def create_user_access_token(user: models.User) -> str:
    """
    Build a JWT access token for a user.
    
    Token payload includes:
    - sub: user email (subject)
    - user_id: user ID
    
    Args:
        user: User model instance
    
    Returns:
        JWT access token string
    """
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires,
    )
    return token


def update_user_password(db: Session, user: models.User, new_password: str):
    """Update user password."""
    user.hashed_password = get_password_hash(new_password)
    db.commit()


def delete_user_account(db: Session, user: models.User):
    """Delete user account and all associated data."""
    # Cascade deletes will handle documents, chunks, sessions, messages
    # But we need to clean up vector store and files
    from pathlib import Path
    from app.config import get_settings
    
    settings = get_settings()
    
    # Delete vector store
    try:
        from app.vectorstore.faiss_store import get_vector_store
        vector_store = get_vector_store()
        # Get all chunk IDs for this user
        chunk_ids = []
        for doc in user.documents:
            chunk_ids.extend([chunk.id for chunk in doc.chunks])
        if chunk_ids:
            vector_store.remove_document_chunks(
                user_id=user.id,
                document_chunk_ids=chunk_ids
            )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error removing vector store for user {user.id}: {e}")
    
    # Delete user storage directory
    user_storage_dir = Path(settings.storage_base_dir) / f"user_{user.id}"
    if user_storage_dir.exists():
        import shutil
        shutil.rmtree(user_storage_dir)
    
    # Delete user from database (cascade will handle related records)
    db.delete(user)
    db.commit()


def create_refresh_token_record(db: Session, user_id: int, token: str):
    """Create a refresh token record in the database."""
    from app.db.models import RefreshToken
    from datetime import datetime, timedelta
    from app.config import get_settings
    
    settings = get_settings()
    expires_at = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    
    refresh_token = RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at
    )
    db.add(refresh_token)
    db.commit()
    return refresh_token


def verify_refresh_token(db: Session, token: str) -> models.User:
    """Verify refresh token and return user."""
    from app.db.models import RefreshToken
    from app.utils.exceptions import AuthenticationError
    from datetime import datetime
    
    refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token == token,
        RefreshToken.expires_at > datetime.utcnow()
    ).first()
    
    if not refresh_token:
        raise AuthenticationError("Invalid or expired refresh token")
    
    user = db.query(models.User).filter(models.User.id == refresh_token.user_id).first()
    if not user:
        raise AuthenticationError("User not found")
    
    return user


def revoke_refresh_token(db: Session, token: str):
    """Revoke a refresh token."""
    from app.db.models import RefreshToken
    
    refresh_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    if refresh_token:
        db.delete(refresh_token)
        db.commit()

