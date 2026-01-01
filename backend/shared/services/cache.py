# Tenant-Aware Caching Service
from typing import Any, Optional, Dict, List, Set, Union
from datetime import datetime, timedelta
import json
import hashlib
import logging
from enum import Enum
import asyncio
import redis.asyncio as redis
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class CacheLevel(str, Enum):
    """Cache levels for multi-tier caching"""
    L1_MEMORY = "l1_memory"      # In-process memory cache
    L2_REDIS = "l2_redis"        # Redis distributed cache
    L3_DATABASE = "l3_database"  # Database query cache


class CacheStrategy(str, Enum):
    """Cache invalidation strategies"""
    TTL = "ttl"                  # Time-to-live based
    LRU = "lru"                  # Least Recently Used
    LFU = "lfu"                  # Least Frequently Used
    WRITE_THROUGH = "write_through"  # Write to cache and storage
    WRITE_BEHIND = "write_behind"    # Write to cache, async to storage


@dataclass
class CacheConfig:
    """Cache configuration"""
    max_memory_mb: int = 100
    default_ttl_seconds: int = 300
    strategy: CacheStrategy = CacheStrategy.LRU
    enable_l1: bool = True
    enable_l2: bool = True
    compression: bool = False
    encryption: bool = False


@dataclass
class CacheStats:
    """Cache statistics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    memory_usage_mb: float = 0.0
    hit_rate: float = 0.0
    avg_response_time_ms: float = 0.0


class AppCache:
    """Multi-level caching system"""
    
    def __init__(self, redis_client: redis.Redis, config: CacheConfig):
        self.redis = redis_client
        self.config = config
        
        # L1 Cache (in-memory)
        self._l1_cache: Dict[str, Any] = {}
        self._l1_access_times: Dict[str, datetime] = {}
        self._l1_access_counts: Dict[str, int] = {}
        
        # Cache statistics
        self.stats = CacheStats()
        
        # Cache key prefix
        self.key_prefix = "app"
    
    def _generate_cache_key(self, key: str, namespace: str = "default") -> str:
        """Generate tenant-scoped cache key"""
        # Create hierarchical key structure
        cache_key = f"{self.key_prefix}:{namespace}:{key}"
        
        # Hash long keys to prevent Redis key length issues
        if len(cache_key) > 250:
            key_hash = hashlib.sha256(cache_key.encode()).hexdigest()[:16]
            cache_key = f"{self.key_prefix}:{namespace}:hash:{key_hash}"
        
        return cache_key
    
    async def get(
        self,
        key: str,
        namespace: str = "default",
        use_l1: bool = True,
        use_l2: bool = True
    ) -> Optional[Any]:
        """Get value from cache with multi-level fallback"""
        cache_key = self._generate_cache_key(key, namespace)
        start_time = datetime.utcnow()
        
        try:
            # L1 Cache check (in-memory)
            if use_l1 and self.config.enable_l1:
                if cache_key in self._l1_cache:
                    self._update_l1_access(cache_key)
                    self.stats.hits += 1
                    self._update_response_time(start_time)
                    logger.debug(f"L1 cache hit for {cache_key}")
                    return self._l1_cache[cache_key]
            
            # L2 Cache check (Redis)
            if use_l2 and self.config.enable_l2:
                value = await self.redis.get(cache_key)
                if value is not None:
                    # Deserialize value
                    deserialized_value = self._deserialize(value)
                    
                    # Promote to L1 cache
                    if use_l1 and self.config.enable_l1:
                        await self._set_l1(cache_key, deserialized_value)
                    
                    self.stats.hits += 1
                    self._update_response_time(start_time)
                    logger.debug(f"L2 cache hit for {cache_key}")
                    return deserialized_value
            
            # Cache miss
            self.stats.misses += 1
            self._update_response_time(start_time)
            logger.debug(f"Cache miss for {cache_key}")
            return None
            
        except Exception as e:
            logger.error(f"Cache get error for {cache_key}: {e}")
            self.stats.misses += 1
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: str = "default",
        use_l1: bool = True,
        use_l2: bool = True
    ) -> bool:
        """Set value in cache with multi-level storage"""
        cache_key = self._generate_cache_key(key, namespace)
        ttl = ttl or self.config.default_ttl_seconds
        
        try:
            # Set in L1 cache (in-memory)
            if use_l1 and self.config.enable_l1:
                await self._set_l1(cache_key, value, ttl)
            
            # Set in L2 cache (Redis)
            if use_l2 and self.config.enable_l2:
                serialized_value = self._serialize(value)
                await self.redis.setex(cache_key, ttl, serialized_value)
            
            logger.debug(f"Cache set for {cache_key} with TTL {ttl}s")
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for {cache_key}: {e}")
            return False
    
    async def delete(
        self,
        key: str,
        namespace: str = "default",
        use_l1: bool = True,
        use_l2: bool = True
    ) -> bool:
        """Delete value from cache"""
        cache_key = self._generate_cache_key(key, namespace)
        
        try:
            # Delete from L1 cache
            if use_l1 and cache_key in self._l1_cache:
                del self._l1_cache[cache_key]
                self._l1_access_times.pop(cache_key, None)
                self._l1_access_counts.pop(cache_key, None)
            
            # Delete from L2 cache
            if use_l2:
                await self.redis.delete(cache_key)
            
            logger.debug(f"Cache delete for {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"Cache delete error for {cache_key}: {e}")
            return False
    
    async def invalidate_namespace(self, namespace: str) -> int:
        """Invalidate all keys in a namespace"""
        pattern = f"{self.key_prefix}:{namespace}:*"
        
        try:
            # Invalidate L1 cache
            l1_deleted = 0
            keys_to_delete = [k for k in self._l1_cache.keys() if k.startswith(f"{self.key_prefix}:{namespace}:")]
            for key in keys_to_delete:
                del self._l1_cache[key]
                self._l1_access_times.pop(key, None)
                self._l1_access_counts.pop(key, None)
                l1_deleted += 1
            
            # Invalidate L2 cache
            l2_deleted = 0
            async for key in self.redis.scan_iter(match=pattern):
                await self.redis.delete(key)
                l2_deleted += 1
            
            total_deleted = l1_deleted + l2_deleted
            logger.info(f"Invalidated {total_deleted} keys in namespace {namespace} for tenant {self.tenant_id}")
            return total_deleted
            
        except Exception as e:
            logger.error(f"Cache invalidation error for namespace {namespace}: {e}")
            return 0
    
    async def invalidate_tenant(self) -> int:
        """Invalidate all cache entries for this tenant"""
        pattern = f"{self.key_prefix}:*"
        
        try:
            # Clear L1 cache
            l1_count = len(self._l1_cache)
            self._l1_cache.clear()
            self._l1_access_times.clear()
            self._l1_access_counts.clear()
            
            # Clear L2 cache
            l2_count = 0
            async for key in self.redis.scan_iter(match=pattern):
                await self.redis.delete(key)
                l2_count += 1
            
            total_deleted = l1_count + l2_count
            logger.info(f"Invalidated all {total_deleted} cache entries")
            return total_deleted
            
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return 0
    
    async def get_stats(self) -> CacheStats:
        """Get cache statistics"""
        # Update memory usage
        self.stats.memory_usage_mb = self._calculate_l1_memory_usage()
        
        # Update hit rate
        total_requests = self.stats.hits + self.stats.misses
        self.stats.hit_rate = (self.stats.hits / total_requests * 100) if total_requests > 0 else 0.0
        
        return self.stats
    
    async def _set_l1(self, cache_key: str, value: Any, ttl: Optional[int] = None):
        """Set value in L1 cache with eviction policy"""
        # Check memory limits and evict if necessary
        await self._enforce_l1_memory_limit()
        
        self._l1_cache[cache_key] = value
        self._l1_access_times[cache_key] = datetime.utcnow()
        self._l1_access_counts[cache_key] = 1
    
    def _update_l1_access(self, cache_key: str):
        """Update L1 cache access statistics"""
        self._l1_access_times[cache_key] = datetime.utcnow()
        self._l1_access_counts[cache_key] = self._l1_access_counts.get(cache_key, 0) + 1
    
    async def _enforce_l1_memory_limit(self):
        """Enforce L1 cache memory limits with eviction"""
        current_memory = self._calculate_l1_memory_usage()
        
        if current_memory > self.config.max_memory_mb:
            # Evict based on strategy
            if self.config.strategy == CacheStrategy.LRU:
                await self._evict_lru()
            elif self.config.strategy == CacheStrategy.LFU:
                await self._evict_lfu()
            else:
                await self._evict_lru()  # Default to LRU
    
    async def _evict_lru(self):
        """Evict least recently used items"""
        if not self._l1_access_times:
            return
        
        # Sort by access time and remove oldest 25%
        sorted_keys = sorted(self._l1_access_times.items(), key=lambda x: x[1])
        evict_count = max(1, len(sorted_keys) // 4)
        
        for key, _ in sorted_keys[:evict_count]:
            self._l1_cache.pop(key, None)
            self._l1_access_times.pop(key, None)
            self._l1_access_counts.pop(key, None)
            self.stats.evictions += 1
    
    async def _evict_lfu(self):
        """Evict least frequently used items"""
        if not self._l1_access_counts:
            return
        
        # Sort by access count and remove least used 25%
        sorted_keys = sorted(self._l1_access_counts.items(), key=lambda x: x[1])
        evict_count = max(1, len(sorted_keys) // 4)
        
        for key, _ in sorted_keys[:evict_count]:
            self._l1_cache.pop(key, None)
            self._l1_access_times.pop(key, None)
            self._l1_access_counts.pop(key, None)
            self.stats.evictions += 1
    
    def _calculate_l1_memory_usage(self) -> float:
        """Calculate approximate L1 cache memory usage in MB"""
        try:
            total_size = 0
            for key, value in self._l1_cache.items():
                total_size += len(str(key).encode('utf-8'))
                total_size += len(str(value).encode('utf-8'))
            
            return total_size / (1024 * 1024)  # Convert to MB
        except Exception:
            return 0.0
    
    def _serialize(self, value: Any) -> str:
        """Serialize value for storage"""
        try:
            if self.config.compression:
                import gzip
                import base64
                json_str = json.dumps(value, default=str)
                compressed = gzip.compress(json_str.encode('utf-8'))
                return base64.b64encode(compressed).decode('utf-8')
            else:
                return json.dumps(value, default=str)
        except Exception as e:
            logger.error(f"Serialization error: {e}")
            return json.dumps(str(value))
    
    def _deserialize(self, value: str) -> Any:
        """Deserialize value from storage"""
        try:
            if self.config.compression:
                import gzip
                import base64
                compressed = base64.b64decode(value.encode('utf-8'))
                json_str = gzip.decompress(compressed).decode('utf-8')
                return json.loads(json_str)
            else:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Deserialization error: {e}")
            return value
    
    def _update_response_time(self, start_time: datetime):
        """Update average response time statistics"""
        response_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Simple moving average
        if self.stats.avg_response_time_ms == 0:
            self.stats.avg_response_time_ms = response_time_ms
        else:
            self.stats.avg_response_time_ms = (self.stats.avg_response_time_ms * 0.9) + (response_time_ms * 0.1)

