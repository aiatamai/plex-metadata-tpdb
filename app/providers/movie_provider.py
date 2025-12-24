"""Movie MediaProvider definition for ThePornDB.

Maps TPDB Movies to Plex Movies.
"""

from app.constants import (
    API_PATHS,
    MOVIE_PROVIDER_IDENTIFIER,
    MOVIE_PROVIDER_TITLE,
    MOVIE_PROVIDER_VERSION,
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


def create_movie_provider() -> MediaProvider:
    """Create the Movie MediaProvider definition.

    This provider supports:
    - MOVIE: Full-length films from TPDB
    """
    return MediaProvider(
        identifier=MOVIE_PROVIDER_IDENTIFIER,
        title=MOVIE_PROVIDER_TITLE,
        version=MOVIE_PROVIDER_VERSION,
        types=[
            TypeDefinition(
                type=MetadataType.MOVIE,
                schemes=[Scheme(scheme=MOVIE_PROVIDER_IDENTIFIER)],
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


def get_movie_provider_response() -> MediaProviderResponse:
    """Get the full MediaProvider response for the Movie provider."""
    return MediaProviderResponse(media_provider=create_movie_provider())
