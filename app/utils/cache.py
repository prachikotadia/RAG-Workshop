"""
Query result caching for improved performance and cost reduction.

Supports both in-memory cache (default) and Redis (optional for production).
Caches both query results (1 hour TTL) and embeddings (24 hour TTL).
"""
import hashlib
import json
import time
import logging
import os
from typing import Any, Optional, Dict, List
from functools import wraps
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Try to import Redis (optional)
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.info("Redis not available, using in-memory cache")

# Redis connection (if available)
_redis_client: Optional[Any] = None

# In-memory cache (fallback when Redis not available)
_cache: Dict[str, Dict[str, Any]] = {}
_embedding_cache: Dict[str, Dict[str, Any]] = {}  # Separate cache for embeddings
_cache_stats = {
    "hits": 0,
    "misses": 0,
    "sets": 0,
    "evictions": 0,
    "embedding_hits": 0,
    "embedding_misses": 0,
}


def _init_redis() -> Optional[Any]:
    """Initialize Redis client if available."""
    if not REDIS_AVAILABLE:
        return None
    
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        client = redis.from_url(redis_url, decode_responses=False)
        client.ping()
        logger.info("Redis cache initialized successfully")
        return client
    except Exception as e:
        logger.warning(f"Redis not available, using in-memory cache: {e}")
        return None


