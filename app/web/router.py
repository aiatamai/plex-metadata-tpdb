"""Admin Web UI routes."""

import secrets
from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

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
