"""Initialize the database with tables."""
from app.db.base import engine, Base
from app.db.models import User, Document, DocumentChunk, ChatSession, ChatMessage

if __name__ == "__main__":
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

