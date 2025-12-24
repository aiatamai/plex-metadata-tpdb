"""Metadata service for retrieving and formatting metadata."""

from typing import Any, Optional

import structlog

from app.clients.tpdb_client import TPDBClient, TPDBNotFoundError, get_tpdb_client
from app.config import get_settings
from app.constants import MOVIE_PROVIDER_IDENTIFIER, TV_PROVIDER_IDENTIFIER
from app.mappers.movie_mapper import MovieMapper
from app.mappers.show_mapper import ShowMapper
from app.models.plex import MediaContainer, MetadataItem
from app.services.cache_service import CacheService, get_cache_service

logger = structlog.get_logger(__name__)


class MetadataService:
    """Service for retrieving metadata from TPDB and formatting for Plex."""

    def __init__(
        self,
        tpdb_client: Optional[TPDBClient] = None,
        cache_service: Optional[CacheService] = None,
    ) -> None:
        """Initialize the metadata service.

        Args:
            tpdb_client: TPDB API client
            cache_service: Cache service
        """
        self._tpdb_client = tpdb_client
        self._cache_service = cache_service

    async def _get_client(self) -> TPDBClient:
        """Get the TPDB client."""
        if self._tpdb_client is None:
            self._tpdb_client = await get_tpdb_client()
        return self._tpdb_client

    def _get_cache(self) -> CacheService:
        """Get the cache service."""
        if self._cache_service is None:
            self._cache_service = get_cache_service()
        return self._cache_service

    async def get_metadata(
        self,
        rating_key: str,
        provider_identifier: str,
        language: str = "en",
    ) -> MediaContainer:
        """Get metadata for an item.

        Args:
            rating_key: The rating key identifying the item
            provider_identifier: The provider identifier
            language: Preferred language

        Returns:
            MediaContainer with the metadata
        """
        logger.debug("Getting metadata", rating_key=rating_key, provider=provider_identifier)

        metadata: list[MetadataItem] = []

        if provider_identifier == TV_PROVIDER_IDENTIFIER:
            # Parse the rating key
            parsed = ShowMapper.parse_rating_key(rating_key)

            if parsed["type"] == "site":
                # Get site/show metadata
                site_data = await self._get_site(parsed["site_slug"])
                if site_data:
                    metadata.append(ShowMapper.site_to_show(site_data))

            elif parsed["type"] == "season":
                # Get season metadata (virtual - just year grouping)
                site_slug = parsed.get("site_slug", "")
                year = parsed.get("year", 2024)
                site_data = await self._get_site(site_slug)
                site_name = site_data.get("name", "Unknown") if site_data else "Unknown"
                site_thumb = site_data.get("logo") if site_data else None
                metadata.append(
                    ShowMapper.create_season(site_slug, site_name, year, site_thumb)
                )

            elif parsed["type"] == "scene":
                # Get scene/episode metadata
                scene_data = await self._get_scene(parsed["scene_id"])
                if scene_data:
                    metadata.append(ShowMapper.scene_to_episode(scene_data))

        elif provider_identifier == MOVIE_PROVIDER_IDENTIFIER:
            # Parse the rating key
            parsed = MovieMapper.parse_rating_key(rating_key)

            if parsed["type"] == "movie":
                movie_data = await self._get_movie(parsed["movie_id"])
                if movie_data:
                    metadata.append(MovieMapper.movie_to_plex(movie_data))

        return MediaContainer(
            offset=0,
            totalSize=len(metadata),
            identifier=provider_identifier,
            size=len(metadata),
            Metadata=metadata,
        )

    async def get_children(
        self,
        rating_key: str,
        provider_identifier: str,
        language: str = "en",
        offset: int = 0,
        limit: int = 50,
    ) -> MediaContainer:
        """Get children (seasons or episodes) for an item.

        Args:
            rating_key: The rating key of the parent item
            provider_identifier: The provider identifier
            language: Preferred language
            offset: Pagination offset
            limit: Number of items to return

        Returns:
            MediaContainer with the children
        """
        logger.debug(
            "Getting children",
            rating_key=rating_key,
            provider=provider_identifier,
            offset=offset,
            limit=limit,
        )

        metadata: list[MetadataItem] = []
        total_size = 0

        if provider_identifier == TV_PROVIDER_IDENTIFIER:
            parsed = ShowMapper.parse_rating_key(rating_key)

            if parsed["type"] == "site":
                # Get seasons (years) for a show
                site_slug = parsed["site_slug"]
                site_data = await self._get_site(site_slug)
                if site_data:
                    # Get all scenes to determine available years
                    years = await self._get_site_years(site_slug)
                    site_name = site_data.get("name", "Unknown")
                    site_thumb = site_data.get("logo")

                    # Create season entries for each year
                    for year in sorted(years, reverse=True)[offset : offset + limit]:
                        metadata.append(
                            ShowMapper.create_season(site_slug, site_name, year, site_thumb)
                        )
                    total_size = len(years)

            elif parsed["type"] == "season":
                # Get episodes for a season (scenes for a year)
                site_slug = parsed.get("site_slug", "")
                year = parsed.get("year", 2024)
                site_data = await self._get_site(site_slug)

                scenes = await self._get_site_scenes_by_year(site_slug, year, offset, limit)
                total_size = scenes.get("total", 0)

                for idx, scene_data in enumerate(scenes.get("data", []), start=offset + 1):
                    metadata.append(
                        ShowMapper.scene_to_episode(scene_data, site_data, episode_index=idx)
                    )

        return MediaContainer(
            offset=offset,
            totalSize=total_size,
            identifier=provider_identifier,
            size=len(metadata),
            Metadata=metadata,
        )

    async def _get_site(self, site_slug: str) -> Optional[dict[str, Any]]:
        """Get site data with caching."""
        cache = self._get_cache()
        client = await self._get_client()

        async def fetch() -> dict[str, Any]:
            response = await client.get_site(site_slug)
            return response.get("data", {})

        try:
            return await cache.get_or_fetch(
                "site_detail",
                {"site_slug": site_slug},
                fetch,
            )
        except TPDBNotFoundError:
            return None

    async def _get_scene(self, scene_id: str) -> Optional[dict[str, Any]]:
        """Get scene data with caching."""
        cache = self._get_cache()
        client = await self._get_client()

        async def fetch() -> dict[str, Any]:
            response = await client.get_scene(scene_id)
            return response.get("data", {})

        try:
            return await cache.get_or_fetch(
                "scene_detail",
                {"scene_id": scene_id},
                fetch,
            )
        except TPDBNotFoundError:
            return None

    async def _get_movie(self, movie_id: str) -> Optional[dict[str, Any]]:
        """Get movie data with caching."""
        cache = self._get_cache()
        client = await self._get_client()

        async def fetch() -> dict[str, Any]:
            response = await client.get_movie(movie_id)
            return response.get("data", {})

        try:
            return await cache.get_or_fetch(
                "movie_detail",
                {"movie_id": movie_id},
                fetch,
            )
        except TPDBNotFoundError:
            return None

    async def _get_site_years(self, site_slug: str) -> list[int]:
        """Get available years for a site by paginating through scenes."""
        cache = self._get_cache()
        client = await self._get_client()
        settings = get_settings()

        async def fetch() -> list[int]:
            years = set()
            page = 1
            max_pages = settings.tpdb_max_pages_for_years

            logger.debug(
                "Fetching site years",
                site_slug=site_slug,
                max_pages=max_pages if max_pages > 0 else "unlimited",
            )

            while True:
                # Fetch scenes page by page
                response = await client.get_site_scenes(site_slug, page=page, per_page=100)
                scenes = response.get("data", [])

                # Extract years from scenes
                for scene in scenes:
                    date_str = scene.get("date")
                    if date_str and len(date_str) >= 4:
                        year_str = date_str[:4]
                        if year_str.isdigit():
                            years.add(int(year_str))

                # Check if we should continue paginating
                # Stop if: no more scenes, reached max pages, or no pagination info
                if not scenes:
                    break

                # Check pagination metadata (if available)
                meta = response.get("meta", {})
                current_page = meta.get("current_page", page)
                last_page = meta.get("last_page")

                logger.debug(
                    "Fetched page",
                    page=current_page,
                    scenes_count=len(scenes),
                    years_found=len(years),
                    last_page=last_page,
                )

                # Stop if we've reached the last page
                if last_page and current_page >= last_page:
                    break

                # Stop if we've reached max_pages limit (0 = unlimited)
                if max_pages > 0 and page >= max_pages:
                    logger.debug(
                        "Reached max pages limit",
                        max_pages=max_pages,
                        years_found=len(years),
                    )
                    break

                page += 1

            result = sorted(years, reverse=True) if years else [2024]
            logger.info(
                "Site years fetched",
                site_slug=site_slug,
                years_count=len(result),
                pages_fetched=page,
            )
            return result

        return await cache.get_or_fetch(
            "site_years",
            {"site_slug": site_slug},
            fetch,
            ttl=3600,  # 1 hour
        )

    async def _get_site_scenes_by_year(
        self,
        site_slug: str,
        year: int,
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Get scenes for a site filtered by year."""
        client = await self._get_client()

        # Calculate page from offset
        page = (offset // limit) + 1

        response = await client.get_site_scenes(
            site_slug,
            page=page,
            per_page=limit,
            year=year,
        )

        return {
            "data": response.get("data", []),
            "total": response.get("meta", {}).get("total", 0),
        }


# Singleton instance
_metadata_service: Optional[MetadataService] = None


async def get_metadata_service() -> MetadataService:
    """Get the metadata service singleton."""
    global _metadata_service
    if _metadata_service is None:
        _metadata_service = MetadataService()
    return _metadata_service
