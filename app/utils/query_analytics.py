"""
Query performance analytics for tracking and optimizing RAG pipeline.

Tracks query latency, token usage, cache hit rate, and enables A/B testing
of different RAG strategies.
"""
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.db import models

logger = logging.getLogger(__name__)

# In-memory storage for query metrics (can be moved to database for persistence)
_query_metrics: List[Dict[str, Any]] = []
_ab_test_results: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
    "variant_a": {"count": 0, "total_latency": 0.0, "total_tokens": 0, "cache_hits": 0},
    "variant_b": {"count": 0, "total_latency": 0.0, "total_tokens": 0, "cache_hits": 0},
})


@dataclass
class QueryMetric:
    """Single query performance metric."""
    user_id: int
    session_id: int
    query: str
    latency_ms: float
    token_count: int
    cache_hit: bool
    strategy: str  # e.g., "hybrid", "vector_only", "reranked"
    timestamp: datetime
    confidence_score: Optional[float] = None
    num_citations: int = 0


def record_query_metric(
    user_id: int,
    session_id: int,
    query: str,
    latency_ms: float,
    token_count: int,
    cache_hit: bool,
    strategy: str = "default",
    confidence_score: Optional[float] = None,
    num_citations: int = 0,
) -> None:
    """
    Record a query performance metric.
    
    Args:
        user_id: User ID
        session_id: Chat session ID
        query: User's query
        latency_ms: Query latency in milliseconds
        token_count: Number of tokens used
        cache_hit: Whether result was from cache
        strategy: RAG strategy used
        confidence_score: Confidence score of answer
        num_citations: Number of citations returned
    """
    metric = QueryMetric(
        user_id=user_id,
        session_id=session_id,
        query=query[:200],  # Truncate long queries
        latency_ms=latency_ms,
        token_count=token_count,
        cache_hit=cache_hit,
        strategy=strategy,
        timestamp=datetime.utcnow(),
        confidence_score=confidence_score,
        num_citations=num_citations,
    )
    
    _query_metrics.append(asdict(metric))
    
    # Keep only last 10000 metrics in memory
    if len(_query_metrics) > 10000:
        _query_metrics.pop(0)
    
    logger.debug(f"Recorded query metric: {latency_ms:.1f}ms, {token_count} tokens, cache={cache_hit}")


def record_ab_test_result(
    test_name: str,
    variant: str,  # "a" or "b"
    latency_ms: float,
    token_count: int,
    cache_hit: bool,
) -> None:
    """
    Record A/B test result.
    
    Args:
        test_name: Name of the A/B test
        variant: "a" or "b"
        latency_ms: Query latency
        token_count: Token usage
        cache_hit: Whether result was cached
    """
    variant_key = f"variant_{variant}"
    if variant_key not in _ab_test_results[test_name]:
        _ab_test_results[test_name][variant_key] = {
            "count": 0,
            "total_latency": 0.0,
            "total_tokens": 0,
            "cache_hits": 0,
        }
    
    result = _ab_test_results[test_name][variant_key]
    result["count"] += 1
    result["total_latency"] += latency_ms
    result["total_tokens"] += token_count
    if cache_hit:
        result["cache_hits"] += 1


