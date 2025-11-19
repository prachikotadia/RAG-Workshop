import logging
import sys
from app.config import get_settings

settings = get_settings()


def setup_logging():
    """Configure application logging."""
    log_level = logging.DEBUG if settings.environment == "dev" else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set third-party loggers to WARNING
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

