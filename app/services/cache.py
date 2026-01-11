"""
VitaFlow API - Redis Cache Service.

Redis-based caching for AI responses to reduce API costs and latency.
"""

import json
import hashlib
import logging
import socket
from typing import Optional, Any, Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CacheService:
    """
    Redis cache service for caching AI responses.

    Uses Redis for fast key-value storage with TTL support.
    Lazy-initializes to allow app startup without Redis.
    Includes circuit breaker pattern for resilience.
    """

    def __init__(self, redis_url: str):
        """Initialize Redis cache client (lazy connection)."""
        self._redis_url = redis_url
        self._client = None
        self._available = None
        self._circuit_open_until = None
        self._failure_count = 0
        self._circuit_threshold = 5
        self._circuit_timeout = 60
        self.logger = logging.getLogger(__name__)
    
    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open."""
        if self._circuit_open_until:
            if datetime.now() < self._circuit_open_until:
                return True
            # Circuit timeout expired, allow retry
            self._circuit_open_until = None
            self._failure_count = 0
        return False

    def _record_failure(self):
        """Record failure and potentially open circuit."""
        self._failure_count += 1
        if self._failure_count >= self._circuit_threshold:
            self._circuit_open_until = datetime.now() + timedelta(seconds=self._circuit_timeout)
            self.logger.warning(
                f"Circuit breaker OPEN for {self._circuit_timeout}s after {self._failure_count} failures"
            )

    def _record_success(self):
        """Reset failure counter on success."""
        if self._failure_count > 0:
            self._failure_count = 0
            self.logger.info("Circuit breaker reset after successful operation")

    @property
    def client(self):
        """Lazy-load Redis client with connection pooling."""
        if self._client is None:
            try:
                import redis.asyncio as redis
                self._client = redis.from_url(
                    self._redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=50,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    socket_keepalive=True,
                    socket_keepalive_options={
                        socket.TCP_KEEPIDLE: 60,
                        socket.TCP_KEEPINTVL: 30,
                        socket.TCP_KEEPCNT: 3
                    },
                    retry_on_timeout=True,
                    retry_on_error=[redis.exceptions.ConnectionError],
                    retry=redis.asyncio.Retry(redis.backoff.ExponentialBackoff(), 3)
                )
            except Exception as e:
                self.logger.warning(f"Redis init failed: {e}")
                self._available = False
        return self._client
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value by key with circuit breaker."""
        if self._available is False or self._is_circuit_open():
            return None
        try:
            if self.client is None:
                return None
            value = await self.client.get(key)
            if value:
                self.logger.debug(f"Cache hit: {key}")
                self._record_success()
                return json.loads(value)
            return None
        except Exception as e:
            self.logger.debug(f"Cache get error: {e}")
            self._record_failure()
            self._available = False
            return None
    
    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """Set cached value with TTL and circuit breaker."""
        if self._available is False or self._is_circuit_open():
            return False
        try:
            if self.client is None:
                return False
            json_value = json.dumps(value)
            await self.client.setex(key, ttl_seconds, json_value)
            self._record_success()
            return True
        except Exception as e:
            self.logger.debug(f"Cache set error: {e}")
            self._record_failure()
            self._available = False
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete cached value."""
        if self._available is False:
            return False
        try:
            if self.client is None:
                return False
            await self.client.delete(key)
            return True
        except Exception as e:
            self.logger.debug(f"Cache delete error: {e}")
            return False
    
    @staticmethod
    def generate_key(prefix: str, params: Dict[str, Any]) -> str:
        """Generate deterministic cache key from parameters."""
        params_str = json.dumps(params, sort_keys=True)
        hash_value = hashlib.md5(params_str.encode()).hexdigest()[:12]
        return f"{prefix}:{hash_value}"
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple cached values efficiently using pipeline."""
        if self._available is False or self._is_circuit_open():
            return {}
        try:
            if self.client is None:
                return {}
            pipeline = self.client.pipeline()
            for key in keys:
                pipeline.get(key)
            values = await pipeline.execute()
            result = {}
            for key, value in zip(keys, values):
                if value:
                    try:
                        result[key] = json.loads(value)
                    except json.JSONDecodeError:
                        self.logger.warning(f"Failed to decode cached value for key: {key}")
            self._record_success()
            return result
        except Exception as e:
            self.logger.debug(f"Cache get_many error: {e}")
            self._record_failure()
            return {}

    async def set_many(self, items: Dict[str, Any], ttl_seconds: int = 3600) -> bool:
        """Set multiple cached values in pipeline."""
        if self._available is False or self._is_circuit_open():
            return False
        try:
            if self.client is None:
                return False
            pipeline = self.client.pipeline()
            for key, value in items.items():
                json_value = json.dumps(value)
                pipeline.setex(key, ttl_seconds, json_value)
            await pipeline.execute()
            self._record_success()
            return True
        except Exception as e:
            self.logger.debug(f"Cache set_many error: {e}")
            self._record_failure()
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern (use sparingly, can be slow)."""
        if self._available is False or self._is_circuit_open():
            return 0
        try:
            if self.client is None:
                return 0
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                deleted = await self.client.delete(*keys)
                self._record_success()
                return deleted
            return 0
        except Exception as e:
            self.logger.debug(f"Cache delete_pattern error: {e}")
            self._record_failure()
            return 0

    async def get_ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL for a key in seconds."""
        if self._available is False or self._is_circuit_open():
            return None
        try:
            if self.client is None:
                return None
            ttl = await self.client.ttl(key)
            self._record_success()
            return ttl if ttl > 0 else None
        except Exception as e:
            self.logger.debug(f"Cache get_ttl error: {e}")
            self._record_failure()
            return None

    async def extend_ttl(self, key: str, additional_seconds: int) -> bool:
        """Extend TTL of existing key."""
        if self._available is False or self._is_circuit_open():
            return False
        try:
            if self.client is None:
                return False
            current_ttl = await self.client.ttl(key)
            if current_ttl > 0:
                new_ttl = current_ttl + additional_seconds
                await self.client.expire(key, new_ttl)
                self._record_success()
                return True
            return False
        except Exception as e:
            self.logger.debug(f"Cache extend_ttl error: {e}")
            self._record_failure()
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis statistics for monitoring."""
        if self._available is False or self._is_circuit_open():
            return {}
        try:
            if self.client is None:
                return {}
            info = await self.client.info()
            stats = {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "used_memory": info.get("used_memory", 0),
                "maxmemory": info.get("maxmemory", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "evicted_keys": info.get("evicted_keys", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec", 0)
            }
            self._record_success()
            return stats
        except Exception as e:
            self.logger.debug(f"Cache get_stats error: {e}")
            self._record_failure()
            return {}

    async def healthcheck(self) -> bool:
        """Check Redis connection health."""
        if self._available is False:
            return False
        try:
            if self.client is None:
                return False
            await self.client.ping()
            self._available = True
            self._record_success()
            return True
        except Exception:
            self._available = False
            self._record_failure()
            return False


# Global cache instance - lazy initialized
try:
    from settings import settings
    cache_service = CacheService(settings.REDIS_URL)
except Exception:
    # Fallback for when config isn't available
    cache_service = CacheService("redis://localhost:6379/0")

