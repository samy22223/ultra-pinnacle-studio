"""
Advanced Rate Limiting System for Ultra Pinnacle AI Studio
Implements sliding window algorithm with Redis/in-memory fallback
"""

import time
import asyncio
import threading
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import re
from collections import defaultdict, deque
import logging

logger = logging.getLogger("ultra_pinnacle")

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory rate limiting")

@dataclass
class RateLimitResult:
    """Result of a rate limit check"""
    allowed: bool
    remaining_requests: int
    reset_time: datetime
    retry_after: Optional[int] = None
    limit_type: str = "unknown"

@dataclass
class RateLimitConfig:
    """Configuration for a rate limit"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 5000
    burst_limit: int = 10
    window_seconds: int = 60

class SlidingWindowLimiter:
    """Sliding window rate limiter using Redis or in-memory storage"""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_client = None
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()
                logger.info("Redis connection established for rate limiting")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}, falling back to in-memory")
                self.redis_client = None

        # In-memory fallback storage
        self.memory_storage: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.lock = threading.Lock()

    def _get_key(self, identifier: str, limit_type: str, window: str) -> str:
        """Generate Redis/in-memory key"""
        return f"rate_limit:{limit_type}:{identifier}:{window}"

    def _cleanup_old_entries(self, entries: deque, window_seconds: int) -> deque:
        """Remove entries older than the window"""
        current_time = time.time()
        cutoff_time = current_time - window_seconds

        # Remove old entries from the left (oldest first)
        while entries and entries[0] < cutoff_time:
            entries.popleft()

        return entries

    def _check_memory_limit(self, key: str, limit: int, window_seconds: int) -> Tuple[bool, int]:
        """Check rate limit using in-memory storage"""
        with self.lock:
            entries = self.memory_storage[key]
            entries = self._cleanup_old_entries(entries, window_seconds)

            current_time = time.time()
            entries.append(current_time)
            self.memory_storage[key] = entries

            request_count = len(entries)
            return request_count <= limit, max(0, limit - request_count)

    def _check_redis_limit(self, key: str, limit: int, window_seconds: int) -> Tuple[bool, int]:
        """Check rate limit using Redis"""
        try:
            current_time = time.time()
            window_start = current_time - window_seconds

            # Remove old entries and count current ones
            removed_count = self.redis_client.zremrangebyscore(key, 0, window_start)
            current_count = self.redis_client.zcard(key)

            # Add current request
            self.redis_client.zadd(key, {str(current_time): current_time})
            self.redis_client.expire(key, window_seconds * 2)  # Expire key after 2x window

            new_count = current_count - removed_count + 1
            return new_count <= limit, max(0, limit - new_count)
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            return True, limit  # Allow on Redis failure

    def check_limit(self, identifier: str, limit: int, window_seconds: int, limit_type: str = "general") -> Tuple[bool, int]:
        """Check if request is within rate limit"""
        key = self._get_key(identifier, limit_type, f"{window_seconds}s")

        if self.redis_client:
            return self._check_redis_limit(key, limit, window_seconds)
        else:
            return self._check_memory_limit(key, limit, window_seconds)

    def get_remaining_time(self, identifier: str, limit_type: str, window_seconds: int) -> int:
        """Get seconds until oldest request expires"""
        key = self._get_key(identifier, limit_type, f"{window_seconds}s")

        if self.redis_client:
            try:
                # Get the oldest timestamp in the window
                oldest = self.redis_client.zrange(key, 0, 0, withscores=True)
                if oldest:
                    current_time = time.time()
                    oldest_time = oldest[0][1]
                    return max(0, int(window_seconds - (current_time - oldest_time)))
                return 0
            except Exception as e:
                logger.error(f"Redis get remaining time failed: {e}")
                return 0
        else:
            with self.lock:
                entries = self.memory_storage[key]
                if entries:
                    current_time = time.time()
                    oldest_time = entries[0]
                    return max(0, int(window_seconds - (current_time - oldest_time)))
                return 0

class RateLimitManager:
    """Main rate limiting manager with user and endpoint specific limits"""

    def __init__(self, redis_url: Optional[str] = None):
        self.limiter = SlidingWindowLimiter(redis_url)
        self.user_configs: Dict[int, RateLimitConfig] = {}
        self.endpoint_configs: Dict[str, RateLimitConfig] = {}
        self.global_config = RateLimitConfig(
            requests_per_minute=1000,
            requests_per_hour=10000,
            requests_per_day=50000,
            burst_limit=100
        )

        # Auto-adjustment settings
        self.auto_adjustment_enabled = True
        self.high_load_threshold = 80.0  # CPU/memory percentage
        self.low_load_threshold = 20.0
        self.adjustment_factor = 0.8  # Reduce limits by 20% under high load

        logger.info("Rate limit manager initialized")

    def load_user_config(self, user_id: int, config: RateLimitConfig):
        """Load rate limit configuration for a user"""
        self.user_configs[user_id] = config

    def load_endpoint_config(self, endpoint_pattern: str, config: RateLimitConfig):
        """Load rate limit configuration for an endpoint"""
        self.endpoint_configs[endpoint_pattern] = config

    def _match_endpoint_pattern(self, endpoint: str, pattern: str) -> bool:
        """Check if endpoint matches a pattern (supports wildcards)"""
        # Convert pattern to regex
        regex_pattern = pattern.replace('*', '.*')
        return bool(re.match(f"^{regex_pattern}$", endpoint))

    def _get_user_config(self, user_id: Optional[int]) -> RateLimitConfig:
        """Get rate limit config for user, fallback to global"""
        if user_id and user_id in self.user_configs:
            return self.user_configs[user_id]
        return self.global_config

    def _get_endpoint_config(self, endpoint: str) -> Optional[RateLimitConfig]:
        """Get rate limit config for endpoint if it matches any pattern"""
        for pattern, config in self.endpoint_configs.items():
            if self._match_endpoint_pattern(endpoint, pattern):
                return config
        return None

    def _calculate_effective_limits(self, base_config: RateLimitConfig) -> RateLimitConfig:
        """Apply auto-adjustment based on system load"""
        if not self.auto_adjustment_enabled:
            return base_config

        # Simple load check (in production, integrate with actual metrics)
        # For now, assume normal load
        load_factor = 1.0

        # TODO: Integrate with actual system metrics
        # if self._get_system_load() > self.high_load_threshold:
        #     load_factor = self.adjustment_factor

        return RateLimitConfig(
            requests_per_minute=int(base_config.requests_per_minute * load_factor),
            requests_per_hour=int(base_config.requests_per_hour * load_factor),
            requests_per_day=int(base_config.requests_per_day * load_factor),
            burst_limit=int(base_config.burst_limit * load_factor),
            window_seconds=base_config.window_seconds
        )

    def check_rate_limit(
        self,
        user_id: Optional[int],
        client_ip: str,
        endpoint: str,
        method: str = "GET"
    ) -> RateLimitResult:
        """Check rate limit for a request"""

        # Determine which config to use (endpoint-specific takes precedence)
        endpoint_config = self._get_endpoint_config(endpoint)
        user_config = self._get_user_config(user_id)

        # Use endpoint config if available, otherwise user config
        config = endpoint_config or user_config
        config = self._calculate_effective_limits(config)

        limit_type = "endpoint" if endpoint_config else "user"

        # Check burst limit (very short window)
        burst_allowed, burst_remaining = self.limiter.check_limit(
            f"{user_id or client_ip}:{endpoint}",
            config.burst_limit,
            10,  # 10 second burst window
            f"{limit_type}_burst"
        )

        if not burst_allowed:
            reset_time = datetime.now() + timedelta(seconds=self.limiter.get_remaining_time(
                f"{user_id or client_ip}:{endpoint}", f"{limit_type}_burst", 10
            ))
            return RateLimitResult(
                allowed=False,
                remaining_requests=burst_remaining,
                reset_time=reset_time,
                retry_after=10,
                limit_type=f"{limit_type}_burst"
            )

        # Check per-minute limit
        minute_allowed, minute_remaining = self.limiter.check_limit(
            f"{user_id or client_ip}:{endpoint}",
            config.requests_per_minute,
            60,
            f"{limit_type}_minute"
        )

        if not minute_allowed:
            reset_time = datetime.now() + timedelta(seconds=self.limiter.get_remaining_time(
                f"{user_id or client_ip}:{endpoint}", f"{limit_type}_minute", 60
            ))
            return RateLimitResult(
                allowed=False,
                remaining_requests=minute_remaining,
                reset_time=reset_time,
                retry_after=60,
                limit_type=f"{limit_type}_minute"
            )

        # Check per-hour limit
        hour_allowed, hour_remaining = self.limiter.check_limit(
            f"{user_id or client_ip}:{endpoint}",
            config.requests_per_hour,
            3600,
            f"{limit_type}_hour"
        )

        if not hour_allowed:
            reset_time = datetime.now() + timedelta(seconds=self.limiter.get_remaining_time(
                f"{user_id or client_ip}:{endpoint}", f"{limit_type}_hour", 3600
            ))
            return RateLimitResult(
                allowed=False,
                remaining_requests=hour_remaining,
                reset_time=reset_time,
                retry_after=3600,
                limit_type=f"{limit_type}_hour"
            )

        # Check per-day limit
        day_allowed, day_remaining = self.limiter.check_limit(
            f"{user_id or client_ip}:{endpoint}",
            config.requests_per_day,
            86400,
            f"{limit_type}_day"
        )

        if not day_allowed:
            reset_time = datetime.now() + timedelta(seconds=self.limiter.get_remaining_time(
                f"{user_id or client_ip}:{endpoint}", f"{limit_type}_day", 86400
            ))
            return RateLimitResult(
                allowed=False,
                remaining_requests=day_remaining,
                reset_time=reset_time,
                retry_after=86400,
                limit_type=f"{limit_type}_day"
            )

        # All checks passed
        reset_time = datetime.now() + timedelta(seconds=60)  # Default to 1 minute
        return RateLimitResult(
            allowed=True,
            remaining_requests=min(burst_remaining, minute_remaining, hour_remaining, day_remaining),
            reset_time=reset_time,
            limit_type=limit_type
        )

    def _get_system_load(self) -> float:
        """Get current system load (CPU + memory average)"""
        try:
            import psutil
            # Get CPU usage percentage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Get memory usage percentage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Return average of CPU and memory usage
            return (cpu_percent + memory_percent) / 2
        except ImportError:
            # Fallback if psutil not available
            try:
                # Simple CPU load using os
                import os
                loadavg = os.getloadavg()
                # Convert to percentage (assuming 4 CPU cores)
                return min(100.0, (loadavg[0] / 4.0) * 100)
            except (AttributeError, OSError):
                # Final fallback
                return 50.0
        except Exception:
            return 50.0

# Global rate limit manager instance
rate_limit_manager = RateLimitManager()

def get_rate_limit_manager() -> RateLimitManager:
    """Get the global rate limit manager instance"""
    return rate_limit_manager