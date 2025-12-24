"""Cache service for multi-tier caching."""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional, TypeVar

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.database import async_session_maker
from app.db.models.cache_entry import CacheEntry

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class CacheService:
    """Multi-tier cache service with database fallback.

    This service provides caching with:
    1. In-memory cache (optional, if Redis is configured)
    2. Database cache (SQLite/PostgreSQL)
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        """Initialize the cache service.

        Args:
            settings: Application settings
        """
        self._settings = settings or get_settings()
        self._memory_cache: dict[str, tuple[Any, datetime]] = {}

    def _make_key(self, endpoint: str, params: dict[str, Any]) -> str:
        """Generate a cache key from endpoint and parameters.

        Args:
            endpoint: The API endpoint
            params: Query parameters

        Returns:
            Cache key string
        """
        # Sort params for consistent key generation
        sorted_params = json.dumps(params, sort_keys=True)
        key_data = f"{endpoint}:{sorted_params}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _get_ttl(self, endpoint: str) -> int:
        """Get TTL for an endpoint.

        Args:
            endpoint: The endpoint type

        Returns:
            TTL in seconds
        """
        ttl_map = {
            "site_list": self._settings.cache_ttl_site_list,
            "site_detail": self._settings.cache_ttl_site_detail,
            "scene_search": self._settings.cache_ttl_scene_search,
            "scene_detail": self._settings.cache_ttl_scene_detail,
            "movie_detail": self._settings.cache_ttl_movie_detail,
        }
        return ttl_map.get(endpoint, 300)  # Default 5 minutes

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any],
    ) -> Optional[Any]:
        """Get a value from cache.

        Args:
            endpoint: The endpoint type
            params: Query parameters

        Returns:
            Cached value or None
        """
        cache_key = self._make_key(endpoint, params)

        # Check memory cache first
        if cache_key in self._memory_cache:
            value, expires_at = self._memory_cache[cache_key]
            if datetime.now(timezone.utc) < expires_at:
                logger.debug("Memory cache hit", key=cache_key, endpoint=endpoint)
                return value
            else:
                del self._memory_cache[cache_key]

        # Check database cache
        async with async_session_maker() as session:
            result = await session.execute(
                select(CacheEntry).where(CacheEntry.cache_key == cache_key)
            )
            entry = result.scalar_one_or_none()

            if entry and not entry.is_expired:
                logger.debug("Database cache hit", key=cache_key, endpoint=endpoint)
                # Update hit count
                entry.hit_count += 1
                await session.commit()

                # Store in memory cache for faster subsequent access
                ttl = self._get_ttl(endpoint)
                self._memory_cache[cache_key] = (
                    entry.response_data,
                    datetime.now(timezone.utc) + timedelta(seconds=min(ttl, 300)),
                )
                return entry.response_data

        logger.debug("Cache miss", key=cache_key, endpoint=endpoint)
        return None

    async def set(
        self,
        endpoint: str,
        params: dict[str, Any],
        value: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """Set a value in cache.

        Args:
            endpoint: The endpoint type
            params: Query parameters
            value: Value to cache
            ttl: Optional TTL override in seconds
        """
        cache_key = self._make_key(endpoint, params)
        ttl = ttl or self._get_ttl(endpoint)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

        # Store in memory cache (shorter TTL for memory)
        memory_ttl = min(ttl, 300)
        self._memory_cache[cache_key] = (
            value,
            datetime.now(timezone.utc) + timedelta(seconds=memory_ttl),
        )

        # Store in database cache
        async with async_session_maker() as session:
            # Try to update existing entry
            result = await session.execute(
                select(CacheEntry).where(CacheEntry.cache_key == cache_key)
            )
            entry = result.scalar_one_or_none()

            if entry:
                entry.response_data = value
                entry.expires_at = expires_at
                entry.hit_count = 0
            else:
                entry = CacheEntry(
                    cache_key=cache_key,
                    endpoint=endpoint,
                    response_data=value,
                    expires_at=expires_at,
                )
                session.add(entry)

            await session.commit()
            logger.debug("Cache set", key=cache_key, endpoint=endpoint, ttl=ttl)

    async def get_or_fetch(
        self,
        endpoint: str,
        params: dict[str, Any],
        fetch_func: Callable[[], Any],
        ttl: Optional[int] = None,
    ) -> Any:
        """Get from cache or fetch and cache.

        Args:
            endpoint: The endpoint type
            params: Query parameters
            fetch_func: Async function to fetch data if not cached
            ttl: Optional TTL override

        Returns:
            Cached or fetched value
        """
        # Try cache first
        cached = await self.get(endpoint, params)
        if cached is not None:
            return cached

        # Fetch and cache
        value = await fetch_func()
        await self.set(endpoint, params, value, ttl)
        return value

    async def clear(self, endpoint: Optional[str] = None) -> int:
        """Clear cache entries.

        Args:
            endpoint: Optional endpoint to clear (clears all if None)

        Returns:
            Number of entries cleared
        """
        # Clear memory cache
        if endpoint:
            keys_to_delete = [
                k for k in self._memory_cache if endpoint in k
            ]
            for k in keys_to_delete:
                del self._memory_cache[k]
        else:
            self._memory_cache.clear()

        # Clear database cache
        async with async_session_maker() as session:
            if endpoint:
                result = await session.execute(
                    delete(CacheEntry).where(CacheEntry.endpoint == endpoint)
                )
            else:
                result = await session.execute(delete(CacheEntry))

            await session.commit()
            count = result.rowcount or 0
            logger.info("Cache cleared", endpoint=endpoint, count=count)
            return count

    async def clear_expired(self) -> int:
        """Clear expired cache entries.

        Returns:
            Number of entries cleared
        """
        # Clear expired from memory
        now = datetime.now(timezone.utc)
        expired_keys = [
            k for k, (_, exp) in self._memory_cache.items() if exp < now
        ]
        for k in expired_keys:
            del self._memory_cache[k]

        # Clear expired from database
        async with async_session_maker() as session:
            result = await session.execute(
                delete(CacheEntry).where(CacheEntry.expires_at < now)
            )
            await session.commit()
            count = result.rowcount or 0
            logger.info("Expired cache cleared", count=count)
            return count

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        async with async_session_maker() as session:
            # Count total entries
            result = await session.execute(select(CacheEntry))
            entries = result.scalars().all()

            total = len(entries)
            expired = sum(1 for e in entries if e.is_expired)
            total_hits = sum(e.hit_count for e in entries)

            # Group by endpoint
            by_endpoint: dict[str, int] = {}
            for e in entries:
                by_endpoint[e.endpoint] = by_endpoint.get(e.endpoint, 0) + 1

            return {
                "total_entries": total,
                "active_entries": total - expired,
                "expired_entries": expired,
                "total_hits": total_hits,
                "memory_entries": len(self._memory_cache),
                "by_endpoint": by_endpoint,
            }


# Singleton instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get the cache service singleton."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