def get_query_statistics(
    user_id: Optional[int] = None,
    hours: int = 24,
) -> Dict[str, Any]:
    """
    Get query performance statistics.
    
    Args:
        user_id: Optional user ID to filter by
        hours: Number of hours to look back
    
    Returns:
        Dictionary with statistics
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    # Filter metrics
    filtered_metrics = [
        m for m in _query_metrics
        if m["timestamp"] >= cutoff_time and (user_id is None or m["user_id"] == user_id)
    ]
    
    if not filtered_metrics:
        return {
            "total_queries": 0,
            "avg_latency_ms": 0.0,
            "p50_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
            "total_tokens": 0,
            "avg_tokens": 0.0,
            "cache_hit_rate": 0.0,
            "avg_confidence": 0.0,
            "avg_citations": 0.0,
        }
    
    latencies = [m["latency_ms"] for m in filtered_metrics]
    latencies.sort()
    
    total_tokens = sum(m["token_count"] for m in filtered_metrics)
    cache_hits = sum(1 for m in filtered_metrics if m["cache_hit"])
    confidence_scores = [m["confidence_score"] for m in filtered_metrics if m["confidence_score"] is not None]
    citations = [m["num_citations"] for m in filtered_metrics]
    
    n = len(filtered_metrics)
    
    return {
        "total_queries": n,
        "avg_latency_ms": sum(latencies) / n,
        "p50_latency_ms": latencies[n // 2] if n > 0 else 0.0,
        "p95_latency_ms": latencies[int(n * 0.95)] if n > 1 else latencies[-1] if n > 0 else 0.0,
        "p99_latency_ms": latencies[int(n * 0.99)] if n > 1 else latencies[-1] if n > 0 else 0.0,
        "min_latency_ms": min(latencies) if latencies else 0.0,
        "max_latency_ms": max(latencies) if latencies else 0.0,
        "total_tokens": total_tokens,
        "avg_tokens": total_tokens / n if n > 0 else 0.0,
        "cache_hit_rate": (cache_hits / n * 100) if n > 0 else 0.0,
        "cache_hits": cache_hits,
        "avg_confidence": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0,
        "avg_citations": sum(citations) / n if n > 0 else 0.0,
    }


def get_slow_queries(
    user_id: Optional[int] = None,
    hours: int = 24,
    threshold_ms: float = 3000.0,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Get slow queries above threshold.
    
    Args:
        user_id: Optional user ID to filter by
        hours: Number of hours to look back
        threshold_ms: Latency threshold in milliseconds
        limit: Maximum number of results
    
    Returns:
        List of slow query metrics
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    filtered_metrics = [
        m for m in _query_metrics
        if (m["timestamp"] >= cutoff_time and
            m["latency_ms"] >= threshold_ms and
            (user_id is None or m["user_id"] == user_id))
    ]
    
    # Sort by latency (descending)
    filtered_metrics.sort(key=lambda x: x["latency_ms"], reverse=True)
    
    return filtered_metrics[:limit]


def get_ab_test_results(test_name: str) -> Dict[str, Any]:
    """
    Get A/B test results.
    
    Args:
        test_name: Name of the A/B test
    
    Returns:
        Dictionary with A/B test statistics
    """
    if test_name not in _ab_test_results:
        return {
            "test_name": test_name,
            "variant_a": {"count": 0},
            "variant_b": {"count": 0},
        }
    
    results = _ab_test_results[test_name]
    variant_a = results.get("variant_a", {"count": 0, "total_latency": 0.0, "total_tokens": 0, "cache_hits": 0})
    variant_b = results.get("variant_b", {"count": 0, "total_latency": 0.0, "total_tokens": 0, "cache_hits": 0})
    
    def calc_stats(variant_data):
        count = variant_data["count"]
        if count == 0:
            return {
                "count": 0,
                "avg_latency_ms": 0.0,
                "avg_tokens": 0.0,
                "cache_hit_rate": 0.0,
            }
        return {
            "count": count,
            "avg_latency_ms": variant_data["total_latency"] / count,
            "avg_tokens": variant_data["total_tokens"] / count,
            "cache_hit_rate": (variant_data["cache_hits"] / count * 100) if count > 0 else 0.0,
        }
    
    return {
        "test_name": test_name,
        "variant_a": calc_stats(variant_a),
        "variant_b": calc_stats(variant_b),
        "winner": "a" if variant_a["count"] > 0 and variant_b["count"] > 0 and (
            (variant_a["total_latency"] / variant_a["count"]) < (variant_b["total_latency"] / variant_b["count"])
        ) else "b" if variant_b["count"] > 0 else None,
    }


def get_strategy_comparison(hours: int = 24) -> Dict[str, Any]:
    """
    Compare performance of different RAG strategies.
    
    Args:
        hours: Number of hours to look back
    
    Returns:
        Dictionary comparing strategies
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    filtered_metrics = [m for m in _query_metrics if m["timestamp"] >= cutoff_time]
    
    strategy_stats = defaultdict(lambda: {
        "count": 0,
        "total_latency": 0.0,
        "total_tokens": 0,
        "cache_hits": 0,
        "total_confidence": 0.0,
        "confidence_count": 0,
    })
    
    for metric in filtered_metrics:
        strategy = metric["strategy"]
        stats = strategy_stats[strategy]
        stats["count"] += 1
        stats["total_latency"] += metric["latency_ms"]
        stats["total_tokens"] += metric["token_count"]
        if metric["cache_hit"]:
            stats["cache_hits"] += 1
        if metric["confidence_score"] is not None:
            stats["total_confidence"] += metric["confidence_score"]
            stats["confidence_count"] += 1
    
    # Calculate averages
    comparison = {}
    for strategy, stats in strategy_stats.items():
        count = stats["count"]
        comparison[strategy] = {
            "count": count,
            "avg_latency_ms": stats["total_latency"] / count if count > 0 else 0.0,
            "avg_tokens": stats["total_tokens"] / count if count > 0 else 0.0,
            "cache_hit_rate": (stats["cache_hits"] / count * 100) if count > 0 else 0.0,
            "avg_confidence": (stats["total_confidence"] / stats["confidence_count"]) if stats["confidence_count"] > 0 else 0.0,
        }
    
    return comparison
