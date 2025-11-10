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

        # Semantic cache storage (query embeddings for similarity matching)
        self._query_embeddings: dict[str, list[float]] = {}  # cache_key -> embedding
        self._semantic_threshold = 0.95  # Cosine similarity threshold for cache hit

        # Metrics
        self.hits = 0
        self.misses = 0
        self.semantic_hits = 0
        self.total_saved_cost = 0.0

        # Initialize embedder for semantic caching
        self.embedder = None
        if enable_semantic:
            try:
                from green_gov_rag.rag.embeddings import ChunkEmbedder

                self.embedder = ChunkEmbedder(provider="huggingface")
                logger.info("Semantic cache enabled (threshold: 0.95)")
            except Exception as e:
                logger.warning(f"Semantic cache initialization failed: {e}")
                self.enable_semantic = False

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

    async def get(self, cache_key: str, query: Optional[str] = None) -> Optional[str]:
        """Get cached response by cache key (async wrapper).

        Args:
            cache_key: Pre-computed cache key
            query: Original query text (for semantic caching)

        Returns:
            Cached response or None
        """
        # Level 1: Check exact match in memory cache
        if cache_key in self._memory_cache:
            entry = self._memory_cache[cache_key]
            entry.hits += 1
            self.hits += 1
            logger.debug(
                f"Cache HIT (exact, memory): {cache_key[:8]}... (hits: {entry.hits})"
            )
            return entry.value

        # Level 2: Check exact match in Redis cache
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
                    logger.debug(f"Cache HIT (exact, redis): {cache_key[:8]}...")
                    return cached_data
            except Exception as e:
                logger.warning(f"Redis get error: {e}")

        # Level 3: Semantic similarity search (if enabled and query provided)
        if self.enable_semantic and self.embedder and query:
            try:
                similar_key, similarity = self._find_similar_query(query)
                if similar_key and similarity >= self._semantic_threshold:
                    # Found semantically similar cached query
                    if similar_key in self._memory_cache:
                        entry = self._memory_cache[similar_key]
                        entry.hits += 1
                        self.semantic_hits += 1
                        logger.info(
                            f"Cache HIT (semantic): {similar_key[:8]}... "
                            f"(similarity: {similarity:.3f}, threshold: {self._semantic_threshold})"
                        )
                        return entry.value
            except Exception as e:
                logger.warning(f"Semantic cache lookup error: {e}")

        # Cache miss
        self.misses += 1
        logger.debug(f"Cache MISS: {cache_key[:8]}...")
        return None

    def _find_similar_query(self, query: str) -> tuple[Optional[str], float]:
        """Find most similar cached query using cosine similarity.

        Args:
            query: Query text to match

        Returns:
            Tuple of (best_matching_cache_key, similarity_score)
        """
        if not self._query_embeddings or not self.embedder:
            return None, 0.0

        # Embed the query (access underlying embedder from ChunkEmbedder)
        query_embedding = self.embedder.embedder.embed_query(query)

        # Calculate cosine similarity with all cached queries
        best_key = None
        best_similarity = 0.0

        for cache_key, cached_embedding in self._query_embeddings.items():
            similarity = self._cosine_similarity(query_embedding, cached_embedding)
            if similarity > best_similarity:
                best_similarity = similarity
                best_key = cache_key

        return best_key, best_similarity

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score (0-1)
        """
        import math

        # Dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        # Magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    async def set(
        self,
        key: str,
        value: str,
        query: Optional[str] = None,
        source_documents: list[str] | None = None,
        estimated_cost: float = 0.02,
    ) -> None:
        """Store response in cache (async wrapper).

        Args:
            key: Pre-computed cache key
            value: LLM response to cache
            query: Original query text (for semantic caching)
            source_documents: List of source document IDs
            estimated_cost: Estimated API cost (for metrics)
        """
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            source_documents=source_documents or [],
        )

        # Store in memory cache
        self._set_memory_cache(key, entry)

        # Store query embedding for semantic caching
        if self.enable_semantic and self.embedder and query:
            try:
                query_embedding = self.embedder.embedder.embed_query(query)
                self._query_embeddings[key] = query_embedding
                logger.debug(f"Stored query embedding for semantic cache: {key[:8]}...")
            except Exception as e:
                logger.warning(f"Failed to store query embedding: {e}")

        # Store in Redis cache
        if self.enable_redis and self.redis_client:
            try:
                self.redis_client.setex(
                    f"llm_cache:{key}",
                    self.cache_ttl,
                    value,
                )
                # Store metadata separately
                metadata = {
                    "created_at": entry.created_at.isoformat(),
                    "source_documents": json.dumps(source_documents or []),
                }
                self.redis_client.setex(
                    f"llm_cache_meta:{key}",
                    self.cache_ttl,
                    json.dumps(metadata),
                )
                logger.debug(f"Cached in Redis: {key[:8]}... (TTL: {self.cache_ttl}s)")
            except Exception as e:
                logger.warning(f"Redis set error: {e}")

        # Update cost savings
        self.total_saved_cost += estimated_cost
        logger.debug(f"Cached response: {key[:8]}...")

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
