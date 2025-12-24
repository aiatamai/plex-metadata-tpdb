"""Admin Web UI routes."""

import secrets
from typing import Annotated, Any, Optional

import structlog
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from app.clients.tpdb_client import TPDBError, TPDBNotFoundError, get_tpdb_client
from app.config import get_settings
from app.services.cache_service import get_cache_service

logger = structlog.get_logger(__name__)

router = APIRouter()
security = HTTPBasic()
templates = Jinja2Templates(directory="app/web/templates")


def verify_credentials(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)]
) -> str:
    """Verify HTTP Basic credentials.

    Args:
        credentials: HTTP Basic credentials

    Returns:
        Username if valid

    Raises:
        HTTPException: If credentials are invalid
    """
    settings = get_settings()
    is_valid_username = secrets.compare_digest(
        credentials.username.encode("utf8"),
        settings.admin_username.encode("utf8"),
    )
    is_valid_password = secrets.compare_digest(
        credentials.password.encode("utf8"),
        settings.admin_password.encode("utf8"),
    )

    if not (is_valid_username and is_valid_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


@router.get("", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    username: str = Depends(verify_credentials),
) -> HTMLResponse:
    """Dashboard page."""
    cache_service = get_cache_service()
    cache_stats = await cache_service.get_stats()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "username": username,
            "cache_stats": cache_stats,
            "settings": get_settings(),
        },
    )


@router.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    username: str = Depends(verify_credentials),
) -> HTMLResponse:
    """Search page."""
    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "username": username,
        },
    )


@router.get("/api/search")
async def search_tpdb(
    q: str = Query(..., min_length=1, max_length=255, description="Search query"),
    type: str = Query("scenes", description="Search type: scenes, sites, movies, or performers"),
    username: str = Depends(verify_credentials),
) -> JSONResponse:
    """Search TPDB directly.

    This endpoint searches ThePornDB for content matching the query.
    Results are returned in a standardized format for the UI.

    Args:
        q: Search query string
        type: Search type (scenes, sites, movies, performers)
        username: Authenticated username

    Returns:
        JSON response with search results

    Raises:
        HTTPException: If search type is invalid or API error occurs
    """
    # Validate search type
    valid_types = {"scenes", "sites", "movies", "performers"}
    if type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid search type. Must be one of: {', '.join(valid_types)}",
        )

    try:
        client = await get_tpdb_client()
        logger.info("TPDB search", query=q, search_type=type, username=username)

        # Call appropriate search method based on type
        if type == "scenes":
            response = await client.search_scenes(q=q, per_page=25)
            data = response.get("data", [])
            # Flatten scene data for UI display
            results = [
                {
                    "id": scene.get("id"),
                    "title": scene.get("title"),
                    "date": scene.get("date"),
                    "description": scene.get("description"),
                    "image": scene.get("image"),
                    "poster": scene.get("poster"),
                    "site": scene.get("site"),
                    "performers": scene.get("performers", []),
                    "type": "scene",
                }
                for scene in data
            ]

        elif type == "sites":
            response = await client.search_sites(q=q, per_page=25)
            data = response.get("data", [])
            # Flatten site data for UI display
            results = [
                {
                    "id": site.get("id"),
                    "name": site.get("name"),
                    "slug": site.get("slug"),
                    "description": site.get("description"),
                    "logo": site.get("logo"),
                    "poster": site.get("poster"),
                    "type": "site",
                }
                for site in data
            ]

        elif type == "movies":
            response = await client.search_movies(q=q, per_page=25)
            data = response.get("data", [])
            # Flatten movie data for UI display
            results = [
                {
                    "id": movie.get("id"),
                    "title": movie.get("title"),
                    "year": movie.get("year"),
                    "date": movie.get("date"),
                    "description": movie.get("description"),
                    "image": movie.get("image"),
                    "poster": movie.get("poster"),
                    "studio": movie.get("studio"),
                    "performers": movie.get("performers", []),
                    "type": "movie",
                }
                for movie in data
            ]

        elif type == "performers":
            response = await client.search_performers(q=q, per_page=25)
            data = response.get("data", [])
            # Flatten performer data for UI display
            results = [
                {
                    "id": performer.get("id"),
                    "name": performer.get("name"),
                    "slug": performer.get("slug"),
                    "bio": performer.get("bio"),
                    "image": performer.get("image"),
                    "gender": performer.get("gender"),
                    "birthdate": performer.get("birthdate"),
                    "type": "performer",
                }
                for performer in data
            ]

        logger.info("TPDB search successful", query=q, search_type=type, result_count=len(results))
        return JSONResponse(
            {"data": results, "count": len(results), "type": type},
            status_code=status.HTTP_200_OK,
        )

    except TPDBNotFoundError:
        logger.warning("TPDB search returned no results", query=q, search_type=type)
        return JSONResponse(
            {"data": [], "count": 0, "type": type},
            status_code=status.HTTP_200_OK,
        )

    except TPDBError as e:
        logger.error("TPDB API error", query=q, search_type=type, error=str(e), status=e.status_code)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TPDB API error: {e.message}",
        )

    except Exception as e:
        logger.error("Unexpected error during search", query=q, search_type=type, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during search",
        )


@router.get("/cache", response_class=HTMLResponse)
async def cache_page(
    request: Request,
    username: str = Depends(verify_credentials),
) -> HTMLResponse:
    """Cache management page."""
    cache_service = get_cache_service()
    cache_stats = await cache_service.get_stats()

    return templates.TemplateResponse(
        "cache.html",
        {
            "request": request,
            "username": username,
            "cache_stats": cache_stats,
        },
    )


@router.post("/cache/clear")
async def clear_cache(
    request: Request,
    endpoint: Optional[str] = Form(None),
    username: str = Depends(verify_credentials),
) -> RedirectResponse:
    """Clear cache entries."""
    cache_service = get_cache_service()
    count = await cache_service.clear(endpoint if endpoint else None)
    logger.info("Cache cleared", endpoint=endpoint, count=count, user=username)

    return RedirectResponse(url="/admin/cache", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/cache/clear-expired")
async def clear_expired_cache(
    request: Request,
    username: str = Depends(verify_credentials),
) -> RedirectResponse:
    """Clear expired cache entries."""
    cache_service = get_cache_service()
    count = await cache_service.clear_expired()
    logger.info("Expired cache cleared", count=count, user=username)

    return RedirectResponse(url="/admin/cache", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    username: str = Depends(verify_credentials),
) -> HTMLResponse:
    """Settings page."""
    settings = get_settings()

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "username": username,
            "settings": settings,
        },
    )
