"""
Graceful shutdown handling for the FastAPI application.
"""
import asyncio
import logging
import signal
from typing import Callable, List

logger = logging.getLogger(__name__)

_shutdown_handlers: List[Callable] = []


def register_shutdown_handler(handler: Callable):
    """Register a function to be called on shutdown."""
    _shutdown_handlers.append(handler)
    logger.debug(f"Registered shutdown handler: {handler.__name__}")


async def run_shutdown_handlers():
    """Run all registered shutdown handlers."""
    logger.info("Running shutdown handlers...")
    for handler in _shutdown_handlers:
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler()
            else:
                handler()
            logger.debug(f"Shutdown handler {handler.__name__} completed")
        except Exception as e:
            logger.error(f"Error in shutdown handler {handler.__name__}: {e}", exc_info=True)


def setup_signal_handlers(app):
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        # Create a task to run shutdown handlers
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(run_shutdown_handlers())
        else:
            loop.run_until_complete(run_shutdown_handlers())
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Signal handlers registered for graceful shutdown")
