"""Mapper for transforming TPDB Sites/Scenes to Plex Shows/Episodes."""

from datetime import date
from typing import Any, Optional

from app.constants import (
    RATING_KEY_SCENE,
    RATING_KEY_SEASON,
    RATING_KEY_SITE,
    TV_PROVIDER_IDENTIFIER,
    ContentType,
)
from app.mappers.common import clean_text, extract_year, format_duration_ms
from app.models.plex import Guid, MetadataItem, Role, Tag


class ShowMapper:
    """Maps TPDB Sites and Scenes to Plex Shows, Seasons, and Episodes."""

    @staticmethod
    def site_to_show(site_data: dict[str, Any]) -> MetadataItem:
        """Map a TPDB Site to a Plex Show.

        Args:
            site_data: Raw site data from TPDB API

        Returns:
            Plex MetadataItem for a show
        """
        site_id = site_data.get("id", "")
        slug = site_data.get("slug") or site_id
        name = site_data.get("name", "Unknown")

        rating_key = f"{RATING_KEY_SITE}-{slug}"
        guid = f"{TV_PROVIDER_IDENTIFIER}://show/{rating_key}"

        return MetadataItem(
            type=ContentType.SHOW,
            ratingKey=rating_key,
            guid=guid,
            title=name,
            summary=clean_text(site_data.get("description")),
            thumb=site_data.get("logo") or site_data.get("poster"),
            art=site_data.get("poster"),
            studio=site_data.get("network"),
            guids=[Guid(id=f"tpdb://{site_id}")],
        )

    @staticmethod
    def create_season(
        site_slug: str,
        site_name: str,
        year: int,
        site_thumb: Optional[str] = None,
    ) -> MetadataItem:
        """Create a Plex Season for a year grouping.

        Args:
            site_slug: The site slug
            site_name: The site name (grandparent title)
            year: The season year
            site_thumb: Optional thumbnail from the site

        Returns:
            Plex MetadataItem for a season
        """
        rating_key = f"{RATING_KEY_SEASON}-{site_slug}-{year}"
        guid = f"{TV_PROVIDER_IDENTIFIER}://season/{rating_key}"

        return MetadataItem(
            type=ContentType.SEASON,
            ratingKey=rating_key,
            guid=guid,
            title=str(year),
            index=year,
            parentIndex=0,  # Shows don't have a numeric index
            parentTitle=site_name,
            grandparentTitle=site_name,
            thumb=site_thumb,
        )

    @staticmethod
    def scene_to_episode(
        scene_data: dict[str, Any],
        site_data: Optional[dict[str, Any]] = None,
        episode_index: int = 1,
    ) -> MetadataItem:
        """Map a TPDB Scene to a Plex Episode.

        Args:
            scene_data: Raw scene data from TPDB API
            site_data: Optional site data for parent info
            episode_index: Episode index within the season

        Returns:
            Plex MetadataItem for an episode
        """
        scene_id = scene_data.get("id", "")
        title = scene_data.get("title", "Unknown")
        date_str = scene_data.get("date")
        year = extract_year(date_str)
        duration_seconds = scene_data.get("duration")

        rating_key = f"{RATING_KEY_SCENE}-{scene_id}"
        guid = f"{TV_PROVIDER_IDENTIFIER}://episode/{rating_key}"

        # Get site info
        site_info = site_data or scene_data.get("site", {}) or {}
        site_name = site_info.get("name", "Unknown")
        site_slug = site_info.get("slug") or site_info.get("id", "unknown")
        site_thumb = site_info.get("logo") or site_info.get("poster")

        # Map performers to roles
        performers = scene_data.get("performers", [])
        roles = [
            Role(tag=p.get("name", "Unknown"), thumb=p.get("image"))
            for p in performers
            if p.get("name")
        ]

        # Map tags to genres
        tags = scene_data.get("tags", [])
        genres = [Tag(tag=t) for t in tags if isinstance(t, str)]

        # Get background image
        background = scene_data.get("background")
        art = None
        if isinstance(background, dict):
            art = background.get("full") or background.get("large")
        elif isinstance(background, str):
            art = background

        return MetadataItem(
            type=ContentType.EPISODE,
            ratingKey=rating_key,
            guid=guid,
            title=title,
            summary=clean_text(scene_data.get("description")),
            thumb=scene_data.get("poster") or scene_data.get("image"),
            art=art,
            index=episode_index,
            parentIndex=year or 2024,  # Season = Year
            parentTitle=str(year) if year else "2024",
            parentThumb=site_thumb,
            grandparentTitle=site_name,
            grandparentThumb=site_thumb,
            originallyAvailableAt=date_str,
            duration=format_duration_ms(duration_seconds),
            roles=roles if roles else None,
            genres=genres if genres else None,
            guids=[Guid(id=f"tpdb://{scene_id}")],
        )

    @staticmethod
    def parse_rating_key(rating_key: str) -> dict[str, Any]:
        """Parse a rating key to extract its components.

        Args:
            rating_key: The rating key to parse

        Returns:
            Dictionary with parsed components:
            - type: "site", "season", "scene"
            - site_slug: Site slug (if applicable)
            - year: Season year (if applicable)
            - scene_id: Scene ID (if applicable)
        """
        result: dict[str, Any] = {"type": None}

        if rating_key.startswith(f"{RATING_KEY_SITE}-"):
            result["type"] = "site"
            result["site_slug"] = rating_key[len(f"{RATING_KEY_SITE}-") :]

        elif rating_key.startswith(f"{RATING_KEY_SEASON}-"):
            # Format: tpdb-season-{site_slug}-{year}
            result["type"] = "season"
            parts = rating_key[len(f"{RATING_KEY_SEASON}-") :].rsplit("-", 1)
            if len(parts) == 2:
                result["site_slug"] = parts[0]
                try:
                    result["year"] = int(parts[1])
                except ValueError:
                    result["year"] = None

        elif rating_key.startswith(f"{RATING_KEY_SCENE}-"):
            result["type"] = "scene"
            result["scene_id"] = rating_key[len(f"{RATING_KEY_SCENE}-") :]

        return result
