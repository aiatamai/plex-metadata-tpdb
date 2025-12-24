"""Constants for the Plex MediaProvider."""

from enum import IntEnum, StrEnum


# Provider Identifiers
TV_PROVIDER_IDENTIFIER = "tv.plex.agents.tpdb.tv"
TV_PROVIDER_TITLE = "ThePornDB TV Provider"
TV_PROVIDER_VERSION = "1.0.0"

MOVIE_PROVIDER_IDENTIFIER = "tv.plex.agents.tpdb.movie"
MOVIE_PROVIDER_TITLE = "ThePornDB Movie Provider"
MOVIE_PROVIDER_VERSION = "1.0.0"


class MetadataType(IntEnum):
    """Plex metadata type identifiers."""

    MOVIE = 1
    SHOW = 2
    SEASON = 3
    EPISODE = 4
    COLLECTION = 18


class FeatureType(StrEnum):
    """Plex feature type identifiers."""

    METADATA = "metadata"
    MATCH = "match"
    COLLECTION = "collection"


class API_PATHS:
    """API endpoint paths for Plex MediaProvider."""

    LIBRARY_METADATA = "/library/metadata"
    LIBRARY_COLLECTIONS = "/library/collections"
    LIBRARY_MATCHES = "/library/metadata/matches"


# Rating Key Prefixes
RATING_KEY_SITE = "tpdb-site"
RATING_KEY_SEASON = "tpdb-season"
RATING_KEY_SCENE = "tpdb-scene"
RATING_KEY_MOVIE = "tpdb-movie"
RATING_KEY_PERFORMER = "tpdb-performer"


# Content Type Strings (for Plex responses)
class ContentType(StrEnum):
    """Plex content type strings."""

    SHOW = "show"
    SEASON = "season"
    EPISODE = "episode"
    MOVIE = "movie"


# ThePornDB API Endpoints
class TPDB_ENDPOINTS:
    """ThePornDB API endpoint paths."""

    SCENES = "/scenes"
    JAV = "/jav"
    MOVIES = "/movies"
    PERFORMERS = "/performers"
    SITES = "/sites"
