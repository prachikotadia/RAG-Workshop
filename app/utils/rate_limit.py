"""
Rate limiting middleware for per-user API rate limits.
"""
import time
from typing import Dict, Tuple
from collections import defaultdict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware that enforces per-user API rate limits.
    
    Uses sliding window algorithm with in-memory storage.
    For production, consider using Redis for distributed rate limiting.
    """
    
    def __init__(self, app, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        # In-memory storage: {user_id: [(timestamp, endpoint), ...]}
        self._request_history: Dict[int, list] = defaultdict(list)
        self._cleanup_interval = 3600  # Clean up old entries every hour
        self._last_cleanup = time.time()
    
    def _cleanup_old_entries(self):
        """Remove entries older than 1 hour."""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        cutoff_time = current_time - 3600  # 1 hour ago
        for user_id in list(self._request_history.keys()):
            self._request_history[user_id] = [
                (ts, endpoint) for ts, endpoint in self._request_history[user_id]
                if ts > cutoff_time
            ]
            # Remove empty entries
            if not self._request_history[user_id]:
                del self._request_history[user_id]
        
        self._last_cleanup = current_time
    
    def _check_rate_limit(self, user_id: int, endpoint: str) -> Tuple[bool, str]:
        """
        Check if user has exceeded rate limits.
        
        Returns:
            (allowed, message) tuple
        """
        current_time = time.time()
        
        # Clean up old entries periodically
        self._cleanup_old_entries()
        
        # Get user's request history
        history = self._request_history[user_id]
        
        # Filter to recent requests
        one_minute_ago = current_time - 60
        one_hour_ago = current_time - 3600
        
        recent_minute = [ts for ts, ep in history if ts > one_minute_ago]
        recent_hour = [ts for ts, ep in history if ts > one_hour_ago]
        
        # Check per-minute limit
        if len(recent_minute) >= self.requests_per_minute:
            return False, f"Rate limit exceeded: {self.requests_per_minute} requests per minute"
        
        # Check per-hour limit
        if len(recent_hour) >= self.requests_per_hour:
            return False, f"Rate limit exceeded: {self.requests_per_hour} requests per hour"
        
        # Add current request to history
        history.append((current_time, endpoint))
        
        # Keep only last hour of history
        history[:] = [(ts, ep) for ts, ep in history if ts > one_hour_ago]
        
        return True, ""
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and OPTIONS requests
        if request.url.path in ["/health", "/"] or request.method == "OPTIONS":
            return await call_next(request)
        
        # Get user ID from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        
        # If no user (public endpoint), skip rate limiting
        if user_id is None:
            return await call_next(request)
        
        # Check rate limit
        endpoint = f"{request.method} {request.url.path}"
        allowed, message = self._check_rate_limit(user_id, endpoint)
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for user {user_id} on {endpoint}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=message,
                headers={"Retry-After": "60"}
            )
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        
        return response

