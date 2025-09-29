"""
Metrics and monitoring for Ultra Pinnacle AI Studio
"""
import time
import psutil
from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import logging

from .database import get_db, User, Conversation, Message, Task
from .auth import get_current_active_user, User as UserModel

logger = logging.getLogger("ultra_pinnacle")
router = APIRouter()

# Metrics storage
metrics_data = {
    "requests_total": 0,
    "requests_by_method": {},
    "requests_by_endpoint": {},
    "response_times": [],
    "errors_total": 0,
    "active_connections": 0,
    "start_time": time.time()
}

def record_request(duration: float, status_code: int, method: str = "GET", endpoint: str = "/"):
    """Record request metrics"""
    metrics_data["requests_total"] += 1

    # Record by method
    if method not in metrics_data["requests_by_method"]:
        metrics_data["requests_by_method"][method] = 0
    metrics_data["requests_by_method"][method] += 1

    # Record by endpoint
    if endpoint not in metrics_data["requests_by_endpoint"]:
        metrics_data["requests_by_endpoint"][endpoint] = 0
    metrics_data["requests_by_endpoint"][endpoint] += 1

    # Record response time
    metrics_data["response_times"].append(duration)
    if len(metrics_data["response_times"]) > 1000:  # Keep last 1000
        metrics_data["response_times"] = metrics_data["response_times"][-1000:]

    # Record errors
    if status_code >= 400:
        metrics_data["errors_total"] += 1

def get_system_metrics() -> Dict[str, Any]:
    """Get system metrics"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_mb": memory.used / 1024 / 1024,
            "memory_total_mb": memory.total / 1024 / 1024,
            "disk_percent": disk.percent,
            "disk_used_gb": disk.used / 1024 / 1024 / 1024,
            "disk_total_gb": disk.total / 1024 / 1024 / 1024,
            "uptime_seconds": time.time() - metrics_data["start_time"]
        }
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        return {
            "cpu_percent": 0,
            "memory_percent": 0,
            "memory_used_mb": 0,
            "memory_total_mb": 0,
            "disk_percent": 0,
            "disk_used_gb": 0,
            "disk_total_gb": 0,
            "uptime_seconds": time.time() - metrics_data["start_time"]
        }

def get_application_metrics(db: Session) -> Dict[str, Any]:
    """Get application metrics"""
    try:
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        total_conversations = db.query(Conversation).count()
        active_tasks = db.query(Task).filter(Task.status == "running").count()
        completed_tasks = db.query(Task).filter(Task.status == "completed").count()
        failed_tasks = db.query(Task).filter(Task.status == "failed").count()

        # Recent logins (last 24 hours)
        recent_logins = 0  # Would need audit log table

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_conversations": total_conversations,
            "active_tasks": active_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "recent_logins_24h": recent_logins
        }
    except Exception as e:
        logger.error(f"Error getting application metrics: {e}")
        return {
            "total_users": 0,
            "active_users": 0,
            "total_conversations": 0,
            "active_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "recent_logins_24h": 0
        }

def get_performance_metrics() -> Dict[str, Any]:
    """Get performance metrics"""
    response_times = metrics_data["response_times"]
    if response_times:
        avg_response_time = sum(response_times) / len(response_times)
        min_response_time = min(response_times)
        max_response_time = max(response_times)
    else:
        avg_response_time = min_response_time = max_response_time = 0

    total_requests = metrics_data["requests_total"]
    errors_total = metrics_data["errors_total"]

    error_rate = (errors_total / total_requests * 100) if total_requests > 0 else 0
    requests_per_minute = total_requests / max(1, (time.time() - metrics_data["start_time"]) / 60)

    return {
        "total_requests": total_requests,
        "avg_response_time": avg_response_time,
        "min_response_time": min_response_time,
        "max_response_time": max_response_time,
        "error_rate": error_rate,
        "requests_per_minute": requests_per_minute,
        "errors_total": errors_total
    }

@router.get("/dashboard")
async def get_dashboard_metrics(db: Session = Depends(get_db)):
    """Get dashboard metrics"""
    return {
        "system": get_system_metrics(),
        "performance": get_performance_metrics(),
        "application": get_application_metrics(db)
    }

@router.get("/dashboard/logs")
async def get_dashboard_logs(lines: int = 20):
    """Get recent application logs (placeholder)"""
    # This would need to read from log files
    # For now, return mock data
    return {
        "logs": [
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO - Application started",
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO - Database connected",
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO - Models loaded"
        ]
    }

@router.get("/")
async def get_metrics():
    """Prometheus metrics endpoint"""
    system = get_system_metrics()
    performance = get_performance_metrics()

    metrics_output = f"""# HELP ultra_pinnacle_cpu_usage_percent CPU usage percentage
# TYPE ultra_pinnacle_cpu_usage_percent gauge
ultra_pinnacle_cpu_usage_percent {system['cpu_percent']}

# HELP ultra_pinnacle_memory_usage_percent Memory usage percentage
# TYPE ultra_pinnacle_memory_usage_percent gauge
ultra_pinnacle_memory_usage_percent {system['memory_percent']}

# HELP ultra_pinnacle_requests_total Total number of requests
# TYPE ultra_pinnacle_requests_total counter
ultra_pinnacle_requests_total {performance['total_requests']}

# HELP ultra_pinnacle_request_duration_seconds Request duration in seconds
# TYPE ultra_pinnacle_request_duration_seconds histogram
ultra_pinnacle_request_duration_seconds_sum {performance['avg_response_time'] * performance['total_requests']}
ultra_pinnacle_request_duration_seconds_count {performance['total_requests']}
"""

    return metrics_output

logger.info("Metrics module initialized")