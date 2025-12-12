"""
Database connection retry utilities for improved reliability.
"""
import logging
import time
from functools import wraps
from typing import Callable, TypeVar, Any
from sqlalchemy.exc import OperationalError, DisconnectionError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0
DEFAULT_BACKOFF_MULTIPLIER = 2.0


def retry_db_operation(
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER,
    retryable_errors: tuple = (OperationalError, DisconnectionError),
):
    """
    Decorator to retry database operations on connection errors.
    
    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries (seconds)
        backoff_multiplier: Multiplier for exponential backoff
        retryable_errors: Tuple of exception types to retry on
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = retry_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_errors as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Database operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        time.sleep(delay)
                        delay *= backoff_multiplier
                        
                        # Refresh database session if available
                        for arg in args:
                            if isinstance(arg, Session):
                                try:
                                    arg.rollback()
                                    arg.close()
                                except Exception:
                                    pass
                    else:
                        logger.error(
                            f"Database operation failed after {max_retries + 1} attempts: {e}"
                        )
                except Exception as e:
                    # Non-retryable error, re-raise immediately
                    raise
            
            # If we get here, all retries failed
            raise last_exception
        
        return wrapper
    return decorator


def ensure_db_connection(db: Session) -> bool:
    """
    Ensure database connection is alive, reconnect if necessary.
    
    Args:
        db: SQLAlchemy session
        
    Returns:
        True if connection is healthy, False otherwise
    """
    try:
        # Simple query to test connection
        db.execute("SELECT 1")
        return True
    except (OperationalError, DisconnectionError) as e:
        logger.warning(f"Database connection lost: {e}. Attempting to reconnect...")
        try:
            db.rollback()
            db.close()
            # Session will be recreated on next use
            return False
        except Exception as reconnect_error:
            logger.error(f"Failed to reconnect to database: {reconnect_error}")
            return False
    except Exception as e:
        logger.error(f"Unexpected error checking database connection: {e}")
        return False
