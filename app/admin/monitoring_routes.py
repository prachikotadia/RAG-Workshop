"""
Monitoring and metrics endpoints.
"""
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from app.utils.monitoring import get_metrics, get_metrics_dict
from app.utils.cache import get_cache_stats

router = APIRouter()


@router.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus text format.
    """
    metrics_text = get_metrics()
    return Response(
        content=metrics_text,
        media_type="text/plain; version=0.0.4"
    )


@router.get("/metrics/json")
async def metrics_json():
    """
    Metrics in JSON format (for easier consumption).
    """
    metrics = get_metrics_dict()
    # Add cache statistics
    cache_stats = get_cache_stats()
    metrics["cache"] = cache_stats
    return metrics

