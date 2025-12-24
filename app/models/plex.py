"""Pydantic models for Plex MediaProvider API."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.constants import FeatureType, MetadataType


class Scheme(BaseModel):
    """Scheme definition for a metadata type."""

    scheme: str


class TypeDefinition(BaseModel):
    """Type definition for MediaProvider."""

    type: MetadataType
    schemes: list[Scheme] = Field(alias="Scheme")

    model_config = ConfigDict(populate_by_name=True)


class Feature(BaseModel):
    """Feature definition for MediaProvider."""

    type: FeatureType
    key: str


class MediaProvider(BaseModel):
    """Plex MediaProvider definition."""

    identifier: str
    title: str
    version: str = "1.0.0"
    types: list[TypeDefinition] = Field(alias="Types")
    features: list[Feature] = Field(alias="Feature")

    model_config = ConfigDict(populate_by_name=True)


class MediaProviderResponse(BaseModel):
    """Response wrapper for MediaProvider."""

    media_provider: MediaProvider = Field(alias="MediaProvider")

    model_config = ConfigDict(populate_by_name=True)


class Tag(BaseModel):
    """Tag/Genre for metadata."""

    tag: str


class Role(BaseModel):
    """Actor/Performer role for metadata."""

    tag: str
    role: str = ""
    thumb: Optional[str] = None


class Guid(BaseModel):
    """External GUID reference."""

    id: str


class MetadataItem(BaseModel):
    """Metadata item for shows, seasons, episodes, or movies."""

    type: str
    ratingKey: str
    guid: str
    title: str
    summary: Optional[str] = None
    thumb: Optional[str] = None
    art: Optional[str] = None
    year: Optional[int] = None
    studio: Optional[str] = None

    # TV-specific fields
    index: Optional[int] = None
    parentIndex: Optional[int] = None
    parentTitle: Optional[str] = None
    parentThumb: Optional[str] = None
    grandparentTitle: Optional[str] = None
    grandparentThumb: Optional[str] = None
    originallyAvailableAt: Optional[str] = None
    duration: Optional[int] = None  # milliseconds

    # Collections
    roles: Optional[list[Role]] = Field(default=None, alias="Role")
    genres: Optional[list[Tag]] = Field(default=None, alias="Genre")
    directors: Optional[list[Tag]] = Field(default=None, alias="Director")
    guids: Optional[list[Guid]] = Field(default=None, alias="Guid")

    model_config = ConfigDict(populate_by_name=True, exclude_none=True)


class MediaContainer(BaseModel):
    """Plex MediaContainer response wrapper."""

    offset: int = 0
    totalSize: int = 0
    identifier: str
    size: int = 0
    metadata: list[MetadataItem] = Field(default_factory=list, alias="Metadata")

    model_config = ConfigDict(populate_by_name=True)


class MediaContainerResponse(BaseModel):
    """Response wrapper for MediaContainer."""

    media_container: MediaContainer = Field(alias="MediaContainer")

    model_config = ConfigDict(populate_by_name=True)


class Image(BaseModel):
    """Image metadata for Plex."""

    type: str  # coverPoster, background, snapshot, clearLogo
    url: str
    ratingKey: Optional[str] = None


class ImagesContainer(BaseModel):
    """Container for images."""

    offset: int = 0
    totalSize: int = 0
    identifier: str
    size: int = 0
    images: list[Image] = Field(default_factory=list, alias="Image")

    model_config = ConfigDict(populate_by_name=True)


class MatchRequest(BaseModel):
    """Incoming match request from Plex."""

    type: MetadataType
    title: Optional[str] = None
    year: Optional[int] = None
    guid: Optional[str] = None  # External ID like "tvdb://12345"

    # TV-specific
    index: Optional[int] = None  # Episode number
    parentIndex: Optional[int] = None  # Season number
    parentTitle: Optional[str] = None  # Season title
    grandparentTitle: Optional[str] = None  # Show title
    date: Optional[str] = None  # Air date YYYY-MM-DD

    # File hints
    filename: Optional[str] = None
    duration: Optional[int] = None


class PagingOptions(BaseModel):
    """Pagination options for metadata requests."""

    containerStart: int = 0
    containerSize: int = 50


class MetadataOptions(BaseModel):
    """Options for metadata retrieval."""

    language: str = "en"
    country: str = "US"
    includeChildren: bool = False
    episodeOrder: Optional[str] = None
