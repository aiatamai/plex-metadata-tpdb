"""Movie Provider routes for Plex MediaProvider.

Handles:
- GET /movie - Returns MediaProvider definition
- POST /movie/library/metadata/matches - Match movies
- GET /movie/library/metadata/{ratingKey} - Get movie metadata
"""

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.constants import MOVIE_PROVIDER_IDENTIFIER, MetadataType
from app.models.plex import (
    MatchRequest,
    MediaContainer,
    MediaContainerResponse,
    MediaProviderResponse,
)
from app.providers.movie_provider import get_movie_provider_response
from app.services.match_service import MatchService, get_match_service
from app.services.metadata_service import MetadataService, get_metadata_service

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("", response_model=MediaProviderResponse)
async def get_provider() -> MediaProviderResponse:
    """Return the Movie MediaProvider definition.

    This endpoint is called by Plex to discover the provider's capabilities.
    """
    logger.info("Movie provider definition requested")
    return get_movie_provider_response()


@router.post("/library/metadata/matches", response_model=MediaContainerResponse)
async def match_content(
    request: Request,
    x_plex_language: Optional[str] = Header(None, alias="X-Plex-Language"),
    x_plex_country: Optional[str] = Header(None, alias="X-Plex-Country"),
    match_service: MatchService = Depends(get_match_service),
) -> MediaContainerResponse:
    """Match movies against ThePornDB.

    Args:
        request: The incoming request containing match parameters
        x_plex_language: Preferred language from Plex
        x_plex_country: Country code from Plex
        match_service: Injected match service
    """
    # Parse the request body with error handling
    try:
        body = await request.json()
    except ValueError as e:
        logger.error("Invalid JSON in movie match request", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON in request body",
        )

    # Validate request structure
    if not isinstance(body, dict):
        logger.error("Movie match request body is not a dictionary", body_type=type(body).__name__)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body must be a JSON object",
        )

    try:
        match_request = MatchRequest(**body)
    except (ValueError, TypeError) as e:
        logger.error("Invalid movie match request parameters", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request parameters: {str(e)}",
        )

    logger.info(
        "Movie match request received",
        title=match_request.title,
        year=match_request.year,
        language=x_plex_language,
    )

    if match_request.type == MetadataType.MOVIE:
        container = await match_service.match_movie(
            match_request, language=x_plex_language or "en"
        )
    else:
        # Return empty container for unsupported types
        container = MediaContainer(
            offset=0,
            totalSize=0,
            identifier=MOVIE_PROVIDER_IDENTIFIER,
            size=0,
            Metadata=[],
        )

    return MediaContainerResponse(MediaContainer=container)


@router.get("/library/metadata/{rating_key}", response_model=MediaContainerResponse)
async def get_metadata(
    rating_key: str,
    x_plex_language: Optional[str] = Header(None, alias="X-Plex-Language"),
    x_plex_country: Optional[str] = Header(None, alias="X-Plex-Country"),
    metadata_service: MetadataService = Depends(get_metadata_service),
) -> MediaContainerResponse:
    """Get metadata for a specific movie.

    Args:
        rating_key: The rating key identifying the movie (e.g., "tpdb-movie-uuid")
        x_plex_language: Preferred language from Plex
        x_plex_country: Country code from Plex
        metadata_service: Injected metadata service
    """
    logger.info("Movie metadata request", rating_key=rating_key, language=x_plex_language)

    container = await metadata_service.get_metadata(
        rating_key=rating_key,
        provider_identifier=MOVIE_PROVIDER_IDENTIFIER,
        language=x_plex_language or "en",
    )

    return MediaContainerResponse(MediaContainer=container)
