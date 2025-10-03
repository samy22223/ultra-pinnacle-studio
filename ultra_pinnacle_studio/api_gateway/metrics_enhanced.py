"""
Enhanced metrics and monitoring for Ultra Pinnacle AI Studio
"""
import time
import psutil
import threading
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
import logging
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json

from .database import get_db, User, Conversation, Message, Task
from .auth import get_current_active_user, User as UserModel

logger = logging.getLogger("ultra_pinnacle")
router = APIRouter()

class MetricsCollector:
    """Advanced metrics collector with time-series data"""
    
    def __init__(self):
        self.start_time = time.time()
        self.metrics_history = defaultdict(lambda: deque(maxlen=1000))  # Keep last 1000 entries
        self.current_metrics = {
            "requests_total": 0,
            "requests_by_method": defaultdict(int),
            "requests_by_endpoint": defaultdict(int),
            "response_times": deque(maxlen=10000),  # Keep more response times
            "errors_total": 0,
            "errors_by_type": defaultdict(int),
            "active_connections": 0,
            "system_load_history": deque(maxlen=100),
            "memory_usage_history": deque(maxlen=100),
            "disk_usage_history": deque(maxlen=100),
            "network_io": {"bytes_sent": 0, "bytes_recv": 0, "last_update": time.time()}
        }
        self.lock = threading.Lock()
        self.monitoring_thread = None
        self.is_monitoring = False
    
    def start_monitoring(self):
        """Start background monitoring"""
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitor_system, daemon=True)
        self.monitoring_thread.start()
        logger.info("Enhanced metrics monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
    
    def _monitor_system(self):
        """Monitor system metrics in background"""
        while self.is_monitoring:
            try:
                timestamp = datetime.now().isoformat()
                
                # CPU and memory
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                
                with self.lock:
                    self.current_metrics["system_load_history"].append({
                        "timestamp": timestamp,
                        "cpu_percent": cpu_percent,
                        "memory_percent": memory.percent,
                        "memory_used_mb": memory.used / 1024 / 1024
                    })
                
                # Disk usage (less frequent)
                if len(self.current_metrics["disk_usage_history"]) == 0 or \
                   time.time() - self.current_metrics["disk_usage_history"][-1]["timestamp_epoch"] > 300:  # Every 5 minutes
                    
                    disk = psutil.disk_usage('/')
                    with self.lock:
                        self.current_metrics["disk_usage_history"].append({
                            "timestamp": timestamp,
                            "timestamp_epoch": time.time(),
                            "disk_percent": disk.percent,
                            "disk_used_gb": disk.used / (1024**3),
                            "disk_free_gb": disk.free / (1024**3)
                        })
                
                # Network I/O
                net_io = psutil.net_io_counters()
                current_time = time.time()
                time_diff = current_time - self.current_metrics["network_io"]["last_update"]
                
                if time_diff > 0:
                    bytes_sent_per_sec = (net_io.bytes_sent - self.current_metrics["network_io"]["bytes_sent"]) / time_diff
                    bytes_recv_per_sec = (net_io.bytes_recv - self.current_metrics["network_io"]["bytes_recv"]) / time_diff
                    
                    with self.lock:
                        self.metrics_history["network_bytes_sent_per_sec"].append({
                            "timestamp": timestamp,
                            "value": bytes_sent_per_sec
                        })
                        self.metrics_history["network_bytes_recv_per_sec"].append({
                            "timestamp": timestamp,
                            "value": bytes_recv_per_sec
                        })
                        
                        self.current_metrics["network_io"].update({
                            "bytes_sent": net_io.bytes_sent,
                            "bytes_recv": net_io.bytes_recv,
                            "last_update": current_time
                        })
                
            except Exception as e:
                logger.error(f"Error in system monitoring: {e}")
            
            time.sleep(60)  # Update every minute
    
    def record_request(self, duration: float, status_code: int, method: str = "GET", endpoint: str = "/", client_ip: str = "unknown"):
        """Record request metrics with enhanced data"""
        timestamp = datetime.now().isoformat()
        
        with self.lock:
            self.current_metrics["requests_total"] += 1
            self.current_metrics["requests_by_method"][method] += 1
            self.current_metrics["requests_by_endpoint"][endpoint] += 1
            self.current_metrics["response_times"].append(duration)
            
            # Record in history
            self.metrics_history["requests"].append({
                "timestamp": timestamp,
                "duration": duration,
                "status_code": status_code,
                "method": method,
                "endpoint": endpoint,
                "client_ip": client_ip
            })
            
            # Record errors
            if status_code >= 400:
                self.current_metrics["errors_total"] += 1
                error_type = "client_error" if status_code < 500 else "server_error"
                self.current_metrics["errors_by_type"][error_type] += 1
                
                self.metrics_history["errors"].append({
                    "timestamp": timestamp,
                    "status_code": status_code,
                    "type": error_type,
                    "method": method,
                    "endpoint": endpoint
                })
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            
            # Get network info
            net_io = psutil.net_io_counters()
            
            # Process info
            process = psutil.Process()
            process_memory = process.memory_info()
            process_cpu = process.cpu_percent()
            
            with self.lock:
                return {
                    "cpu_percent": cpu_percent,
                    "cpu_load_avg": load_avg,
                    "memory_percent": memory.percent,
                    "memory_used_mb": memory.used / 1024 / 1024,
                    "memory_total_mb": memory.total / 1024 / 1024,
                    "memory_available_mb": memory.available / 1024 / 1024,
                    "disk_percent": disk.percent,
                    "disk_used_gb": disk.used / (1024**3),
                    "disk_total_gb": disk.total / (1024**3),
                    "disk_free_gb": disk.free / (1024**3),
                    "network_bytes_sent": net_io.bytes_sent,
                    "network_bytes_recv": net_io.bytes_recv,
                    "process_memory_mb": process_memory.rss / 1024 / 1024,
                    "process_cpu_percent": process_cpu,
                    "uptime_seconds": time.time() - self.start_time,
                    "system_load_history": list(self.current_metrics["system_load_history"])[-10:],  # Last 10 readings
                    "disk_usage_history": list(self.current_metrics["disk_usage_history"])[-5:]  # Last 5 readings
                }
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {"error": str(e)}
    
    def get_application_metrics(self, db: Session) -> Dict[str, Any]:
        """Get comprehensive application metrics"""
        try:
            # User metrics
            total_users = db.query(User).count()
            active_users = db.query(User).filter(User.is_active == True).count()
            superusers = db.query(User).filter(User.is_superuser == True).count()
            
            # Conversation metrics
            total_conversations = db.query(Conversation).count()
            recent_conversations = db.query(Conversation).filter(
                Conversation.updated_at >= datetime.now() - timedelta(days=1)
            ).count()
            
            # Message metrics
            total_messages = db.query(Message).count()
            recent_messages = db.query(Message).filter(
                Message.created_at >= datetime.now() - timedelta(days=1)
            ).count()
            
            # Task metrics
            total_tasks = db.query(Task).count() if hasattr(Task, 'status') else 0
            active_tasks = db.query(Task).filter(Task.status == "running").count() if hasattr(Task, 'status') else 0
            completed_tasks = db.query(Task).filter(Task.status == "completed").count() if hasattr(Task, 'status') else 0
            failed_tasks = db.query(Task).filter(Task.status == "failed").count() if hasattr(Task, 'status') else 0
            
            # AI model usage (placeholder - would need actual tracking)
            ai_requests = 0
            ai_tokens_used = 0
            
            with self.lock:
                return {
                    "users": {
                        "total": total_users,
                        "active": active_users,
                        "superusers": superusers
                    },
                    "conversations": {
                        "total": total_conversations,
                        "recent_24h": recent_conversations
                    },
                    "messages": {
                        "total": total_messages,
                        "recent_24h": recent_messages
                    },
                    "tasks": {
                        "total": total_tasks,
                        "active": active_tasks,
                        "completed": completed_tasks,
                        "failed": failed_tasks
                    },
                    "ai_usage": {
                        "requests_total": ai_requests,
                        "tokens_used": ai_tokens_used
                    }
                }
        except Exception as e:
            logger.error(f"Error getting application metrics: {e}")
            return {"error": str(e)}
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        with self.lock:
            response_times = list(self.current_metrics["response_times"])
            
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                median_response_time = sorted(response_times)[len(response_times) // 2]
                p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]
                p99_response_time = sorted(response_times)[int(len(response_times) * 0.99)]
                min_response_time = min(response_times)
                max_response_time = max(response_times)
            else:
                avg_response_time = median_response_time = p95_response_time = p99_response_time = min_response_time = max_response_time = 0
            
            total_requests = self.current_metrics["requests_total"]
            errors_total = self.current_metrics["errors_total"]
            
            # Calculate rates
            uptime_seconds = time.time() - self.start_time
            requests_per_second = total_requests / max(1, uptime_seconds)
            requests_per_minute = requests_per_second * 60
            error_rate = (errors_total / total_requests * 100) if total_requests > 0 else 0
            
            # Endpoint performance
            endpoint_performance = {}
            for endpoint, count in self.current_metrics["requests_by_endpoint"].items():
                endpoint_times = [r["duration"] for r in self.metrics_history["requests"] 
                                if r["endpoint"] == endpoint][-100:]  # Last 100 requests
                if endpoint_times:
                    endpoint_performance[endpoint] = {
                        "requests": count,
                        "avg_response_time": sum(endpoint_times) / len(endpoint_times),
                        "error_rate": len([r for r in self.metrics_history["errors"] 
                                         if r["endpoint"] == endpoint]) / max(1, count) * 100
                    }
            
            return {
                "requests": {
                    "total": total_requests,
                    "per_second": requests_per_second,
                    "per_minute": requests_per_minute,
                    "by_method": dict(self.current_metrics["requests_by_method"]),
                    "by_endpoint": dict(self.current_metrics["requests_by_endpoint"])
                },
                "response_times": {
                    "avg": avg_response_time,
                    "median": median_response_time,
                    "p95": p95_response_time,
                    "p99": p99_response_time,
                    "min": min_response_time,
                    "max": max_response_time,
                    "count": len(response_times)
                },
                "errors": {
                    "total": errors_total,
                    "rate_percent": error_rate,
                    "by_type": dict(self.current_metrics["errors_by_type"])
                },
                "endpoint_performance": endpoint_performance,
                "uptime_seconds": uptime_seconds
            }
    
    def get_health_score(self) -> Dict[str, Any]:
        """Calculate overall system health score"""
        try:
            system_metrics = self.get_system_metrics()
            performance_metrics = self.get_performance_metrics()
            
            # Health scoring (0-100)
            scores = {
                "cpu_health": max(0, 100 - system_metrics.get("cpu_percent", 0)),
                "memory_health": max(0, 100 - system_metrics.get("memory_percent", 0)),
                "disk_health": max(0, 100 - system_metrics.get("disk_percent", 0)),
                "error_rate_health": max(0, 100 - performance_metrics["errors"]["rate_percent"]),
                "response_time_health": max(0, 100 - min(100, performance_metrics["response_times"]["avg"] * 1000))  # Penalize slow responses
            }
            
            overall_score = sum(scores.values()) / len(scores)
            
            # Determine status
            if overall_score >= 90:
                status = "excellent"
            elif overall_score >= 75:
                status = "good"
            elif overall_score >= 60:
                status = "warning"
            elif overall_score >= 40:
                status = "critical"
            else:
                status = "failing"
            
            return {
                "overall_score": round(overall_score, 2),
                "status": status,
                "component_scores": {k: round(v, 2) for k, v in scores.items()},
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating health score: {e}")
            return {
                "overall_score": 0,
                "status": "unknown",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# Global metrics collector
metrics_collector = MetricsCollector()

def record_request(duration: float, status_code: int, method: str = "GET", endpoint: str = "/", client_ip: str = "unknown"):
    """Record request metrics (backward compatibility)"""
    metrics_collector.record_request(duration, status_code, method, endpoint, client_ip)

def get_system_metrics() -> Dict[str, Any]:
    """Get system metrics (backward compatibility)"""
    return metrics_collector.get_system_metrics()

def get_application_metrics(db: Session) -> Dict[str, Any]:
    """Get application metrics (backward compatibility)"""
    return metrics_collector.get_application_metrics(db)

def get_performance_metrics() -> Dict[str, Any]:
    """Get performance metrics (backward compatibility)"""
    return metrics_collector.get_performance_metrics()

# Enhanced API endpoints
@router.get("/enhanced/dashboard")
async def get_enhanced_dashboard_metrics(db: Session = Depends(get_db)):
    """Get enhanced dashboard metrics with health scoring"""
    return {
        "system": metrics_collector.get_system_metrics(),
        "performance": metrics_collector.get_performance_metrics(),
        "application": metrics_collector.get_application_metrics(db),
        "health": metrics_collector.get_health_score(),
        "timestamp": datetime.now().isoformat()
    }

@router.get("/enhanced/health")
async def get_system_health():
    """Get system health score and status"""
    return metrics_collector.get_health_score()

@router.get("/enhanced/performance/history")
async def get_performance_history(hours: int = 1):
    """Get performance metrics history"""
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    with metrics_collector.lock:
        # Filter recent data
        recent_requests = [r for r in metrics_collector.metrics_history["requests"] 
                          if datetime.fromisoformat(r["timestamp"]) > cutoff_time]
        recent_errors = [e for e in metrics_collector.metrics_history["errors"] 
                        if datetime.fromisoformat(e["timestamp"]) > cutoff_time]
    
    return {
        "time_range_hours": hours,
        "requests": recent_requests,
        "errors": recent_errors,
        "summary": {
            "total_requests": len(recent_requests),
            "total_errors": len(recent_errors),
            "error_rate": len(recent_errors) / max(1, len(recent_requests)) * 100
        }
    }

@router.get("/enhanced/alerts")
async def get_system_alerts():
    """Get active system alerts based on metrics"""
    alerts = []
    health_score = metrics_collector.get_health_score()
    system_metrics = metrics_collector.get_system_metrics()
    performance_metrics = metrics_collector.get_performance_metrics()
    
    # CPU alerts
    if system_metrics.get("cpu_percent", 0) > 90:
        alerts.append({
            "level": "critical",
            "type": "cpu_usage",
            "message": f"High CPU usage: {system_metrics['cpu_percent']:.1f}%",
            "value": system_metrics["cpu_percent"],
            "threshold": 90
        })
    elif system_metrics.get("cpu_percent", 0) > 75:
        alerts.append({
            "level": "warning",
            "type": "cpu_usage",
            "message": f"Elevated CPU usage: {system_metrics['cpu_percent']:.1f}%",
            "value": system_metrics["cpu_percent"],
            "threshold": 75
        })
    
    # Memory alerts
    if system_metrics.get("memory_percent", 0) > 90:
        alerts.append({
            "level": "critical",
            "type": "memory_usage",
            "message": f"High memory usage: {system_metrics['memory_percent']:.1f}%",
            "value": system_metrics["memory_percent"],
            "threshold": 90
        })
    elif system_metrics.get("memory_percent", 0) > 80:
        alerts.append({
            "level": "warning",
            "type": "memory_usage",
            "message": f"Elevated memory usage: {system_metrics['memory_percent']:.1f}%",
            "value": system_metrics["memory_percent"],
            "threshold": 80
        })
    
    # Error rate alerts
    error_rate = performance_metrics["errors"]["rate_percent"]
    if error_rate > 10:
        alerts.append({
            "level": "critical",
            "type": "error_rate",
            "message": f"High error rate: {error_rate:.1f}%",
            "value": error_rate,
            "threshold": 10
        })
    elif error_rate > 5:
        alerts.append({
            "level": "warning",
            "type": "error_rate",
            "message": f"Elevated error rate: {error_rate:.1f}%",
            "value": error_rate,
            "threshold": 5
        })
    
    # Response time alerts
    avg_response_time = performance_metrics["response_times"]["avg"]
    if avg_response_time > 5.0:  # 5 seconds
        alerts.append({
            "level": "warning",
            "type": "response_time",
            "message": f"Slow response time: {avg_response_time:.2f}s",
            "value": avg_response_time,
            "threshold": 5.0
        })
    
    return {
        "alerts": alerts,
        "total_alerts": len(alerts),
        "health_status": health_score["status"],
        "timestamp": datetime.now().isoformat()
    }

# Start monitoring when module is imported
metrics_collector.start_monitoring()

logger.info("Enhanced metrics module initialized")
