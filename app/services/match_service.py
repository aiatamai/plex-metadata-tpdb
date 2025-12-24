"""Match service for finding metadata matches."""

from typing import Any, Optional

import structlog

from app.clients.tpdb_client import TPDBClient, get_tpdb_client
from app.constants import MOVIE_PROVIDER_IDENTIFIER, TV_PROVIDER_IDENTIFIER
from app.mappers.movie_mapper import MovieMapper
from app.mappers.show_mapper import ShowMapper
from app.models.plex import MatchRequest, MediaContainer, MetadataItem
from app.services.cache_service import CacheService, get_cache_service

logger = structlog.get_logger(__name__)


class MatchService:
    """Service for matching content against TPDB."""

    def __init__(
        self,
        tpdb_client: Optional[TPDBClient] = None,
        cache_service: Optional[CacheService] = None,
    ) -> None:
        """Initialize the match service.

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

    async def match_show(
        self,
        request: MatchRequest,
        language: str = "en",
    ) -> MediaContainer:
        """Match a show (site) against TPDB.

        Args:
            request: Match request from Plex
            language: Preferred language

        Returns:
            MediaContainer with matching shows
        """
        logger.info("Matching show", title=request.title, year=request.year)

        metadata: list[MetadataItem] = []
        client = await self._get_client()

        # Check for external GUID first (e.g., "tpdb://site-id")
        if request.guid and request.guid.startswith("tpdb://"):
            site_id = request.guid.replace("tpdb://", "")
            try:
                response = await client.get_site(site_id)
                site_data = response.get("data", {})
                if site_data:
                    metadata.append(ShowMapper.site_to_show(site_data))
            except Exception as e:
                logger.warning("Failed to fetch site by GUID", guid=request.guid, error=str(e))

        # Search by title if no GUID match
        if not metadata and request.title:
            response = await client.search_sites(q=request.title, per_page=10)
            for site_data in response.get("data", []):
                metadata.append(ShowMapper.site_to_show(site_data))

        return MediaContainer(
            offset=0,
            totalSize=len(metadata),
            identifier=TV_PROVIDER_IDENTIFIER,
            size=len(metadata),
            Metadata=metadata,
        )

    async def match_season(
        self,
        request: MatchRequest,
        language: str = "en",
    ) -> MediaContainer:
        """Match a season against TPDB.

        Seasons in our mapping are year-based groupings.

        Args:
            request: Match request from Plex
            language: Preferred language

        Returns:
            MediaContainer with matching seasons
        """
        logger.info(
            "Matching season",
            grandparent=request.grandparentTitle,
            index=request.parentIndex,
        )

        metadata: list[MetadataItem] = []

        # Get the show (site) first
        if request.grandparentTitle:
            client = await self._get_client()
            response = await client.search_sites(q=request.grandparentTitle, per_page=1)
            sites = response.get("data", [])

            if sites:
                site_data = sites[0]
                site_slug = site_data.get("slug") or site_data.get("id")
                site_name = site_data.get("name", "Unknown")
                site_thumb = site_data.get("logo")

                # Use the parent index as the year
                year = request.parentIndex or 2024
                metadata.append(
                    ShowMapper.create_season(site_slug, site_name, year, site_thumb)
                )

        return MediaContainer(
            offset=0,
            totalSize=len(metadata),
            identifier=TV_PROVIDER_IDENTIFIER,
            size=len(metadata),
            Metadata=metadata,
        )

    async def match_episode(
        self,
        request: MatchRequest,
        language: str = "en",
    ) -> MediaContainer:
        """Match an episode (scene) against TPDB.

        Args:
            request: Match request from Plex
            language: Preferred language

        Returns:
            MediaContainer with matching episodes
        """
        logger.info(
            "Matching episode",
            title=request.title,
            grandparent=request.grandparentTitle,
            date=request.date,
        )

        metadata: list[MetadataItem] = []
        client = await self._get_client()

        # Search by title and optionally filter by site
        search_params: dict[str, Any] = {"per_page": 10}

        if request.title:
            search_params["q"] = request.title

        if request.grandparentTitle:
            # Try to find the site first
            site_response = await client.search_sites(q=request.grandparentTitle, per_page=1)
            sites = site_response.get("data", [])
            if sites:
                search_params["site"] = sites[0].get("slug") or sites[0].get("id")

        if request.date:
            search_params["date"] = request.date

        # Search for scenes
        response = await client.search_scenes(**search_params)
        for idx, scene_data in enumerate(response.get("data", []), start=1):
            metadata.append(ShowMapper.scene_to_episode(scene_data, episode_index=idx))

        return MediaContainer(
            offset=0,
            totalSize=len(metadata),
            identifier=TV_PROVIDER_IDENTIFIER,
            size=len(metadata),
            Metadata=metadata,
        )

    async def match_movie(
        self,
        request: MatchRequest,
        language: str = "en",
    ) -> MediaContainer:
        """Match a movie against TPDB.

        Args:
            request: Match request from Plex
            language: Preferred language

        Returns:
            MediaContainer with matching movies
        """
        logger.info("Matching movie", title=request.title, year=request.year)

        metadata: list[MetadataItem] = []
        client = await self._get_client()

        # Check for external GUID first
        if request.guid and request.guid.startswith("tpdb://"):
            movie_id = request.guid.replace("tpdb://", "")
            try:
                response = await client.get_movie(movie_id)
                movie_data = response.get("data", {})
                if movie_data:
                    metadata.append(MovieMapper.movie_to_plex(movie_data))
            except Exception as e:
                logger.warning("Failed to fetch movie by GUID", guid=request.guid, error=str(e))

        # Search by title if no GUID match
        if not metadata and request.title:
            response = await client.search_movies(
                q=request.title,
                year=request.year,
                per_page=10,
            )
            for movie_data in response.get("data", []):
                metadata.append(MovieMapper.movie_to_plex(movie_data))

        return MediaContainer(
            offset=0,
            totalSize=len(metadata),
            identifier=MOVIE_PROVIDER_IDENTIFIER,
            size=len(metadata),
            Metadata=metadata,
        )


# Singleton instance
_match_service: Optional[MatchService] = None


async def get_match_service() -> MatchService:
    """Get the match service singleton."""
    global _match_service
    if _match_service is None:
        _match_service = MatchService()
    return _match_service
