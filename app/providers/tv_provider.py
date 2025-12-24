"""TV MediaProvider definition for ThePornDB.

Maps TPDB Sites to TV Shows and Scenes to Episodes.
Seasons are organized by release year.
"""

from app.constants import (
    API_PATHS,
    TV_PROVIDER_IDENTIFIER,
    TV_PROVIDER_TITLE,
    TV_PROVIDER_VERSION,
    FeatureType,
    MetadataType,
)
from app.models.plex import (
    Feature,
    MediaProvider,
    MediaProviderResponse,
    Scheme,
    TypeDefinition,
)


def create_tv_provider() -> MediaProvider:
    """Create the TV MediaProvider definition.

    This provider supports:
    - SHOW: TPDB Sites/Studios
    - SEASON: Grouped by release year
    - EPISODE: Individual scenes
    """
    return MediaProvider(
        identifier=TV_PROVIDER_IDENTIFIER,
        title=TV_PROVIDER_TITLE,
        version=TV_PROVIDER_VERSION,
        types=[
            TypeDefinition(
                type=MetadataType.SHOW,
                schemes=[Scheme(scheme=TV_PROVIDER_IDENTIFIER)],
            ),
            TypeDefinition(
                type=MetadataType.SEASON,
                schemes=[Scheme(scheme=TV_PROVIDER_IDENTIFIER)],
            ),
            TypeDefinition(
                type=MetadataType.EPISODE,
                schemes=[Scheme(scheme=TV_PROVIDER_IDENTIFIER)],
            ),
        ],
        features=[
            Feature(
                type=FeatureType.METADATA,
                key=API_PATHS.LIBRARY_METADATA,
            ),
            Feature(
                type=FeatureType.MATCH,
                key=API_PATHS.LIBRARY_MATCHES,
            ),
        ],
    )


def get_tv_provider_response() -> MediaProviderResponse:
    """Get the full MediaProvider response for the TV provider."""
    return MediaProviderResponse(media_provider=create_tv_provider())
