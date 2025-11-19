"""Background task utilities."""
from fastapi import BackgroundTasks
from typing import Callable, Any
import asyncio
import logging

logger = logging.getLogger(__name__)


async def run_background_task(func: Callable, *args, **kwargs):
    """Run a function as a background task."""
    try:
        if asyncio.iscoroutinefunction(func):
            await func(*args, **kwargs)
        else:
            func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Background task failed: {e}", exc_info=True)