def _get_redis_client() -> Optional[Any]:
    """Get or initialize Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = _init_redis()
    return _redis_client


def _generate_cache_key(query: str, user_id: int, top_k: int = 10) -> str:
    """Generate a cache key from query and parameters."""
    key_data = f"{user_id}:{query}:{top_k}"
    return hashlib.sha256(key_data.encode()).hexdigest()


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    total_requests = _cache_stats["hits"] + _cache_stats["misses"]
    hit_rate = (_cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0
    
    total_embedding_requests = _cache_stats["embedding_hits"] + _cache_stats["embedding_misses"]
    embedding_hit_rate = (_cache_stats["embedding_hits"] / total_embedding_requests * 100) if total_embedding_requests > 0 else 0
    
    redis_client = _get_redis_client()
    cache_type = "redis" if redis_client else "memory"
    
    return {
        "hits": _cache_stats["hits"],
        "misses": _cache_stats["misses"],
        "sets": _cache_stats["sets"],
        "evictions": _cache_stats["evictions"],
        "hit_rate": round(hit_rate, 2),
        "total_requests": total_requests,
        "cache_size": len(_cache),
        "cache_type": cache_type,
        "embedding_hits": _cache_stats["embedding_hits"],
        "embedding_misses": _cache_stats["embedding_misses"],
        "embedding_hit_rate": round(embedding_hit_rate, 2),
        "embedding_cache_size": len(_embedding_cache),
    }


def get_cached_embedding(query: str, user_id: int, ttl: int = 86400) -> Optional[List[float]]:
    """
    Get cached embedding for a query.
    
    Args:
        query: User's query string
        user_id: User ID
        ttl: Time-to-live in seconds (default: 24 hours = 86400)
    
    Returns:
        Cached embedding vector if found and valid, None otherwise
    """
    cache_key = f"embedding:{user_id}:{hashlib.sha256(query.encode()).hexdigest()}"
    redis_client = _get_redis_client()
    
    if redis_client:
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                embedding = json.loads(cached_data)
                _cache_stats["embedding_hits"] += 1
                logger.debug(f"Embedding cache hit for query: {query[:50]}...")
                return embedding
        except Exception as e:
            logger.warning(f"Redis error, falling back to memory: {e}")
    
    # Fallback to in-memory cache
    if cache_key in _embedding_cache:
        cached_data = _embedding_cache[cache_key]
        cached_time = cached_data.get("timestamp", 0)
        age = time.time() - cached_time
        
        if age <= ttl:
            _cache_stats["embedding_hits"] += 1
            logger.debug(f"Embedding cache hit (memory) for query: {query[:50]}...")
            return cached_data.get("embedding")
        else:
            del _embedding_cache[cache_key]
            _cache_stats["evictions"] += 1
    
    _cache_stats["embedding_misses"] += 1
    return None


def set_cached_embedding(query: str, user_id: int, embedding: List[float], ttl: int = 86400) -> None:
    """
    Cache an embedding vector.
    
    Args:
        query: User's query string
        user_id: User ID
        embedding: Embedding vector to cache
        ttl: Time-to-live in seconds (default: 24 hours)
    """
    cache_key = f"embedding:{user_id}:{hashlib.sha256(query.encode()).hexdigest()}"
    redis_client = _get_redis_client()
    
    if redis_client:
        try:
            redis_client.setex(
                cache_key,
                ttl,
                json.dumps(embedding)
            )
            logger.debug(f"Cached embedding (Redis) for query: {query[:50]}...")
            return
        except Exception as e:
            logger.warning(f"Redis error, falling back to memory: {e}")
    
    # Fallback to in-memory cache
    _embedding_cache[cache_key] = {
        "embedding": embedding,
        "timestamp": time.time(),
        "query": query[:100],
        "user_id": user_id,
    }
    logger.debug(f"Cached embedding (memory) for query: {query[:50]}...")
    
    # Simple eviction for embedding cache
    if len(_embedding_cache) > 500:
        sorted_items = sorted(_embedding_cache.items(), key=lambda x: x[1].get("timestamp", 0))
        to_remove = len(sorted_items) // 10
        for key, _ in sorted_items[:to_remove]:
            del _embedding_cache[key]
            _cache_stats["evictions"] += 1


def get_cached_result(query: str, user_id: int, top_k: int = 10, ttl: int = 3600) -> Optional[Any]:
    """
    Get cached query result if available and not expired.
    
    Args:
        query: User's query string
        user_id: User ID
        top_k: Number of results requested
        ttl: Time-to-live in seconds (default: 1 hour)
    
    Returns:
        Cached result if found and valid, None otherwise
    """
    cache_key = _generate_cache_key(query, user_id, top_k)
    redis_client = _get_redis_client()
    
    if redis_client:
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                result = json.loads(cached_data)
                _cache_stats["hits"] += 1
                logger.debug(f"Cache hit (Redis) for query: {query[:50]}...")
                return result
        except Exception as e:
            logger.warning(f"Redis error, falling back to memory: {e}")
    
    # Fallback to in-memory cache
    if cache_key not in _cache:
        _cache_stats["misses"] += 1
        return None
    
    cached_data = _cache[cache_key]
    cached_time = cached_data.get("timestamp", 0)
    age = time.time() - cached_time
    
    if age > ttl:
        # Cache expired
        del _cache[cache_key]
        _cache_stats["evictions"] += 1
        _cache_stats["misses"] += 1
        logger.debug(f"Cache expired for query: {query[:50]}...")
        return None
    
    _cache_stats["hits"] += 1
    logger.debug(f"Cache hit (memory) for query: {query[:50]}... (age: {age:.1f}s)")
    return cached_data.get("result")


def set_cached_result(query: str, user_id: int, result: Any, top_k: int = 10, ttl: int = 3600) -> None:
    """
    Cache a query result.
    
    Args:
        query: User's query string
        user_id: User ID
        result: Result to cache
        top_k: Number of results
        ttl: Time-to-live in seconds (default: 1 hour)
    """
    cache_key = _generate_cache_key(query, user_id, top_k)
    redis_client = _get_redis_client()
    
    if redis_client:
        try:
            # Serialize result for Redis
            serialized = json.dumps(result, default=str)
            redis_client.setex(cache_key, ttl, serialized)
            _cache_stats["sets"] += 1
            logger.debug(f"Cached result (Redis) for query: {query[:50]}...")
            return
        except Exception as e:
            logger.warning(f"Redis error, falling back to memory: {e}")
    
    # Fallback to in-memory cache
    _cache[cache_key] = {
        "result": result,
        "timestamp": time.time(),
        "query": query[:100],  # Store first 100 chars for debugging
        "user_id": user_id,
    }
    
    _cache_stats["sets"] += 1
    logger.debug(f"Cached result (memory) for query: {query[:50]}...")
    
    # Simple eviction: if cache is too large, remove oldest 10%
    if len(_cache) > 1000:
        sorted_items = sorted(_cache.items(), key=lambda x: x[1].get("timestamp", 0))
        to_remove = len(sorted_items) // 10
        for key, _ in sorted_items[:to_remove]:
            del _cache[key]
            _cache_stats["evictions"] += 1
        logger.info(f"Evicted {to_remove} old cache entries")


def invalidate_user_cache(user_id: int) -> None:
    """Invalidate all cache entries for a user (e.g., after document upload)."""
    redis_client = _get_redis_client()
    
    if redis_client:
        try:
            # Use pattern matching to find all keys for this user
            pattern = f"*:{user_id}:*"
            keys = list(redis_client.scan_iter(match=pattern))
            if keys:
                redis_client.delete(*keys)
                _cache_stats["evictions"] += len(keys)
                logger.info(f"Invalidated {len(keys)} cache entries (Redis) for user {user_id}")
            
            # Also invalidate embedding cache
            embedding_pattern = f"embedding:{user_id}:*"
            embedding_keys = list(redis_client.scan_iter(match=embedding_pattern))
            if embedding_keys:
                redis_client.delete(*embedding_keys)
                logger.info(f"Invalidated {len(embedding_keys)} embedding cache entries (Redis) for user {user_id}")
            return
        except Exception as e:
            logger.warning(f"Redis error during invalidation: {e}")
    
    # Fallback to in-memory cache
    keys_to_remove = [
        key for key, data in _cache.items()
        if data.get("user_id") == user_id
    ]
    
    for key in keys_to_remove:
        del _cache[key]
        _cache_stats["evictions"] += 1
    
    # Also invalidate embedding cache
    embedding_keys_to_remove = [
        key for key, data in _embedding_cache.items()
        if data.get("user_id") == user_id
    ]
    
    for key in embedding_keys_to_remove:
        del _embedding_cache[key]
        _cache_stats["evictions"] += 1
    
    logger.info(f"Invalidated {len(keys_to_remove)} cache entries and {len(embedding_keys_to_remove)} embedding entries (memory) for user {user_id}")


def clear_cache() -> None:
    """Clear all cached results."""
    count = len(_cache)
    _cache.clear()
    _cache_stats["evictions"] += count
    logger.info(f"Cleared {count} cache entries")


def cache_query_result(ttl: int = 3600):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time-to-live in seconds
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract query and user_id from function arguments
            # Assumes function signature: (self, db, user, session, question, ...)
            if len(args) >= 4:
                user = args[2] if len(args) > 2 else None
                question = args[3] if len(args) > 3 else None
                top_k = kwargs.get("top_k", 10)
                
                if user and question:
                    # Try to get from cache
                    cached = get_cached_result(question, user.id, top_k, ttl)
                    if cached is not None:
                        logger.info(f"Returning cached result for user {user.id}")
                        return cached
                    
                    # Call function and cache result
                    result = await func(*args, **kwargs)
                    set_cached_result(question, user.id, result, top_k)
                    return result
            
            # Fallback: just call function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator
