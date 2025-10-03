import logging
import logging.handlers
import json
import sys
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import psutil
import traceback

class StructuredFormatter(logging.Formatter):
    """Enhanced formatter with structured logging capabilities"""

    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        # Add structured data
        structured_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.thread,
            "thread_name": record.threadName
        }

        # Add exception info if present
        if record.exc_info:
            structured_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "Unknown",
                "message": str(record.exc_info[1]) if record.exc_info[1] else "",
                "traceback": traceback.format_exception(*record.exc_info)
            }

        # Add extra fields from record
        if self.include_extra and hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                             'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                             'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                             'thread', 'threadName', 'processName', 'process', 'message']:
                    structured_data[key] = value

        # Format as JSON for structured logs
        try:
            return json.dumps(structured_data, default=str, ensure_ascii=False)
        except:
            # Fallback to regular formatting
            return super().format(record)

class PerformanceMonitor:
    """Monitor and log performance metrics"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.metrics = defaultdict(list)
        self.lock = threading.Lock()

    def log_performance(self, operation: str, duration: float, **extra):
        """Log performance metric"""
        with self.lock:
            self.metrics[operation].append({
                "duration": duration,
                "timestamp": datetime.now().isoformat(),
                **extra
            })

            # Keep only last 1000 metrics per operation
            if len(self.metrics[operation]) > 1000:
                self.metrics[operation] = self.metrics[operation][-1000:]

        self.logger.info(f"Performance: {operation} took {duration:.3f}s",
                        extra={"operation": operation, "duration": duration, **extra})

    def get_performance_stats(self, operation: str = None) -> Dict[str, Any]:
        """Get performance statistics"""
        with self.lock:
            if operation:
                metrics = self.metrics.get(operation, [])
                if not metrics:
                    return {}

                durations = [m["duration"] for m in metrics]
                return {
                    "operation": operation,
                    "count": len(durations),
                    "avg_duration": sum(durations) / len(durations),
                    "min_duration": min(durations),
                    "max_duration": max(durations),
                    "last_updated": metrics[-1]["timestamp"] if metrics else None
                }
            else:
                return {op: self.get_performance_stats(op) for op in self.metrics.keys()}

class LogAggregator:
    """Aggregate and analyze logs for insights"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.error_counts = defaultdict(int)
        self.warning_counts = defaultdict(int)
        self.request_counts = defaultdict(int)
        self.lock = threading.Lock()

    def log_error(self, error_type: str, message: str, **extra):
        """Log and count errors"""
        with self.lock:
            self.error_counts[error_type] += 1

        self.logger.error(f"Error [{error_type}]: {message}",
                         extra={"error_type": error_type, **extra})

    def log_warning(self, warning_type: str, message: str, **extra):
        """Log and count warnings"""
        with self.lock:
            self.warning_counts[warning_type] += 1

        self.logger.warning(f"Warning [{warning_type}]: {message}",
                           extra={"warning_type": warning_type, **extra})

    def log_request(self, endpoint: str, method: str, status_code: int, duration: float):
        """Log API request"""
        with self.lock:
            self.request_counts[f"{method} {endpoint}"] += 1

        level = logging.INFO if status_code < 400 else logging.WARNING if status_code < 500 else logging.ERROR
        self.logger.log(level, f"Request: {method} {endpoint} -> {status_code} ({duration:.3f}s)",
                       extra={"endpoint": endpoint, "method": method, "status_code": status_code, "duration": duration})

    def get_aggregated_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics"""
        with self.lock:
            return {
                "errors": dict(self.error_counts),
                "warnings": dict(self.warning_counts),
                "requests": dict(self.request_counts),
                "total_errors": sum(self.error_counts.values()),
                "total_warnings": sum(self.warning_counts.values()),
                "total_requests": sum(self.request_counts.values())
            }

class EnhancedLogger:
    """Enhanced logging system with monitoring and analytics"""

    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.logger = None
        self.performance_monitor = None
        self.log_aggregator = None
        self.setup_complete = False

    def setup_logging(self) -> logging.Logger:
        """Setup enhanced logging configuration"""

        # Load config
        if self.config_path is None:
            import os
            self.config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')

        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
        except FileNotFoundError:
            config = {"app": {"log_level": "INFO"}}
            print(f"Warning: Config file not found at {self.config_path}, using defaults")

        log_level = getattr(logging, config.get("app", {}).get("log_level", "INFO").upper())
        logs_dir = Path(config.get("paths", {}).get("logs_dir", "logs/"))
        logs_dir.mkdir(exist_ok=True)

        # Create main logger
        logger = logging.getLogger("ultra_pinnacle")
        logger.setLevel(log_level)

        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Console handler with structured formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # Structured JSON file handler
        json_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "ultra_pinnacle.json",
            maxBytes=50*1024*1024,  # 50MB
            backupCount=10
        )
        json_handler.setLevel(logging.DEBUG)  # Log everything to JSON
        json_formatter = StructuredFormatter()
        json_handler.setFormatter(json_formatter)
        logger.addHandler(json_handler)

        # Traditional text file handler
        text_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "ultra_pinnacle.log",
            maxBytes=20*1024*1024,  # 20MB
            backupCount=5
        )
        text_handler.setLevel(log_level)
        text_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        text_handler.setFormatter(text_formatter)
        logger.addHandler(text_handler)

        # Error-only handler
        error_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "errors.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d\n%(message)s\n%(exc_text)s'
        )
        error_handler.setFormatter(error_formatter)
        logger.addHandler(error_handler)

        # Initialize monitoring components
        self.logger = logger
        self.performance_monitor = PerformanceMonitor(logger)
        self.log_aggregator = LogAggregator(logger)

        # Start cleanup thread
        cleanup_thread = threading.Thread(target=self._cleanup_old_logs, daemon=True)
        cleanup_thread.start()

        self.setup_complete = True
        logger.info("Enhanced logging system initialized")

        return logger

    def _cleanup_old_logs(self):
        """Periodically clean up old log files"""
        while True:
            try:
                logs_dir = Path(self.config_path).parent / "logs"
                if logs_dir.exists():
                    # Remove log files older than 30 days
                    cutoff = datetime.now() - timedelta(days=30)
                    for log_file in logs_dir.glob("*.log*"):
                        if log_file.stat().st_mtime < cutoff.timestamp():
                            log_file.unlink()
                            self.logger.info(f"Removed old log file: {log_file}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error cleaning up logs: {e}")

            time.sleep(86400)  # Clean up once per day

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if self.performance_monitor:
            return self.performance_monitor.get_performance_stats()
        return {}

    def get_aggregated_stats(self) -> Dict[str, Any]:
        """Get aggregated logging statistics"""
        if self.log_aggregator:
            return self.log_aggregator.get_aggregated_stats()
        return {}

    def log_performance(self, operation: str, duration: float, **extra):
        """Log performance metric"""
        if self.performance_monitor:
            self.performance_monitor.log_performance(operation, duration, **extra)

    def log_error(self, error_type: str, message: str, **extra):
        """Log error with aggregation"""
        if self.log_aggregator:
            self.log_aggregator.log_error(error_type, message, **extra)

    def log_warning(self, warning_type: str, message: str, **extra):
        """Log warning with aggregation"""
        if self.log_aggregator:
            self.log_aggregator.log_warning(warning_type, message, **extra)

    def log_request(self, endpoint: str, method: str, status_code: int, duration: float):
        """Log API request"""
        if self.log_aggregator:
            self.log_aggregator.log_request(endpoint, method, status_code, duration)

# Global enhanced logger instance
enhanced_logger = EnhancedLogger()

def setup_logging(config_path: str = None):
    """Setup enhanced logging configuration"""
    return enhanced_logger.setup_logging()

# Global logger instance (backward compatibility)
logger = enhanced_logger.logger or setup_logging()