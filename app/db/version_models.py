"""
Database models for document versioning.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class DocumentVersion(Base):
    """
    Model for document versions.
    
    Tracks different versions of a document over time, allowing
    rollback and diff viewing.
    """
    __tablename__ = "document_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)  # 1, 2, 3, etc.
    
    # Version metadata
    title = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=True)
    file_type = Column(String(50), nullable=True)
    
    # Content snapshot (can store full content or reference to storage)
    content_hash = Column(String(64), nullable=False)  # SHA-256 hash of content
    storage_path = Column(String(500), nullable=True)  # Path to stored version file
    
    # Version info
    created_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    change_description = Column(Text, nullable=True)  # User-provided description of changes
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    chunks_snapshot = Column(JSON, nullable=True)  # Snapshot of chunk metadata
    
    def __repr__(self):
        return f"<DocumentVersion(id={self.id}, document_id={self.document_id}, version={self.version_number})>"


class VersionDiff(Base):
    """
    Model for storing diffs between document versions.
    
    Pre-computed diffs for faster comparison viewing.
    """
    __tablename__ = "version_diffs"
    
    id = Column(Integer, primary_key=True, index=True)
    from_version_id = Column(Integer, ForeignKey('document_versions.id', ondelete='CASCADE'), nullable=False)
    to_version_id = Column(Integer, ForeignKey('document_versions.id', ondelete='CASCADE'), nullable=False)
    
    # Diff data
    diff_summary = Column(Text, nullable=True)  # Human-readable summary
    diff_data = Column(JSON, nullable=True)  # Structured diff data
    chunks_added = Column(Integer, default=0)
    chunks_removed = Column(Integer, default=0)
    chunks_modified = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<VersionDiff(id={self.id}, from={self.from_version_id}, to={self.to_version_id})>"
