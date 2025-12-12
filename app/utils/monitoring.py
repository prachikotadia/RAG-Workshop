"""
Monitoring and observability utilities.
"""
import time
import logging
from typing import Dict, Any
from functools import wraps
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Prometheus-style metrics (in-memory, can be upgraded to Prometheus client)
_metrics = {
    "http_requests_total": {},
    "http_request_duration_seconds": {},
    "http_request_size_bytes": {},
    "http_response_size_bytes": {},
    "errors_total": {},
}


def record_metric(metric_name: str, labels: Dict[str, str] = None, value: float = 1.0):
    """
    Record a metric.
    
    Args:
        metric_name: Name of the metric
        labels: Optional labels (e.g., {"method": "GET", "endpoint": "/health"})
        value: Metric value
    """
    if labels is None:
        labels = {}
    
    label_key = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
    
    if metric_name not in _metrics:
        _metrics[metric_name] = {}
    
    if label_key not in _metrics[metric_name]:
        _metrics[metric_name][label_key] = 0.0
    
    _metrics[metric_name][label_key] += value


def get_metrics() -> Dict[str, Any]:
    """Get all metrics in Prometheus format."""
    lines = []
    for metric_name, label_values in _metrics.items():
        for label_key, value in label_values.items():
            labels = f"{{{label_key}}}" if label_key else ""
            lines.append(f"{metric_name}{labels} {value}")
    return "\n".join(lines)


def get_metrics_dict() -> Dict[str, Any]:
    """Get all metrics as a dictionary."""
    return _metrics.copy()


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware to track performance metrics."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        method = request.method
        path = request.url.path
        
        # Record request
        record_metric(
            "http_requests_total",
            labels={"method": method, "endpoint": path, "status": "unknown"}
        )
        
        # Get request size
        request_size = 0
        if hasattr(request, "body"):
            try:
                body = await request.body()
                request_size = len(body)
            except Exception:
                pass
        
        record_metric(
            "http_request_size_bytes",
            labels={"method": method, "endpoint": path},
            value=request_size
        )
        
        # Process request
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Record success metrics
            record_metric(
                "http_requests_total",
                labels={"method": method, "endpoint": path, "status": str(response.status_code)}
            )
            record_metric(
                "http_request_duration_seconds",
                labels={"method": method, "endpoint": path},
                value=duration
            )
            
            # Get response size
            if hasattr(response, "body"):
                try:
                    response_size = len(response.body) if hasattr(response.body, "__len__") else 0
                    record_metric(
                        "http_response_size_bytes",
                        labels={"method": method, "endpoint": path},
                        value=response_size
                    )
                except Exception:
                    pass
            
            # Add performance headers
            response.headers["X-Response-Time"] = f"{duration:.3f}"
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Record error metrics
            record_metric(
                "http_requests_total",
                labels={"method": method, "endpoint": path, "status": "500"}
            )
            record_metric(
                "errors_total",
                labels={"method": method, "endpoint": path, "error_type": type(e).__name__}
            )
            record_metric(
                "http_request_duration_seconds",
                labels={"method": method, "endpoint": path},
                value=duration
            )
            
            raise


def track_performance(func):
    """Decorator to track function performance."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        func_name = f"{func.__module__}.{func.__name__}"
        
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            
            record_metric(
                "function_duration_seconds",
                labels={"function": func_name},
                value=duration
            )
            
            return result
        except Exception as e:
            duration = time.time() - start_time
            
            record_metric(
                "function_errors_total",
                labels={"function": func_name, "error_type": type(e).__name__}
            )
            
            raise
    
    return wrapper

