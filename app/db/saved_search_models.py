"""
Database models for saved search queries.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class SavedSearch(Base):
    """
    Model for saved search queries.
    
    Users can save frequently used search queries with filters
    for quick access.
    """
    __tablename__ = "saved_searches"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # User-friendly name for the search
    query = Column(String(500), nullable=True)  # Search text query
    filters = Column(JSON, default={})  # Store all filter parameters as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    use_count = Column(Integer, default=0)  # Track how often it's used
    
    def __repr__(self):
        return f"<SavedSearch(id={self.id}, name='{self.name}', user_id={self.user_id})>"
