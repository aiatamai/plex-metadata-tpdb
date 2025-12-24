"""TV Provider routes for Plex MediaProvider.

Handles:
- GET /tv - Returns MediaProvider definition
- POST /tv/library/metadata/matches - Match shows/seasons/episodes
- GET /tv/library/metadata/{ratingKey} - Get metadata for item
- GET /tv/library/metadata/{ratingKey}/children - Get seasons/episodes
"""

from typing import Any, Optional

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

from app.constants import TV_PROVIDER_IDENTIFIER, MetadataType
from app.models.plex import (
    MatchRequest,
    MediaContainer,
    MediaContainerResponse,
    MediaProviderResponse,
)
from app.providers.tv_provider import get_tv_provider_response
from app.services.match_service import MatchService, get_match_service
from app.services.metadata_service import MetadataService, get_metadata_service

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("", response_model=MediaProviderResponse)
async def get_provider() -> MediaProviderResponse:
    """Return the TV MediaProvider definition.

    This endpoint is called by Plex to discover the provider's capabilities.
    """
    logger.info("TV provider definition requested")
    return get_tv_provider_response()


@router.post("/library/metadata/matches", response_model=MediaContainerResponse)
async def match_content(
    request: Request,
    x_plex_language: Optional[str] = Header(None, alias="X-Plex-Language"),
    x_plex_country: Optional[str] = Header(None, alias="X-Plex-Country"),
    match_service: MatchService = Depends(get_match_service),
) -> MediaContainerResponse:
    """Match shows, seasons, or episodes against ThePornDB.

    This endpoint is called by Plex when the user initiates a metadata match.

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
        logger.error("Invalid JSON in match request", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON in request body",
        )

    # Validate request structure
    if not isinstance(body, dict):
        logger.error("Match request body is not a dictionary", body_type=type(body).__name__)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body must be a JSON object",
        )

    try:
        match_request = MatchRequest(**body)
    except (ValueError, TypeError) as e:
        logger.error("Invalid match request parameters", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request parameters: {str(e)}",
        )

    logger.info(
        "Match request received",
        type=match_request.type,
        title=match_request.title,
        language=x_plex_language,
    )

    # Route to appropriate handler based on type
    if match_request.type == MetadataType.SHOW:
        container = await match_service.match_show(
            match_request, language=x_plex_language or "en"
        )
    elif match_request.type == MetadataType.SEASON:
        container = await match_service.match_season(
            match_request, language=x_plex_language or "en"
        )
    elif match_request.type == MetadataType.EPISODE:
        container = await match_service.match_episode(
            match_request, language=x_plex_language or "en"
        )
    else:
        # Return empty container for unsupported types
        container = MediaContainer(
            offset=0,
            totalSize=0,
            identifier=TV_PROVIDER_IDENTIFIER,
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
    """Get metadata for a specific item.

    Args:
        rating_key: The rating key identifying the item (e.g., "tpdb-site-brazzers")
        x_plex_language: Preferred language from Plex
        x_plex_country: Country code from Plex
        metadata_service: Injected metadata service
    """
    logger.info("Metadata request", rating_key=rating_key, language=x_plex_language)

    container = await metadata_service.get_metadata(
        rating_key=rating_key,
        provider_identifier=TV_PROVIDER_IDENTIFIER,
        language=x_plex_language or "en",
    )

    return MediaContainerResponse(MediaContainer=container)


@router.get("/library/metadata/{rating_key}/children", response_model=MediaContainerResponse)
async def get_children(
    rating_key: str,
    x_plex_language: Optional[str] = Header(None, alias="X-Plex-Language"),
    x_plex_country: Optional[str] = Header(None, alias="X-Plex-Country"),
    containerStart: int = Query(0, alias="X-Plex-Container-Start"),
    containerSize: int = Query(50, alias="X-Plex-Container-Size"),
    metadata_service: MetadataService = Depends(get_metadata_service),
) -> MediaContainerResponse:
    """Get children (seasons or episodes) for an item.

    Args:
        rating_key: The rating key of the parent item
        x_plex_language: Preferred language from Plex
        x_plex_country: Country code from Plex
        containerStart: Pagination offset
        containerSize: Number of items to return
        metadata_service: Injected metadata service
    """
    logger.info(
        "Children request",
        rating_key=rating_key,
        start=containerStart,
        size=containerSize,
    )

    container = await metadata_service.get_children(
        rating_key=rating_key,
        provider_identifier=TV_PROVIDER_IDENTIFIER,
        language=x_plex_language or "en",
        offset=containerStart,
        limit=containerSize,
    )

    return MediaContainerResponse(MediaContainer=container)
