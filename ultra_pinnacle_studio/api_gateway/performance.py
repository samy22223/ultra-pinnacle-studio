"""
Performance Optimization Module for Ultra Pinnacle AI Studio
Caching, connection pooling, and performance enhancements
"""

import time
import asyncio
import threading
from typing import Dict, List, Optional, Any, Callable, Awaitable
from functools import wraps, lru_cache
import json
import hashlib
from datetime import datetime, timedelta
from collections import OrderedDict
import aioredis
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import psutil

from .logging_config import logger

class LRUCache:
    """Thread-safe LRU cache with TTL support"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache = OrderedDict()
        self.expiration = {}
        self.lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            if key not in self.cache:
                return None

            # Check expiration
            if time.time() > self.expiration.get(key, 0):
                del self.cache[key]
                del self.expiration[key]
                return None

            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]

            self.cache[key] = value
            self.expiration[key] = time.time() + (ttl or self.default_ttl)

            # Remove oldest items if cache is full
            while len(self.cache) > self.max_size:
                oldest_key, _ = self.cache.popitem(last=False)
                del self.expiration[oldest_key]

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                del self.expiration[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.expiration.clear()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hit_rate": 0,  # Would need to track hits/misses
                "entries": list(self.cache.keys())
            }

class RedisCache:
    """Redis-based distributed cache"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis = None
        self.connected = False

    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis = await aioredis.from_url(self.redis_url)
            self.connected = True
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            self.connected = False

    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        if not self.connected or not self.redis:
            return None
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    async def set(self, key: str, value: str, ttl: int = 300) -> bool:
        """Set value in Redis with TTL"""
        if not self.connected or not self.redis:
            return False
        try:
            return await self.redis.setex(key, ttl, value)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        if not self.connected or not self.redis:
            return False
        try:
            return await self.redis.delete(key) > 0
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

