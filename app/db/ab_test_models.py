"""
Database models for A/B testing framework.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base import Base


class ExperimentStatus(str, enum.Enum):
    """Status of an A/B test experiment."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Experiment(Base):
    """
    Model for A/B test experiments.
    
    Each experiment tests different configurations (RAG strategies, chunk sizes, prompts, etc.)
    """
    __tablename__ = "experiments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default=ExperimentStatus.DRAFT.value)
    
    # Experiment configuration
    test_type = Column(String(50), nullable=False)  # 'rag_strategy', 'chunk_size', 'prompt', etc.
    variants = Column(JSON, nullable=False)  # List of variant configurations
    
    # Metrics tracking
    total_queries = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    
    # Relationships
    results = relationship("ExperimentResult", back_populates="experiment", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Experiment(id={self.id}, name='{self.name}', status='{self.status}')>"


class ExperimentResult(Base):
    """
    Model for individual query results in an A/B test.
    
    Tracks performance metrics for each variant tested.
    """
    __tablename__ = "experiment_results"
    
    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey('experiments.id', ondelete='CASCADE'), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey('chat_sessions.id', ondelete='SET NULL'), nullable=True)
    variant_name = Column(String(100), nullable=False)  # Which variant was used
    
    # Query details
    query_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=True)
    
    # Performance metrics
    latency_ms = Column(Float, nullable=True)  # Response time in milliseconds
    token_count = Column(Integer, nullable=True)  # Total tokens used
    cost_usd = Column(Float, nullable=True)  # Estimated cost in USD
    
    # Quality metrics
    relevance_score = Column(Float, nullable=True)  # User feedback or automated score
    retrieved_chunks_count = Column(Integer, nullable=True)
    
    # Metadata (using result_metadata as column name to avoid SQLAlchemy reserved word)
    result_metadata = Column("metadata", JSON, default={})  # Additional metrics or context
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    experiment = relationship("Experiment", back_populates="results")
    
    def __repr__(self):
        return f"<ExperimentResult(id={self.id}, experiment_id={self.experiment_id}, variant='{self.variant_name}')>"


class ExperimentVariant(Base):
    """
    Model for experiment variant configurations.
    
    Stores the actual configuration for each variant being tested.
    """
    __tablename__ = "experiment_variants"
    
    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey('experiments.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(100), nullable=False)  # e.g., "control", "variant_a", "variant_b"
    description = Column(Text, nullable=True)
    
    # Configuration stored as JSON
    config = Column(JSON, nullable=False)  # e.g., {"chunk_size": 500, "strategy": "hybrid"}
    
    # Traffic allocation (0.0 to 1.0)
    traffic_percentage = Column(Float, default=0.5)  # 50% by default for A/B test
    
    # Results summary (aggregated)
    total_queries = Column(Integer, default=0)
    avg_latency_ms = Column(Float, nullable=True)
    avg_relevance_score = Column(Float, nullable=True)
    total_cost_usd = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ExperimentVariant(id={self.id}, name='{self.name}', experiment_id={self.experiment_id})>"
