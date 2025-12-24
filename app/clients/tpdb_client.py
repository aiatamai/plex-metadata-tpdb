"""ThePornDB API client."""

from typing import Any, Optional

import aiohttp
import structlog

from app.clients.rate_limiter import RateLimiter
from app.config import Settings, get_settings

logger = structlog.get_logger(__name__)


class TPDBError(Exception):
    """Base exception for TPDB API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class TPDBNotFoundError(TPDBError):
    """Resource not found on TPDB."""

    pass


class TPDBRateLimitError(TPDBError):
    """Rate limit exceeded on TPDB."""

    pass


class TPDBClient:
    """Async client for ThePornDB API.

    This client handles authentication, rate limiting, and provides
    methods for accessing TPDB API endpoints.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        """Initialize the TPDB client.

        Args:
            settings: Application settings (uses default if not provided)
            session: Optional aiohttp session to reuse
        """
        self._settings = settings or get_settings()
        self._session = session
        self._owns_session = session is None
        self._rate_limiter = RateLimiter(
            requests_per_second=self._settings.tpdb_rate_limit,
            burst_size=5,
        )

    @property
    def base_url(self) -> str:
        """Get the TPDB API base URL."""
        return self._settings.tpdb_base_url

    @property
    def _headers(self) -> dict[str, str]:
        """Get default headers for API requests."""
        return {
            "Authorization": f"Bearer {self._settings.tpdb_api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self._headers)
            self._owns_session = True
        return self._session

    async def close(self) -> None:
        """Close the client session if we own it."""
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Make a rate-limited request to the TPDB API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json: JSON body for POST requests

        Returns:
            Response data as dictionary

        Raises:
            TPDBError: For API errors
            TPDBNotFoundError: When resource is not found
            TPDBRateLimitError: When rate limit is exceeded
        """
        # Acquire rate limit token
        await self._rate_limiter.acquire()

        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"

        logger.debug("TPDB API request", method=method, url=url, params=params)

        try:
            async with session.request(
                method, url, params=params, json=json
            ) as response:
                if response.status == 404:
                    raise TPDBNotFoundError(
                        f"Resource not found: {endpoint}",
                        status_code=404,
                    )
                elif response.status == 429:
                    raise TPDBRateLimitError(
                        "TPDB rate limit exceeded",
                        status_code=429,
                    )
                elif response.status >= 400:
                    text = await response.text()
                    raise TPDBError(
                        f"TPDB API error: {text}",
                        status_code=response.status,
                    )

                data = await response.json()
                return data

        except aiohttp.ClientError as e:
            logger.error("TPDB request failed", error=str(e), url=url)
            raise TPDBError(f"Request failed: {str(e)}")

    # Scene endpoints
    async def search_scenes(
        self,
        q: Optional[str] = None,
        site: Optional[str] = None,
        performer: Optional[str] = None,
        date: Optional[str] = None,
        page: int = 1,
        per_page: int = 25,
    ) -> dict[str, Any]:
        """Search for scenes.

        Args:
            q: Search query (title, performer, etc.)
            site: Filter by site slug
            performer: Filter by performer name
            date: Filter by date (YYYY-MM-DD)
            page: Page number
            per_page: Results per page

        Returns:
            TPDB search response
        """
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if q:
            params["q"] = q
        if site:
            params["site"] = site
        if performer:
            params["performers"] = performer
        if date:
            params["date"] = date

        return await self._request("GET", "/scenes", params=params)

    async def get_scene(self, scene_id: str) -> dict[str, Any]:
        """Get a scene by ID or slug.

        Args:
            scene_id: Scene UUID or slug

        Returns:
            Scene data
        """
        return await self._request("GET", f"/scenes/{scene_id}")

    async def get_scene_by_hash(
        self, hash_value: str, hash_type: str = "OSHASH"
    ) -> Optional[dict[str, Any]]:
        """Find a scene by content hash.

        Args:
            hash_value: The hash value
            hash_type: Hash type (OSHASH or PHASH)

        Returns:
            Scene data or None if not found
        """
        try:
            return await self._request("GET", f"/scenes/hash/{hash_value}")
        except TPDBNotFoundError:
            return None

    # Site endpoints
    async def search_sites(
        self,
        q: Optional[str] = None,
        page: int = 1,
        per_page: int = 25,
    ) -> dict[str, Any]:
        """Search for sites/studios.

        Args:
            q: Search query
            page: Page number
            per_page: Results per page

        Returns:
            TPDB search response
        """
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if q:
            params["q"] = q

        return await self._request("GET", "/sites", params=params)

    async def get_site(self, site_id: str) -> dict[str, Any]:
        """Get a site by ID or slug.

        Args:
            site_id: Site UUID or slug

        Returns:
            Site data
        """
        return await self._request("GET", f"/sites/{site_id}")

    async def get_site_scenes(
        self,
        site_id: str,
        page: int = 1,
        per_page: int = 25,
        year: Optional[int] = None,
    ) -> dict[str, Any]:
        """Get scenes for a site.

        Args:
            site_id: Site UUID or slug
            page: Page number
            per_page: Results per page
            year: Filter by year

        Returns:
            TPDB scenes response
        """
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if year:
            params["date"] = f"{year}"

        return await self._request("GET", f"/sites/{site_id}/scenes", params=params)

    # Movie endpoints
    async def search_movies(
        self,
        q: Optional[str] = None,
        year: Optional[int] = None,
        page: int = 1,
        per_page: int = 25,
    ) -> dict[str, Any]:
        """Search for movies.

        Args:
            q: Search query
            year: Filter by year
            page: Page number
            per_page: Results per page

        Returns:
            TPDB search response
        """
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if q:
            params["q"] = q
        if year:
            params["year"] = year

        return await self._request("GET", "/movies", params=params)

    async def get_movie(self, movie_id: str) -> dict[str, Any]:
        """Get a movie by ID or slug.

        Args:
            movie_id: Movie UUID or slug

        Returns:
            Movie data
        """
        return await self._request("GET", f"/movies/{movie_id}")

    # Performer endpoints
    async def search_performers(
        self,
        q: Optional[str] = None,
        page: int = 1,
        per_page: int = 25,
    ) -> dict[str, Any]:
        """Search for performers.

        Args:
            q: Search query
            page: Page number
            per_page: Results per page

        Returns:
            TPDB search response
        """
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if q:
            params["q"] = q

        return await self._request("GET", "/performers", params=params)

    async def get_performer(self, performer_id: str) -> dict[str, Any]:
        """Get a performer by ID or slug.

        Args:
            performer_id: Performer UUID or slug

        Returns:
            Performer data
        """
        return await self._request("GET", f"/performers/{performer_id}")


# Singleton instance
_client: Optional[TPDBClient] = None


async def get_tpdb_client() -> TPDBClient:
    """Get the TPDB client singleton."""
    global _client
    if _client is None:
        _client = TPDBClient()
    return _client
