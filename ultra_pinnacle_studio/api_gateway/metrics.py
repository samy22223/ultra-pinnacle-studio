"""
Prometheus metrics and monitoring for Ultra Pinnacle AI Studio
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import time
import psutil
from typing import Callable
from functools import wraps

# Request metrics
REQUEST_COUNT = Counter(
    'ultra_pinnacle_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'ultra_pinnacle_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

# AI Model metrics
MODEL_INFERENCE_COUNT = Counter(
    'ultra_pinnacle_model_inferences_total',
    'Total number of model inferences',
    ['model_name', 'task_type']
)

MODEL_INFERENCE_LATENCY = Histogram(
    'ultra_pinnacle_model_inference_duration_seconds',
    'Model inference duration in seconds',
    ['model_name', 'task_type']
)

# System metrics
ACTIVE_CONNECTIONS = Gauge(
    'ultra_pinnacle_active_connections',
    'Number of active connections'
)

MEMORY_USAGE = Gauge(
    'ultra_pinnacle_memory_usage_bytes',
    'Memory usage in bytes'
)

CPU_USAGE = Gauge(
    'ultra_pinnacle_cpu_usage_percent',
    'CPU usage percentage'
)

# Background task metrics
TASK_COUNT = Counter(
    'ultra_pinnacle_tasks_total',
    'Total number of background tasks',
    ['task_type', 'status']
)

TASK_QUEUE_SIZE = Gauge(
    'ultra_pinnacle_task_queue_size',
    'Number of tasks in queue'
)

# File upload metrics
UPLOAD_COUNT = Counter(
    'ultra_pinnacle_uploads_total',
    'Total number of file uploads',
    ['file_type']
)

UPLOAD_SIZE = Histogram(
    'ultra_pinnacle_upload_size_bytes',
    'Upload file size in bytes',
    ['file_type']
)

# Authentication metrics
AUTH_ATTEMPTS = Counter(
    'ultra_pinnacle_auth_attempts_total',
    'Total authentication attempts',
    ['result']
)

ACTIVE_SESSIONS = Gauge(
    'ultra_pinnacle_active_sessions',
    'Number of active user sessions'
)

def update_system_metrics():
    """Update system resource metrics"""
    MEMORY_USAGE.set(psutil.virtual_memory().used)
    CPU_USAGE.set(psutil.cpu_percent(interval=1))

def metrics_middleware(request, call_next):
    """FastAPI middleware for request metrics"""
    start_time = time.time()

    # Update system metrics periodically
    update_system_metrics()

    response = call_next(request)

    # Record request metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code
    ).inc()

    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(time.time() - start_time)

    return response

def track_model_inference(model_name: str, task_type: str):
    """Decorator to track model inference metrics"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)

            MODEL_INFERENCE_COUNT.labels(
                model_name=model_name,
                task_type=task_type
            ).inc()

            MODEL_INFERENCE_LATENCY.labels(
                model_name=model_name,
                task_type=task_type
            ).observe(time.time() - start_time)

            return result
        return wrapper
    return decorator

def track_task(task_type: str):
    """Decorator to track background task metrics"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            TASK_COUNT.labels(task_type=task_type, status='started').inc()
            try:
                result = await func(*args, **kwargs)
                TASK_COUNT.labels(task_type=task_type, status='completed').inc()
                return result
            except Exception as e:
                TASK_COUNT.labels(task_type=task_type, status='failed').inc()
                raise e
        return wrapper
    return decorator

def get_metrics():
    """Get Prometheus metrics"""
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

# Health check with detailed metrics
def get_health_status():
    """Get comprehensive health status"""
    try:
        # System health
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent()

        # Application health (would be expanded with actual checks)
        app_health = {
            "status": "healthy",
            "timestamp": time.time(),
            "system": {
                "memory_usage_percent": memory.percent,
                "cpu_usage_percent": cpu,
                "disk_usage_percent": psutil.disk_usage('/').percent
            },
            "application": {
                "active_connections": ACTIVE_CONNECTIONS._value if hasattr(ACTIVE_CONNECTIONS, '_value') else 0,
                "task_queue_size": TASK_QUEUE_SIZE._value if hasattr(TASK_QUEUE_SIZE, '_value') else 0
            }
        }

        # Determine overall health
        if memory.percent > 90 or cpu > 95:
            app_health["status"] = "warning"
        if memory.percent > 95 or cpu > 99:
            app_health["status"] = "critical"

        return app_health

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }