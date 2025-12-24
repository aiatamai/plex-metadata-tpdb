"""Pydantic models for ThePornDB API responses."""

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, Field


class TPDBImage(BaseModel):
    """Image from TPDB."""

    url: str
    width: Optional[int] = None
    height: Optional[int] = None


class TPDBPerformer(BaseModel):
    """Performer from TPDB."""

    id: str
    name: str
    slug: Optional[str] = None
    bio: Optional[str] = None
    gender: Optional[str] = None
    birthdate: Optional[str] = None
    birthplace: Optional[str] = None
    ethnicity: Optional[str] = None
    height: Optional[int] = None
    weight: Optional[int] = None
    measurements: Optional[str] = None
    image: Optional[str] = None
    aliases: Optional[list[str]] = None
    extra: Optional[dict[str, Any]] = None


class TPDBSite(BaseModel):
    """Site/Studio from TPDB."""

    id: str
    name: str
    slug: Optional[str] = None
    short_name: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    logo: Optional[str] = None
    favicon: Optional[str] = None
    poster: Optional[str] = None
    network: Optional[str] = None
    parent: Optional[dict[str, Any]] = None


class TPDBScene(BaseModel):
    """Scene from TPDB."""

    id: str
    title: str
    slug: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None  # YYYY-MM-DD
    duration: Optional[int] = None  # seconds
    image: Optional[str] = None
    poster: Optional[str] = None
    background: Optional[dict[str, Any]] = None
    url: Optional[str] = None
    site: Optional[TPDBSite] = None
    performers: list[TPDBPerformer] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    markers: Optional[list[dict[str, Any]]] = None
    extra: Optional[dict[str, Any]] = None

    @property
    def release_date(self) -> Optional[date]:
        """Parse the release date."""
        if self.date:
            try:
                return date.fromisoformat(self.date)
            except ValueError:
                return None
        return None

    @property
    def year(self) -> Optional[int]:
        """Get the release year."""
        release = self.release_date
        return release.year if release else None


class TPDBMovie(BaseModel):
    """Movie from TPDB."""

    id: str
    title: str
    slug: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None
    year: Optional[int] = None
    duration: Optional[int] = None
    image: Optional[str] = None
    poster: Optional[str] = None
    background: Optional[dict[str, Any]] = None
    url: Optional[str] = None
    studio: Optional[TPDBSite] = None
    performers: list[TPDBPerformer] = Field(default_factory=list)
    directors: list[str] = Field(default_factory=list)
    scenes: list[TPDBScene] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    extra: Optional[dict[str, Any]] = None


class TPDBPagination(BaseModel):
    """Pagination info from TPDB."""

    current_page: int = 1
    from_: Optional[int] = Field(None, alias="from")
    to: Optional[int] = None
    per_page: int = 25
    total: int = 0
    last_page: int = 1


class TPDBSearchResponse(BaseModel):
    """Search response from TPDB."""

    data: list[Any] = Field(default_factory=list)
    meta: Optional[TPDBPagination] = None


class TPDBDetailResponse(BaseModel):
    """Detail response from TPDB."""

    data: dict[str, Any]
