from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

settings = get_settings()

# Determine database type and set appropriate connection arguments
database_url_str = str(settings.database_url)
connect_args = {}

# Only add connection arguments for PostgreSQL
# Note: connect_timeout format varies by psycopg version
# For safety, we'll use minimal connect_args and rely on pool_pre_ping
if "postgresql" in database_url_str.lower():
    # PostgreSQL connection arguments
    # psycopg2-binary supports connect_timeout, but format may vary
    # Using empty connect_args and relying on pool_pre_ping for reliability
    connect_args = {}
elif "sqlite" in database_url_str.lower():
    # SQLite doesn't need connection arguments
    connect_args = {}
else:
    # For other databases, use empty connect_args
    connect_args = {}

# Enhanced engine configuration for reliability
# pool_pre_ping=True handles connection verification automatically
engine = create_engine(
    database_url_str,
    pool_pre_ping=True,  # Verify connections before using (handles timeouts)
    poolclass=QueuePool,
    pool_size=10,  # Number of connections to maintain
    max_overflow=20,  # Maximum connections beyond pool_size
    pool_recycle=3600,  # Recycle connections after 1 hour
    connect_args=connect_args
)

# Add connection event listeners for better error handling
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Set SQLite pragmas if using SQLite (for development)."""
    if "sqlite" in str(settings.database_url):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")
        dbapi_conn.execute("PRAGMA journal_mode=WAL")

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Log connection checkout for debugging."""
    logger.debug("Database connection checked out from pool")

@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """Log connection checkin for debugging."""
    logger.debug("Database connection returned to pool")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

