"""
Sentry integration for error tracking.
"""
import logging
import os

logger = logging.getLogger(__name__)

_sentry_initialized = False


def init_sentry(dsn: str = None, environment: str = "production"):
    """
    Initialize Sentry error tracking.
    
    Args:
        dsn: Sentry DSN (or use SENTRY_DSN env var)
        environment: Environment name
    """
    global _sentry_initialized
    
    if _sentry_initialized:
        return
    
    dsn = dsn or os.getenv("SENTRY_DSN")
    if not dsn:
        logger.info("Sentry DSN not provided, skipping Sentry initialization")
        return
    
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            ],
            traces_sample_rate=0.1,  # 10% of transactions
            profiles_sample_rate=0.1,  # 10% of profiles
        )
        
        _sentry_initialized = True
        logger.info("Sentry initialized successfully")
        
    except ImportError:
        logger.warning("sentry-sdk not installed. Install with: pip install sentry-sdk")
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}", exc_info=True)


def capture_exception(error: Exception, **kwargs):
    """Capture an exception in Sentry."""
    if not _sentry_initialized:
        return
    
    try:
        import sentry_sdk
        sentry_sdk.capture_exception(error, **kwargs)
    except Exception:
        pass  # Don't fail if Sentry capture fails


def capture_message(message: str, level: str = "info", **kwargs):
    """Capture a message in Sentry."""
    if not _sentry_initialized:
        return
    
    try:
        import sentry_sdk
        sentry_sdk.capture_message(message, level=level, **kwargs)
    except Exception:
        pass