class ConnectionPool:
    """HTTP connection pool for external API calls"""

    def __init__(self, max_connections: int = 100, timeout: int = 30):
        self.max_connections = max_connections
        self.timeout = timeout
        self.session = None

    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=self.max_connections, ttl_dns_cache=300)
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def request(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make HTTP request using pooled connection"""
        if not self.session:
            raise RuntimeError("Connection pool not initialized")
        return await self.session.request(method, url, **kwargs)

class AsyncTaskManager:
    """Manage async tasks with resource limits"""

    def __init__(self, max_workers: int = 10):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.semaphore = asyncio.Semaphore(max_workers * 2)  # Allow more concurrent tasks
        self.active_tasks = set()

    async def run_in_thread(self, func: Callable, *args, **kwargs) -> Any:
        """Run blocking function in thread pool"""
        async with self.semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self.executor, func, *args, **kwargs)

    async def run_async_task(self, coro: Awaitable) -> Any:
        """Run async task with tracking"""
        task = asyncio.create_task(coro)
        self.active_tasks.add(task)

        try:
            result = await task
            return result
        finally:
            self.active_tasks.discard(task)

    def get_active_task_count(self) -> int:
        """Get number of active tasks"""
        return len(self.active_tasks)

class DatabaseOptimizer:
    """Database query optimization and connection pooling"""

    def __init__(self):
        self.query_cache = LRUCache(max_size=500, default_ttl=600)  # 10 minute cache
        self.connection_pool_size = 20
        self.statement_timeout = 30000  # 30 seconds

    def optimize_query(self, query: str, params: tuple = None) -> str:
        """Optimize SQL query"""
        # Add basic optimizations
        optimized = query.strip()

        # Remove unnecessary spaces
        optimized = ' '.join(optimized.split())

        # Add query hints for better performance
        if "SELECT" in optimized.upper() and "LIMIT" not in optimized.upper():
            # Add LIMIT for potentially large result sets
            pass  # Would need more context

        return optimized

    def get_query_hash(self, query: str, params: tuple = None) -> str:
        """Generate hash for query caching"""
        query_str = f"{query}:{params}" if params else query
        return hashlib.md5(query_str.encode()).hexdigest()

    def cache_query_result(self, query_hash: str, result: Any, ttl: int = 600):
        """Cache query result"""
        self.query_cache.set(query_hash, result, ttl)

    def get_cached_result(self, query_hash: str) -> Optional[Any]:
        """Get cached query result"""
        return self.query_cache.get(query_hash)

class PerformanceMonitor:
    """Monitor and optimize performance"""

    def __init__(self):
        self.metrics = {
            "response_times": [],
            "memory_usage": [],
            "cpu_usage": [],
            "active_connections": []
        }
        self.lock = threading.Lock()
        self.monitoring = False

    def start_monitoring(self):
        """Start performance monitoring"""
        self.monitoring = True
        monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        monitor_thread.start()

    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring = False

    def _monitor_loop(self):
        """Monitor system performance"""
        while self.monitoring:
            try:
                with self.lock:
                    # Record metrics
                    self.metrics["memory_usage"].append({
                        "timestamp": datetime.now().isoformat(),
                        "usage": psutil.virtual_memory().percent
                    })

                    self.metrics["cpu_usage"].append({
                        "timestamp": datetime.now().isoformat(),
                        "usage": psutil.cpu_percent(interval=1)
                    })

                    # Keep only last 100 entries
                    for metric_list in self.metrics.values():
                        if len(metric_list) > 100:
                            metric_list[:] = metric_list[-100:]

            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")

            time.sleep(60)  # Monitor every minute

    def record_response_time(self, endpoint: str, method: str, duration: float):
        """Record API response time"""
        with self.lock:
            self.metrics["response_times"].append({
                "timestamp": datetime.now().isoformat(),
                "endpoint": endpoint,
                "method": method,
                "duration": duration
            })

            # Keep only last 1000 response times
            if len(self.metrics["response_times"]) > 1000:
                self.metrics["response_times"] = self.metrics["response_times"][-1000:]

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        with self.lock:
            stats = {}

            # Response time stats
            if self.metrics["response_times"]:
                durations = [r["duration"] for r in self.metrics["response_times"]]
                stats["response_times"] = {
                    "avg": sum(durations) / len(durations),
                    "min": min(durations),
                    "max": max(durations),
                    "p95": sorted(durations)[int(len(durations) * 0.95)],
                    "count": len(durations)
                }

            # Memory usage stats
            if self.metrics["memory_usage"]:
                memory_values = [m["usage"] for m in self.metrics["memory_usage"]]
                stats["memory_usage"] = {
                    "current": memory_values[-1] if memory_values else 0,
                    "avg": sum(memory_values) / len(memory_values),
                    "max": max(memory_values)
                }

            # CPU usage stats
            if self.metrics["cpu_usage"]:
                cpu_values = [c["usage"] for c in self.metrics["cpu_usage"]]
                stats["cpu_usage"] = {
                    "current": cpu_values[-1] if cpu_values else 0,
                    "avg": sum(cpu_values) / len(cpu_values),
                    "max": max(cpu_values)
                }

            return stats

# Performance optimization decorators
def cached(ttl: int = 300, key_prefix: str = ""):
    """Cache function results"""
    def decorator(func):
        cache = LRUCache(max_size=1000, default_ttl=ttl)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            key_data = f"{key_prefix}:{func.__name__}:{args}:{kwargs}"
            key = hashlib.md5(key_data.encode()).hexdigest()

            # Check cache
            cached_result = cache.get(key)
            if cached_result is not None:
                return cached_result

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            cache.set(key, result, ttl)
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            key_data = f"{key_prefix}:{func.__name__}:{args}:{kwargs}"
            key = hashlib.md5(key_data.encode()).hexdigest()

            # Check cache
            cached_result = cache.get(key)
            if cached_result is not None:
                return cached_result

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            cache.set(key, result, ttl)
            return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator

def timed_operation(operation_name: str = None):
    """Time function execution and log performance"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                # Log performance
                from .logging_config import enhanced_logger
                if enhanced_logger:
                    enhanced_logger.log_performance(
                        operation_name or func.__name__,
                        duration,
                        function=func.__name__
                    )

                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Operation {func.__name__} failed after {duration:.3f}s: {e}")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                # Log performance
                from .logging_config import enhanced_logger
                if enhanced_logger:
                    enhanced_logger.log_performance(
                        operation_name or func.__name__,
                        duration,
                        function=func.__name__
                    )

                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Operation {func.__name__} failed after {duration:.3f}s: {e}")
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator

# Global instances
lru_cache = LRUCache()
redis_cache = RedisCache()
connection_pool = ConnectionPool()
async_task_manager = AsyncTaskManager()
database_optimizer = DatabaseOptimizer()
performance_monitor = PerformanceMonitor()

# Start performance monitoring
performance_monitor.start_monitoring()

logger.info("Performance optimization module initialized")