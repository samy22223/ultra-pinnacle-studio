"""
Metrics Dashboard for Ultra Pinnacle AI Studio
Provides monitoring and visualization of system metrics
"""
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import deque
import json
from pathlib import Path

class MetricsCollector:
    """Collect system and application metrics"""

    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.cpu_history = deque(maxlen=max_history)
        self.memory_history = deque(maxlen=max_history)
        self.request_history = deque(maxlen=max_history)
        self.error_history = deque(maxlen=max_history)
        self.start_time = time.time()

    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system-level metrics"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_mb": psutil.virtual_memory().used / 1024 / 1024,
            "memory_total_mb": psutil.virtual_memory().total / 1024 / 1024,
            "disk_usage_percent": psutil.disk_usage('/').percent,
            "disk_free_gb": psutil.disk_usage('/').free / 1024 / 1024 / 1024,
            "network_connections": len(psutil.net_connections()),
            "uptime_seconds": time.time() - self.start_time
        }

    def record_request(self, duration: float, status_code: int):
        """Record an API request"""
        timestamp = datetime.now().isoformat()
        self.request_history.append({
            "timestamp": timestamp,
            "duration": duration,
            "status_code": status_code
        })

        # Keep only last hour of requests
        cutoff_time = datetime.now() - timedelta(hours=1)
        while self.request_history and datetime.fromisoformat(self.request_history[0]["timestamp"]) < cutoff_time:
            self.request_history.popleft()

    def record_error(self, error_type: str, message: str):
        """Record an error"""
        timestamp = datetime.now().isoformat()
        self.error_history.append({
            "timestamp": timestamp,
            "type": error_type,
            "message": message
        })

        # Keep only last 24 hours of errors
        cutoff_time = datetime.now() - timedelta(hours=24)
        while self.error_history and datetime.fromisoformat(self.error_history[0]["timestamp"]) < cutoff_time:
            self.error_history.popleft()

    def get_request_stats(self) -> Dict[str, Any]:
        """Get request statistics"""
        if not self.request_history:
            return {
                "total_requests": 0,
                "avg_response_time": 0,
                "success_rate": 0,
                "requests_per_minute": 0
            }

        total_requests = len(self.request_history)
        successful_requests = sum(1 for r in self.request_history if r["status_code"] < 400)
        total_duration = sum(r["duration"] for r in self.request_history)

        # Calculate requests per minute (based on time span)
        if len(self.request_history) >= 2:
            time_span = (
                datetime.fromisoformat(self.request_history[-1]["timestamp"]) -
                datetime.fromisoformat(self.request_history[0]["timestamp"])
            ).total_seconds() / 60  # minutes
            requests_per_minute = total_requests / max(time_span, 1)
        else:
            requests_per_minute = 0

        return {
            "total_requests": total_requests,
            "avg_response_time": total_duration / total_requests if total_requests > 0 else 0,
            "success_rate": successful_requests / total_requests if total_requests > 0 else 0,
            "requests_per_minute": requests_per_minute
        }

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        error_counts = {}
        for error in self.error_history:
            error_type = error["type"]
            error_counts[error_type] = error_counts.get(error_type, 0) + 1

        return {
            "total_errors": len(self.error_history),
            "error_types": error_counts,
            "recent_errors": list(self.error_history)[-10:]  # Last 10 errors
        }

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system_metrics": self.collect_system_metrics(),
            "request_stats": self.get_request_stats(),
            "error_stats": self.get_error_stats(),
            "uptime_hours": (time.time() - self.start_time) / 3600
        }

# Global metrics collector instance
metrics_collector = MetricsCollector()

def get_metrics_collector():
    """Get the global metrics collector"""
    return metrics_collector