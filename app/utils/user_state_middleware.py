"""
Middleware to set user_id in request.state for rate limiting and audit logging.
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError
from app.auth.jwt import decode_access_token
from app.db.schemas import TokenPayload


class UserStateMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract user_id from JWT and set it in request.state.
    This allows rate limiting and audit logging to access user_id without
    requiring authentication on every endpoint.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Try to extract user_id from JWT token
        user_id = None
        
        # Skip for public endpoints
        if request.url.path in ["/health", "/", "/auth/login", "/auth/signup"]:
            request.state.user_id = None
            return await call_next(request)
        
        # Extract token from Authorization header
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = decode_access_token(token)
                token_data = TokenPayload(
                    sub=payload.get("sub"),
                    user_id=payload.get("user_id"),
                    exp=payload.get("exp")
                )
                user_id = token_data.user_id
            except (JWTError, Exception):
                # Invalid token, but don't fail - let auth dependency handle it
                pass
        
        # Set user_id in request state
        request.state.user_id = user_id
        
        return await call_next(request)

