"""Retry utilities for API calls."""
import asyncio
import logging
from typing import Callable, TypeVar, Optional
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


async def retry_async(
    func: Callable,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> T:
    """
    Retry an async function with exponential backoff.
    
    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry on
    
    Returns:
        Result of the function call
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except exceptions as e:
            last_exception = e
            if attempt < max_retries:
                wait_time = delay * (backoff ** attempt)
                logger.warning(
                    f"Retry attempt {attempt + 1}/{max_retries} after {wait_time:.2f}s: {str(e)}"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Max retries ({max_retries}) exceeded: {str(e)}")
                raise
    
    raise last_exception


def retry_sync(
    func: Callable,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> T:
    """
    Retry a sync function with exponential backoff.
    
    Args:
        func: Sync function to retry
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry on
    
    Returns:
        Result of the function call
    """
    import time
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            if attempt < max_retries:
                wait_time = delay * (backoff ** attempt)
                logger.warning(
                    f"Retry attempt {attempt + 1}/{max_retries} after {wait_time:.2f}s: {str(e)}"
                )
                time.sleep(wait_time)
            else:
                logger.error(f"Max retries ({max_retries}) exceeded: {str(e)}")
                raise
    
    raise last_exception

