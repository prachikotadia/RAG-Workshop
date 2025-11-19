"""
FastAPI dependency for authentication.

Phase 3 spec: get_current_user dependency that validates JWT and loads user.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError
from app.db.base import get_db
from app.db import models
from app.db.schemas import TokenPayload
from app.auth.jwt import decode_access_token
from app.config import get_settings

settings = get_settings()

# OAuth2 scheme for extracting Bearer token from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """
    FastAPI dependency to get the current authenticated user.
    
    Decodes JWT, validates it, and loads the corresponding user from the DB.
    On any failure, raises HTTP 401 with WWW-Authenticate: Bearer header.
    
    Args:
        token: JWT token extracted from Authorization header
        db: Database session
    
    Returns:
        User model instance
    
    Raises:
        HTTPException: 401 if token is invalid, expired, or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode token
        payload = decode_access_token(token)
        
        # Parse into TokenPayload
        token_data = TokenPayload(
            sub=payload.get("sub"),
            user_id=payload.get("user_id"),
            exp=payload.get("exp")
        )
        
        # Ensure sub (email) is present
        if token_data.sub is None:
            raise credentials_exception
        
    except JWTError:
        raise credentials_exception
    
    # Query user by email (case-insensitive, since email is stored in lowercase)
    email_normalized = token_data.sub.lower().strip() if token_data.sub else None
    if not email_normalized:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.email.ilike(email_normalized)).first()
    if user is None:
        raise credentials_exception
    
    return user

