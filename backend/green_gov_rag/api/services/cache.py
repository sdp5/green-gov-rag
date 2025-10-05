"""Caching service for LLM responses."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CacheEntry(BaseModel):
    """Cache entry model."""

    key: str
    value: str
    created_at: datetime
    hits: int = 0
    source_documents: list[str] = []


class CacheService:
    """Service for caching LLM responses with multi-level support."""

    def __init__(
        self,
        enable_redis: bool = False,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        cache_ttl: int = 3600,
        enable_semantic: bool = False,
    ):
        """Initialize cache service.

        Args:
            enable_redis: Enable Redis caching
            redis_host: Redis host
            redis_port: Redis port
            cache_ttl: Cache TTL in seconds
            enable_semantic: Enable semantic similarity caching
        """
        self.enable_redis = enable_redis
        self.cache_ttl = cache_ttl
        self.enable_semantic = enable_semantic
        self.redis_client = None

        # In-memory cache (LRU with max 1000 entries)
        self._memory_cache: dict[str, CacheEntry] = {}
        self._max_memory_entries = 1000

        # Metrics
        self.hits = 0
        self.misses = 0
        self.total_saved_cost = 0.0

        # Initialize Redis if enabled
        if enable_redis:
            try:
                import redis

                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    decode_responses=True,
                    socket_connect_timeout=2,
                )
                # Test connection
                self.redis_client.ping()
                logger.info(f"Redis cache enabled: {redis_host}:{redis_port}")
            except ImportError:
                logger.warning(
                    "Redis library not installed. Install with: pip install redis"
                )
                self.enable_redis = False
            except Exception as e:
                logger.warning(
                    f"Redis connection failed: {e}. Using memory cache only."
                )
                self.enable_redis = False

    def _create_cache_key(
        self,
        query: str,
        context: str,
        filters: dict[str, Any] | None = None,
    ) -> str:
        """Create deterministic cache key from query components.

        Args:
            query: User query
            context: Retrieved context
            filters: Query filters (region, jurisdiction, topics)

        Returns:
            MD5 hash as cache key
        """
        filters_str = json.dumps(filters or {}, sort_keys=True)
        content = f"{query}|{context}|{filters_str}"
        return hashlib.md5(content.encode()).hexdigest()

    def get(
        self,
        query: str,
        context: str,
        filters: dict[str, Any] | None = None,
    ) -> Optional[str]:
        """Get cached response if available.

        Args:
            query: User query
            context: Retrieved context
            filters: Query filters

        Returns:
            Cached response or None
        """
        cache_key = self._create_cache_key(query, context, filters)

        # Level 1: Check memory cache
        if cache_key in self._memory_cache:
            entry = self._memory_cache[cache_key]
            entry.hits += 1
            self.hits += 1
            logger.debug(f"Cache HIT (memory): {cache_key[:8]}... (hits: {entry.hits})")
            return entry.value

        # Level 2: Check Redis cache
        if self.enable_redis and self.redis_client:
            try:
                cached_data = self.redis_client.get(f"llm_cache:{cache_key}")
                if cached_data and isinstance(cached_data, str):
                    # Promote to memory cache
                    entry = CacheEntry(
                        key=cache_key,
                        value=cached_data,
                        created_at=datetime.now(),
                        hits=1,
                    )
                    self._set_memory_cache(cache_key, entry)
                    self.hits += 1
                    logger.debug(f"Cache HIT (redis): {cache_key[:8]}...")
                    return cached_data
            except Exception as e:
                logger.warning(f"Redis get error: {e}")

        # Cache miss
        self.misses += 1
        logger.debug(f"Cache MISS: {cache_key[:8]}...")
        return None

    def set(
        self,
        query: str,
        context: str,
        response: str,
        filters: dict[str, Any] | None = None,
        source_documents: list[str] | None = None,
        estimated_cost: float = 0.02,
    ) -> None:
        """Store response in cache.

        Args:
            query: User query
            context: Retrieved context
            response: LLM response to cache
            filters: Query filters
            source_documents: List of source document IDs
            estimated_cost: Estimated API cost (for metrics)
        """
        cache_key = self._create_cache_key(query, context, filters)

        entry = CacheEntry(
            key=cache_key,
            value=response,
            created_at=datetime.now(),
            source_documents=source_documents or [],
        )

        # Store in memory cache
        self._set_memory_cache(cache_key, entry)

        # Store in Redis cache
        if self.enable_redis and self.redis_client:
            try:
                self.redis_client.setex(
                    f"llm_cache:{cache_key}",
                    self.cache_ttl,
                    response,
                )
                # Store metadata separately
                metadata = {
                    "created_at": entry.created_at.isoformat(),
                    "source_documents": json.dumps(source_documents or []),
                }
                self.redis_client.setex(
                    f"llm_cache_meta:{cache_key}",
                    self.cache_ttl,
                    json.dumps(metadata),
                )
                logger.debug(
                    f"Cached in Redis: {cache_key[:8]}... (TTL: {self.cache_ttl}s)"
                )
            except Exception as e:
                logger.warning(f"Redis set error: {e}")

        logger.debug(f"Cached response: {cache_key[:8]}...")

    def _set_memory_cache(self, key: str, entry: CacheEntry) -> None:
        """Set entry in memory cache with LRU eviction."""
        # Simple LRU: if full, remove oldest entry
        if len(self._memory_cache) >= self._max_memory_entries:
            # Remove oldest (first inserted)
            oldest_key = next(iter(self._memory_cache))
            del self._memory_cache[oldest_key]

        self._memory_cache[key] = entry

    def invalidate_by_document(self, document_id: str) -> int:
        """Invalidate cache entries that used a specific document.

        Args:
            document_id: Document ID to invalidate

        Returns:
            Number of entries invalidated
        """
        invalidated = 0

        # Invalidate from memory cache
        keys_to_remove = [
            key
            for key, entry in self._memory_cache.items()
            if document_id in entry.source_documents
        ]
        for key in keys_to_remove:
            del self._memory_cache[key]
            invalidated += 1

        # Invalidate from Redis
        if self.enable_redis and self.redis_client:
            try:
                # Scan for metadata entries
                for meta_key in self.redis_client.scan_iter("llm_cache_meta:*"):
                    meta_value = self.redis_client.get(meta_key)
                    metadata = json.loads(
                        meta_value if isinstance(meta_value, str) else "{}"
                    )
                    source_docs = json.loads(metadata.get("source_documents", "[]"))
                    if document_id in source_docs:
                        # Extract cache key from metadata key
                        cache_key = meta_key.replace("llm_cache_meta:", "")
                        self.redis_client.delete(f"llm_cache:{cache_key}")
                        self.redis_client.delete(meta_key)
                        invalidated += 1
            except Exception as e:
                logger.warning(f"Redis invalidation error: {e}")

        logger.info(
            f"Invalidated {invalidated} cache entries for document {document_id}"
        )
        return invalidated

    def clear(self) -> None:
        """Clear all cache entries."""
        self._memory_cache.clear()

        if self.enable_redis and self.redis_client:
            try:
                # Delete all cache entries
                for key in self.redis_client.scan_iter("llm_cache:*"):
                    self.redis_client.delete(key)
                for key in self.redis_client.scan_iter("llm_cache_meta:*"):
                    self.redis_client.delete(key)
                logger.info("Cleared Redis cache")
            except Exception as e:
                logger.warning(f"Redis clear error: {e}")

        logger.info("Cleared all cache")

    def get_metrics(self) -> dict[str, Any]:
        """Get cache performance metrics.

        Returns:
            Dictionary with cache metrics
        """
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        estimated_savings = self.hits * 0.02  # $0.02 per cached call

        metrics = {
            "total_requests": total_requests,
            "cache_hits": self.hits,
            "cache_misses": self.misses,
            "hit_rate_percent": round(hit_rate, 2),
            "memory_cache_size": len(self._memory_cache),
            "estimated_cost_savings_usd": round(estimated_savings, 2),
            "redis_enabled": self.enable_redis,
        }

        # Add Redis metrics if available
        if self.enable_redis and self.redis_client:
            try:
                info_dict: dict[str, Any] = self.redis_client.info("stats")  # type: ignore[assignment]
                db_size: int = self.redis_client.dbsize()  # type: ignore[assignment]
                metrics["redis_total_keys"] = db_size
                metrics["redis_hits"] = info_dict.get("keyspace_hits", 0)
                metrics["redis_misses"] = info_dict.get("keyspace_misses", 0)
            except Exception as e:
                logger.warning(f"Redis metrics error: {e}")

        return metrics
