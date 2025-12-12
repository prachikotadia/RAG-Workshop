"""
A/B Testing framework for RAG pipeline optimization.

Tests different configurations (RAG strategies, chunk sizes, prompts) and tracks metrics.
"""
import logging
import random
import time
from typing import Dict, Optional, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.ab_test_models import Experiment, ExperimentResult, ExperimentVariant, ExperimentStatus
from app.db import models

logger = logging.getLogger(__name__)


def get_active_experiment_for_user(db: Session, user_id: int, test_type: str) -> Optional[Experiment]:
    """Get the active experiment for a user and test type."""
    return db.query(Experiment).filter(
        Experiment.user_id == user_id,
        Experiment.test_type == test_type,
        Experiment.status == ExperimentStatus.RUNNING.value
    ).first()


def select_variant_for_query(db: Session, experiment: Experiment) -> Optional[Dict[str, Any]]:
    """
    Select a variant for a query based on traffic allocation.
    
    Returns the variant configuration to use, or None if no variant should be used.
    """
    variants = db.query(ExperimentVariant).filter(
        ExperimentVariant.experiment_id == experiment.id
    ).all()
    
    if not variants:
        return None
    
    # Simple random selection based on traffic_percentage
    # In production, you'd use more sophisticated allocation
    rand = random.random()
    cumulative = 0.0
    
    for variant in variants:
        cumulative += variant.traffic_percentage
        if rand <= cumulative:
            return {
                "variant_id": variant.id,
                "variant_name": variant.name,
                "config": variant.config,
            }
    
    # Fallback to first variant
    if variants:
        variant = variants[0]
        return {
            "variant_id": variant.id,
            "variant_name": variant.name,
            "config": variant.config,
        }
    
    return None


def record_experiment_result(
    db: Session,
    experiment_id: int,
    variant_name: str,
    query_text: str,
    response_text: Optional[str] = None,
    latency_ms: Optional[float] = None,
    token_count: Optional[int] = None,
    cost_usd: Optional[float] = None,
    relevance_score: Optional[float] = None,
    retrieved_chunks_count: Optional[int] = None,
    session_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> ExperimentResult:
    """Record a query result for an A/B test experiment."""
    result = ExperimentResult(
        experiment_id=experiment_id,
        variant_name=variant_name,
        query_text=query_text,
        response_text=response_text,
        latency_ms=latency_ms,
        token_count=token_count,
        cost_usd=cost_usd,
        relevance_score=relevance_score,
        retrieved_chunks_count=retrieved_chunks_count,
        session_id=session_id,
        metadata=metadata or {},
    )
    db.add(result)
    
    # Update experiment and variant statistics
    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if experiment:
        experiment.total_queries += 1
    
    variant = db.query(ExperimentVariant).filter(
        ExperimentVariant.experiment_id == experiment_id,
        ExperimentVariant.name == variant_name
    ).first()
    if variant:
        variant.total_queries += 1
        if latency_ms:
            # Update average latency (simplified - in production use proper aggregation)
            if variant.avg_latency_ms:
                variant.avg_latency_ms = (variant.avg_latency_ms + latency_ms) / 2
            else:
                variant.avg_latency_ms = latency_ms
        if relevance_score:
            if variant.avg_relevance_score:
                variant.avg_relevance_score = (variant.avg_relevance_score + relevance_score) / 2
            else:
                variant.avg_relevance_score = relevance_score
        if cost_usd:
            variant.total_cost_usd += cost_usd
    
    db.commit()
    db.refresh(result)
    return result


def get_experiment_statistics(db: Session, experiment_id: int) -> Dict[str, Any]:
    """Get aggregated statistics for an experiment."""
    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not experiment:
        return {}
    
    variants = db.query(ExperimentVariant).filter(
        ExperimentVariant.experiment_id == experiment_id
    ).all()
    
    # Aggregate results by variant
    variant_stats = []
    for variant in variants:
        results = db.query(ExperimentResult).filter(
            ExperimentResult.experiment_id == experiment_id,
            ExperimentResult.variant_name == variant.name
        ).all()
        
        if results:
            avg_latency = sum(r.latency_ms for r in results if r.latency_ms) / len([r for r in results if r.latency_ms])
            avg_relevance = sum(r.relevance_score for r in results if r.relevance_score) / len([r for r in results if r.relevance_score])
            total_cost = sum(r.cost_usd for r in results if r.cost_usd)
        else:
            avg_latency = variant.avg_latency_ms or 0
            avg_relevance = variant.avg_relevance_score or 0
            total_cost = variant.total_cost_usd or 0
        
        variant_stats.append({
            "variant_name": variant.name,
            "total_queries": variant.total_queries,
            "avg_latency_ms": avg_latency,
            "avg_relevance_score": avg_relevance,
            "total_cost_usd": total_cost,
            "config": variant.config,
        })
    
    return {
        "experiment_id": experiment.id,
        "name": experiment.name,
        "status": experiment.status,
        "total_queries": experiment.total_queries,
        "variants": variant_stats,
    }
