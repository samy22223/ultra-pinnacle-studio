from typing import Dict, Any, Optional, List
import asyncio
import time
from functools import lru_cache
from cachetools import TTLCache, LRUCache
import redis
import json
from .logging_config import logger

class CacheManager:
    """
    Multi-layer caching system for Ultra Pinnacle AI Studio.

    Provides:
    - In-memory LRU cache for frequently accessed data
    - Redis cache for distributed caching (optional)
    - TTL-based expiration
    - Cache statistics and monitoring
    """

    def __init__(self, redis_url: Optional[str] = None, enable_redis: bool = False):
        # In-memory caches with different TTLs
        self.translation_cache = TTLCache(maxsize=10000, ttl=3600)  # 1 hour
        self.user_cache = TTLCache(maxsize=5000, ttl=1800)  # 30 minutes
        self.api_cache = TTLCache(maxsize=2000, ttl=300)  # 5 minutes
        self.static_cache = LRUCache(maxsize=1000)  # No expiration for static data

        # Redis cache (optional)
        self.redis_client = None
        if enable_redis and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()  # Test connection
                logger.info("Redis cache enabled")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self.redis_client = None

        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }

        # Cache keys prefixes
        self.prefixes = {
            "translation": "trans:",
            "user": "user:",
            "api": "api:",
            "static": "static:"
        }

    def _make_key(self, prefix: str, *args) -> str:
        """Create a cache key from prefix and arguments"""
        return f"{prefix}{':'.join(str(arg) for arg in args)}"

    def _serialize_value(self, value: Any) -> str:
        """Serialize value for storage"""
        if isinstance(value, (dict, list)):
            return json.dumps(value, default=str)
        return str(value)

    def _deserialize_value(self, value: str, expected_type: type = dict) -> Any:
        """Deserialize value from storage"""
        try:
            if expected_type == dict:
                return json.loads(value)
            elif expected_type == list:
                return json.loads(value)
            elif expected_type == int:
                return int(value)
            elif expected_type == float:
                return float(value)
            else:
                return value
        except (json.JSONDecodeError, ValueError):
            return value

    async def get(self, cache_type: str, key: str, expected_type: type = dict) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            cache_type: Type of cache ('translation', 'user', 'api', 'static')
            key: Cache key
            expected_type: Expected return type for deserialization

        Returns:
            Cached value or None if not found
        """
        try:
            cache = self._get_cache(cache_type)
            if not cache:
                return None

            full_key = self._make_key(self.prefixes[cache_type], key)

            # Try in-memory cache first
            if full_key in cache:
                self.stats["hits"] += 1
                return cache[full_key]

            # Try Redis if available
            if self.redis_client:
                redis_value = self.redis_client.get(full_key)
                if redis_value:
                    # Store in memory cache for faster future access
                    deserialized = self._deserialize_value(redis_value.decode(), expected_type)
                    cache[full_key] = deserialized
                    self.stats["hits"] += 1
                    return deserialized

            self.stats["misses"] += 1
            return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self.stats["errors"] += 1
            return None

    async def set(self, cache_type: str, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.

        Args:
            cache_type: Type of cache ('translation', 'user', 'api', 'static')
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (overrides default)

        Returns:
            True if successful, False otherwise
        """
        try:
            cache = self._get_cache(cache_type)
            if not cache:
                return False

            full_key = self._make_key(self.prefixes[cache_type], key)
            serialized = self._serialize_value(value)

            # Store in memory cache
            cache[full_key] = value
            self.stats["sets"] += 1

            # Store in Redis if available
            if self.redis_client:
                redis_ttl = ttl or self._get_default_ttl(cache_type)
                self.redis_client.setex(full_key, redis_ttl, serialized)

            return True

        except Exception as e:
            logger.error(f"Cache set error: {e}")
            self.stats["errors"] += 1
            return False

    async def delete(self, cache_type: str, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            cache_type: Type of cache
            key: Cache key

        Returns:
            True if successful, False otherwise
        """
        try:
            cache = self._get_cache(cache_type)
            if not cache:
                return False

            full_key = self._make_key(self.prefixes[cache_type], key)

            # Delete from memory cache
            if full_key in cache:
                del cache[full_key]

            # Delete from Redis
            if self.redis_client:
                self.redis_client.delete(full_key)

            self.stats["deletes"] += 1
            return True

        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            self.stats["errors"] += 1
            return False

    async def clear_cache(self, cache_type: Optional[str] = None) -> bool:
        """
        Clear cache(s).

        Args:
            cache_type: Specific cache type to clear, or None to clear all

        Returns:
            True if successful, False otherwise
        """
        try:
            if cache_type:
                cache = self._get_cache(cache_type)
                if cache:
                    cache.clear()
                if self.redis_client:
                    # Clear Redis keys with pattern
                    pattern = f"{self.prefixes[cache_type]}*"
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        self.redis_client.delete(*keys)
            else:
                # Clear all caches
                self.translation_cache.clear()
                self.user_cache.clear()
                self.api_cache.clear()
                self.static_cache.clear()
                if self.redis_client:
                    # Clear all keys with our prefixes
                    for prefix in self.prefixes.values():
                        pattern = f"{prefix}*"
                        keys = self.redis_client.keys(pattern)
                        if keys:
                            self.redis_client.delete(*keys)

            return True

        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            self.stats["errors"] += 1
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        return {
            "stats": self.stats.copy(),
            "hit_rate": round(hit_rate, 2),
            "cache_sizes": {
                "translation": len(self.translation_cache),
                "user": len(self.user_cache),
                "api": len(self.api_cache),
                "static": len(self.static_cache)
            },
            "redis_enabled": self.redis_client is not None
        }

    def _get_cache(self, cache_type: str):
        """Get the appropriate cache instance"""
        cache_map = {
            "translation": self.translation_cache,
            "user": self.user_cache,
            "api": self.api_cache,
            "static": self.static_cache
        }
        return cache_map.get(cache_type)

    def _get_default_ttl(self, cache_type: str) -> int:
        """Get default TTL for cache type"""
        ttl_map = {
            "translation": 3600,  # 1 hour
            "user": 1800,         # 30 minutes
            "api": 300,           # 5 minutes
            "static": 86400       # 24 hours
        }
        return ttl_map.get(cache_type, 300)

    # High-level caching methods for specific use cases

    async def get_translation(self, namespace: str, key: str, language: str) -> Optional[str]:
        """Get cached translation"""
        cache_key = f"{namespace}:{key}:{language}"
        return await self.get("translation", cache_key, str)

    async def set_translation(self, namespace: str, key: str, language: str, value: str):
        """Cache translation"""
        cache_key = f"{namespace}:{key}:{language}"
        await self.set("translation", cache_key, value)

    async def get_user_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get cached user data"""
        return await self.get("user", str(user_id), dict)

    async def set_user_data(self, user_id: int, data: Dict[str, Any]):
        """Cache user data"""
        await self.set("user", str(user_id), data)

    async def get_api_response(self, endpoint: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get cached API response"""
        # Create deterministic cache key from endpoint and sorted params
        param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        cache_key = f"{endpoint}?{param_str}"
        return await self.get("api", cache_key)

    async def set_api_response(self, endpoint: str, params: Dict[str, Any], response: Any):
        """Cache API response"""
        param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        cache_key = f"{endpoint}?{param_str}"
        await self.set("api", cache_key, response)

    async def invalidate_user_cache(self, user_id: int):
        """Invalidate all cached data for a user"""
        await self.delete("user", str(user_id))

    async def invalidate_translation_cache(self, namespace: Optional[str] = None):
        """Invalidate translation cache, optionally for specific namespace"""
        if namespace:
            # Clear specific namespace (would need pattern matching in Redis)
            pass
        else:
            await self.clear_cache("translation")

# Global cache manager instance
cache_manager = None

def get_cache_manager(redis_url: Optional[str] = None, enable_redis: bool = False) -> CacheManager:
    """Get or create the global cache manager instance."""
    global cache_manager
    if cache_manager is None:
        cache_manager = CacheManager(redis_url, enable_redis)
    return cache_manager

# Cached function decorators for common use cases
@lru_cache(maxsize=1000)
def cached_translation_lookup(namespace: str, key: str, language: str) -> Optional[str]:
    """LRU cached translation lookup (synchronous)"""
    # This would be used for synchronous translation lookups
    # Implementation would depend on the actual translation storage
    return None