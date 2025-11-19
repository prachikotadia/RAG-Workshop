"""
JWT token creation and verification.

Phase 3 spec: Centralize JWT logic for creating and decoding tokens.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from app.config import get_settings

settings = get_settings()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT access token with expiration.
    
    Args:
        data: Dictionary containing token claims (must include 'sub' for email)
        expires_delta: Optional expiration timedelta. If None, uses settings default.
    
    Returns:
        Encoded JWT token string
    
    Example:
        token = create_access_token(
            data={"sub": "user@example.com", "user_id": 1},
            expires_delta=timedelta(minutes=60)
        )
    """
    to_encode = data.copy()  # Avoid mutating input
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    # Add expiration and issued-at claims
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow()
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a JWT access token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload dictionary
    
    Raises:
        JWTError: If token is invalid, expired, or malformed
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        raise JWTError(f"Invalid token: {str(e)}")


def create_refresh_token() -> str:
    """
    Create a refresh token (for refresh token endpoint).
    
    Returns:
        Encoded JWT refresh token string
    """
    import secrets
    # Generate a random token for refresh token
    return secrets.token_urlsafe(32)

