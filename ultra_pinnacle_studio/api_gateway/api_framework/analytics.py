"""
API Analytics and Monitoring for Ultra Pinnacle AI Studio

This module provides comprehensive analytics and monitoring capabilities for:
- API usage metrics and statistics
- Performance monitoring
- Error tracking and analysis
- User behavior analytics
- Real-time dashboards
"""

from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter
import asyncio
import logging
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("ultra_pinnacle")


@dataclass
class APIMetrics:
    """API metrics data structure"""

    endpoint: str
    method: str
    status_code: int
    response_time: float
    request_size: int = 0
    response_size: int = 0
    user_id: Optional[int] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EndpointStats:
    """Statistics for a specific endpoint"""

    endpoint: str
    method: str
    total_requests: int = 0
    total_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    avg_response_time: float = 0.0
    status_codes: Counter = field(default_factory=Counter)
    error_count: int = 0
    last_request_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_request(self, metrics: APIMetrics):
        """Add a request to the statistics"""
        self.total_requests += 1
        self.total_response_time += metrics.response_time
        self.avg_response_time = self.total_response_time / self.total_requests

        if metrics.response_time < self.min_response_time:
            self.min_response_time = metrics.response_time
        if metrics.response_time > self.max_response_time:
            self.max_response_time = metrics.response_time

        self.status_codes[metrics.status_code] += 1
        if metrics.status_code >= 400:
            self.error_count += 1

        self.last_request_at = metrics.timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "endpoint": self.endpoint,
            "method": self.method,
            "total_requests": self.total_requests,
            "total_response_time": self.total_response_time,
            "min_response_time": self.min_response_time if self.min_response_time != float('inf') else 0,
            "max_response_time": self.max_response_time,
            "avg_response_time": self.avg_response_time,
            "status_codes": dict(self.status_codes),
            "error_count": self.error_count,
            "error_rate": self.error_count / max(1, self.total_requests),
            "last_request_at": self.last_request_at.isoformat() if self.last_request_at else None,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class UserActivity:
    """User activity tracking"""

    user_id: int
    endpoint: str
    method: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorAnalytics:
    """Error analytics data"""

    endpoint: str
    method: str
    status_code: int
    error_type: str
    error_message: str
    user_id: Optional[int] = None
    client_ip: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    stack_trace: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AnalyticsCollector:
    """Collects and aggregates API analytics data"""

    def __init__(self, retention_days: int = 30):
        self.retention_days = retention_days
        self.endpoint_stats: Dict[str, EndpointStats] = {}
        self.user_activities: List[UserActivity] = []
        self.error_analytics: List[ErrorAnalytics] = []
        self.metrics_buffer: List[APIMetrics] = []
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=2)

        # Start background cleanup task (only if event loop is running)
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(self._cleanup_old_data())
        except RuntimeError:
            # No event loop running, cleanup will be handled externally
            pass

    def record_request(self, metrics: APIMetrics):
        """Record API request metrics"""
        with self._lock:
            self.metrics_buffer.append(metrics)

            # Update endpoint statistics
            key = f"{metrics.method}:{metrics.endpoint}"
            if key not in self.endpoint_stats:
                self.endpoint_stats[key] = EndpointStats(
                    endpoint=metrics.endpoint,
                    method=metrics.method
                )
            self.endpoint_stats[key].add_request(metrics)

            # Record user activity if user_id is provided
            if metrics.user_id:
                activity = UserActivity(
                    user_id=metrics.user_id,
                    endpoint=metrics.endpoint,
                    method=metrics.method,
                    timestamp=metrics.timestamp,
                    metadata=metrics.metadata
                )
                self.user_activities.append(activity)

    def record_error(self, error: ErrorAnalytics):
        """Record error analytics"""
        with self._lock:
            self.error_analytics.append(error)

    def get_endpoint_stats(self, endpoint: Optional[str] = None, method: Optional[str] = None) -> Dict[str, Any]:
        """Get endpoint statistics"""
        with self._lock:
            if endpoint and method:
                key = f"{method}:{endpoint}"
                stats = self.endpoint_stats.get(key)
                return stats.to_dict() if stats else {}
            elif endpoint:
                # Return stats for all methods of this endpoint
                result = {}
                for key, stats in self.endpoint_stats.items():
                    if stats.endpoint == endpoint:
                        result[key] = stats.to_dict()
                return result
            else:
                # Return all endpoint stats
                return {key: stats.to_dict() for key, stats in self.endpoint_stats.items()}

    def get_user_activity(self, user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Get user activity history"""
        with self._lock:
            activities = [a for a in self.user_activities if a.user_id == user_id]
            activities.sort(key=lambda x: x.timestamp, reverse=True)
            return [
                {
                    "endpoint": a.endpoint,
                    "method": a.method,
                    "timestamp": a.timestamp.isoformat(),
                    "session_id": a.session_id,
                    "metadata": a.metadata
                }
                for a in activities[:limit]
            ]

    def get_error_analytics(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get error analytics for the specified time period"""
        with self._lock:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            errors = [e for e in self.error_analytics if e.timestamp >= cutoff_time]

            return [
                {
                    "endpoint": e.endpoint,
                    "method": e.method,
                    "status_code": e.status_code,
                    "error_type": e.error_type,
                    "error_message": e.error_message,
                    "user_id": e.user_id,
                    "client_ip": e.client_ip,
                    "timestamp": e.timestamp.isoformat(),
                    "stack_trace": e.stack_trace,
                    "metadata": e.metadata
                }
                for e in errors
            ]

    def get_global_stats(self) -> Dict[str, Any]:
        """Get global API statistics"""
        with self._lock:
            total_requests = sum(stats.total_requests for stats in self.endpoint_stats.values())
            total_errors = sum(stats.error_count for stats in self.endpoint_stats.values())
            total_response_time = sum(stats.total_response_time for stats in self.endpoint_stats.values())

            # Calculate average response time across all endpoints
            avg_response_time = total_response_time / max(1, total_requests)

            # Status code distribution
            status_distribution = Counter()
            for stats in self.endpoint_stats.values():
                status_distribution.update(stats.status_codes)

            return {
                "total_requests": total_requests,
                "total_errors": total_errors,
                "error_rate": total_errors / max(1, total_requests),
                "avg_response_time": avg_response_time,
                "status_distribution": dict(status_distribution),
                "active_endpoints": len(self.endpoint_stats),
                "total_users": len(set(a.user_id for a in self.user_activities)),
                "data_points": len(self.metrics_buffer)
            }

    def get_performance_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance trends over time"""
        with self._lock:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            # Group metrics by hour
            hourly_stats = defaultdict(lambda: {
                "requests": 0,
                "errors": 0,
                "total_response_time": 0.0,
                "avg_response_time": 0.0
            })

            for metrics in self.metrics_buffer:
                if metrics.timestamp >= cutoff_time:
                    hour_key = metrics.timestamp.replace(minute=0, second=0, microsecond=0)
                    stats = hourly_stats[hour_key.isoformat()]
                    stats["requests"] += 1
                    stats["total_response_time"] += metrics.response_time
                    if metrics.status_code >= 400:
                        stats["errors"] += 1

            # Calculate averages
            for stats in hourly_stats.values():
                if stats["requests"] > 0:
                    stats["avg_response_time"] = stats["total_response_time"] / stats["requests"]

            return dict(hourly_stats)

    async def _cleanup_old_data(self):
        """Background task to clean up old data"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.retention_days)

                with self._lock:
                    # Clean up old metrics
                    self.metrics_buffer = [
                        m for m in self.metrics_buffer
                        if m.timestamp >= cutoff_time
                    ]

                    # Clean up old user activities
                    self.user_activities = [
                        a for a in self.user_activities
                        if a.timestamp >= cutoff_time
                    ]

                    # Clean up old error analytics
                    self.error_analytics = [
                        e for e in self.error_analytics
                        if e.timestamp >= cutoff_time
                    ]

                logger.info(f"Cleaned up analytics data older than {cutoff_time}")

            except Exception as e:
                logger.error(f"Error during analytics cleanup: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    def export_data(self) -> Dict[str, Any]:
        """Export all analytics data"""
        with self._lock:
            return {
                "endpoint_stats": {k: v.to_dict() for k, v in self.endpoint_stats.items()},
                "user_activities": [
                    {
                        "user_id": a.user_id,
                        "endpoint": a.endpoint,
                        "method": a.method,
                        "timestamp": a.timestamp.isoformat(),
                        "session_id": a.session_id,
                        "metadata": a.metadata
                    }
                    for a in self.user_activities
                ],
                "error_analytics": [
                    {
                        "endpoint": e.endpoint,
                        "method": e.method,
                        "status_code": e.status_code,
                        "error_type": e.error_type,
                        "error_message": e.error_message,
                        "user_id": e.user_id,
                        "client_ip": e.client_ip,
                        "timestamp": e.timestamp.isoformat(),
                        "stack_trace": e.stack_trace,
                        "metadata": e.metadata
                    }
                    for e in self.error_analytics
                ],
                "global_stats": self.get_global_stats(),
                "exported_at": datetime.now(timezone.utc).isoformat()
            }


# Global analytics collector instance
analytics_collector = AnalyticsCollector()


# Middleware for automatic metrics collection
class AnalyticsMiddleware:
    """Middleware to automatically collect API analytics"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        start_time = time.time()
        request = None

        # Capture request details
        try:
            from starlette.requests import Request
            request = Request(scope, receive)
            await request.body()  # Read request body to get size
        except Exception:
            pass

        # Process the request
        response_status = 200
        response_size = 0

        async def send_wrapper(message):
            nonlocal response_status, response_size
            if message["type"] == "http.response.start":
                response_status = message["status"]
            elif message["type"] == "http.response.body":
                response_size += len(message.get("body", b""))
            await send(message)

        await self.app(scope, receive, send_wrapper)

        # Record metrics
        try:
            response_time = time.time() - start_time

            # Extract user info from scope if available
            user_id = None
            client_ip = None
            user_agent = None

            for header_name, header_value in scope.get("headers", []):
                if header_name == b"x-user-id":
                    user_id = int(header_value.decode())
                elif header_name == b"x-forwarded-for":
                    client_ip = header_value.decode().split(",")[0].strip()
                elif header_name == b"user-agent":
                    user_agent = header_value.decode()

            if not client_ip and scope.get("client"):
                client_ip = scope["client"][0]

            path = scope.get("path", "")
            method = scope.get("method", "")

            metrics = APIMetrics(
                endpoint=path,
                method=method,
                status_code=response_status,
                response_time=response_time,
                response_size=response_size,
                user_id=user_id,
                client_ip=client_ip,
                user_agent=user_agent,
                metadata={
                    "query_params": dict(scope.get("query_string", {})),
                    "headers_count": len(scope.get("headers", []))
                }
            )

            # Record metrics asynchronously
            asyncio.create_task(self._record_metrics_async(metrics))

        except Exception as e:
            logger.error(f"Error recording analytics: {e}")

    async def _record_metrics_async(self, metrics: APIMetrics):
        """Record metrics asynchronously"""
        try:
            analytics_collector.record_request(metrics)
        except Exception as e:
            logger.error(f"Error in async metrics recording: {e}")


# Convenience functions
def record_api_request(
    endpoint: str,
    method: str,
    status_code: int,
    response_time: float,
    user_id: Optional[int] = None,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    **metadata
) -> None:
    """Record an API request"""
    metrics = APIMetrics(
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        response_time=response_time,
        user_id=user_id,
        client_ip=client_ip,
        user_agent=user_agent,
        metadata=metadata
    )
    analytics_collector.record_request(metrics)


def record_api_error(
    endpoint: str,
    method: str,
    status_code: int,
    error_type: str,
    error_message: str,
    user_id: Optional[int] = None,
    client_ip: Optional[str] = None,
    stack_trace: Optional[str] = None,
    **metadata
) -> None:
    """Record an API error"""
    error = ErrorAnalytics(
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        error_type=error_type,
        error_message=error_message,
        user_id=user_id,
        client_ip=client_ip,
        stack_trace=stack_trace,
        metadata=metadata
    )
    analytics_collector.record_error(error)


def get_analytics_dashboard_data() -> Dict[str, Any]:
    """Get data for analytics dashboard"""
    return {
        "global_stats": analytics_collector.get_global_stats(),
        "performance_trends": analytics_collector.get_performance_trends(),
        "top_endpoints": sorted(
            analytics_collector.get_endpoint_stats().values(),
            key=lambda x: x["total_requests"],
            reverse=True
        )[:10],
        "error_summary": analytics_collector.get_error_analytics(hours=24),
        "generated_at": datetime.now(timezone.utc).isoformat()
    }