"""Mapper for transforming TPDB Movies to Plex Movies."""

from typing import Any, Optional

from app.constants import (
    MOVIE_PROVIDER_IDENTIFIER,
    RATING_KEY_MOVIE,
    ContentType,
)
from app.mappers.common import clean_text, extract_year, format_duration_ms
from app.models.plex import Guid, MetadataItem, Role, Tag


class MovieMapper:
    """Maps TPDB Movies to Plex Movies."""

    @staticmethod
    def movie_to_plex(movie_data: dict[str, Any]) -> MetadataItem:
        """Map a TPDB Movie to a Plex Movie.

        Args:
            movie_data: Raw movie data from TPDB API

        Returns:
            Plex MetadataItem for a movie
        """
        movie_id = movie_data.get("id", "")
        title = movie_data.get("title", "Unknown")
        date_str = movie_data.get("date")
        year = movie_data.get("year") or extract_year(date_str)
        duration_seconds = movie_data.get("duration")

        rating_key = f"{RATING_KEY_MOVIE}-{movie_id}"
        guid = f"{MOVIE_PROVIDER_IDENTIFIER}://movie/{rating_key}"

        # Get studio info
        studio_info = movie_data.get("studio") or {}
        studio_name = studio_info.get("name") if isinstance(studio_info, dict) else None

        # Map performers to roles
        performers = movie_data.get("performers", [])
        roles = [
            Role(tag=p.get("name", "Unknown"), thumb=p.get("image"))
            for p in performers
            if p.get("name")
        ]

        # Map directors
        directors = movie_data.get("directors", [])
        director_tags = [Tag(tag=d) for d in directors if isinstance(d, str)]

        # Map tags to genres
        tags = movie_data.get("tags", [])
        genres = [Tag(tag=t) for t in tags if isinstance(t, str)]

        # Get background image
        background = movie_data.get("background")
        art = None
        if isinstance(background, dict):
            art = background.get("full") or background.get("large")
        elif isinstance(background, str):
            art = background

        return MetadataItem(
            type=ContentType.MOVIE,
            ratingKey=rating_key,
            guid=guid,
            title=title,
            summary=clean_text(movie_data.get("description")),
            thumb=movie_data.get("poster") or movie_data.get("image"),
            art=art,
            year=year,
            studio=studio_name,
            originallyAvailableAt=date_str,
            duration=format_duration_ms(duration_seconds),
            roles=roles if roles else None,
            genres=genres if genres else None,
            directors=director_tags if director_tags else None,
            guids=[Guid(id=f"tpdb://{movie_id}")],
        )

    @staticmethod
    def parse_rating_key(rating_key: str) -> dict[str, Any]:
        """Parse a movie rating key to extract the movie ID.

        Args:
            rating_key: The rating key to parse

        Returns:
            Dictionary with parsed components:
            - type: "movie"
            - movie_id: The movie ID
        """
        result: dict[str, Any] = {"type": None}

        if rating_key.startswith(f"{RATING_KEY_MOVIE}-"):
            result["type"] = "movie"
            result["movie_id"] = rating_key[len(f"{RATING_KEY_MOVIE}-") :]

        return result
