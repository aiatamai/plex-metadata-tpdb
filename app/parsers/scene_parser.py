"""Scene filename parser for extracting metadata hints."""

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from app.parsers.patterns import (
    DATE_PATTERNS,
    FILE_EXTENSIONS,
    JAV_CODE_PATTERN,
    PERFORMER_SEPARATOR,
    QUALITY_PATTERNS,
    RESOLUTION_PATTERN,
    SCENE_NUMBER_PATTERN,
    SEPARATORS,
    SITE_PATTERNS,
)


@dataclass
class ParsedScene:
    """Parsed scene information from filename."""

    filename: str
    site: Optional[str] = None
    title: Optional[str] = None
    performers: list[str] = field(default_factory=list)
    release_date: Optional[date] = None
    scene_number: Optional[int] = None
    resolution: Optional[str] = None
    jav_code: Optional[str] = None
    confidence: float = 0.0

    def to_search_query(self) -> str:
        """Generate a search query from parsed data."""
        parts = []
        if self.site:
            parts.append(self.site)
        if self.performers:
            parts.extend(self.performers[:2])  # Limit to 2 performers
        if self.title:
            parts.append(self.title)
        return " ".join(parts)


class SceneParser:
    """Parser for extracting metadata from scene filenames."""

    @classmethod
    def parse(cls, filename: str) -> ParsedScene:
        """Parse a filename to extract metadata hints.

        Args:
            filename: The filename to parse

        Returns:
            ParsedScene with extracted information
        """
        result = ParsedScene(filename=filename)

        # Get just the filename without path
        name = Path(filename).name

        # Strip file extension
        name = FILE_EXTENSIONS.sub("", name)

        # Check for JAV code first
        jav_match = JAV_CODE_PATTERN.search(name)
        if jav_match:
            result.jav_code = f"{jav_match.group(1).upper()}-{jav_match.group(2)}"
            result.confidence += 0.3

        # Extract resolution
        res_match = RESOLUTION_PATTERN.search(name)
        if res_match:
            result.resolution = res_match.group(1).lower()
            # Remove resolution from name
            name = RESOLUTION_PATTERN.sub("", name)

        # Remove quality/codec markers
        name = QUALITY_PATTERNS.sub("", name)

        # Try site patterns
        for pattern in SITE_PATTERNS:
            match = pattern.match(name)
            if match:
                groups = match.groups()
                result.site = cls._clean_site_name(groups[0])
                result.confidence += 0.4

                # Extract date (groups 1-3 are date parts)
                result.release_date = cls._parse_date_parts(
                    groups[1], groups[2], groups[3]
                )
                if result.release_date:
                    result.confidence += 0.2

                # Remaining part is performers + title
                remaining = groups[4] if len(groups) > 4 else ""
                cls._parse_remaining(remaining, result)
                break

        # If no pattern matched, try generic date extraction
        if not result.release_date:
            result.release_date = cls._extract_date(name)
            if result.release_date:
                result.confidence += 0.1

        # Extract scene number
        scene_match = SCENE_NUMBER_PATTERN.search(name)
        if scene_match:
            result.scene_number = int(scene_match.group(1))

        # If we still don't have a title, use the cleaned filename
        if not result.title:
            result.title = cls._clean_title(name)
            if result.title:
                result.confidence += 0.1

        return result

    @classmethod
    def _clean_site_name(cls, name: str) -> str:
        """Clean and normalize a site name."""
        # Replace separators with spaces
        cleaned = SEPARATORS.sub(" ", name)
        # Capitalize each word
        return cleaned.strip().title()

    @classmethod
    def _parse_date_parts(
        cls, part1: str, part2: str, part3: str
    ) -> Optional[date]:
        """Parse date from three parts (could be YY.MM.DD or YYYY.MM.DD)."""
        try:
            # Determine if first part is year
            year = int(part1)
            month = int(part2)
            day = int(part3)

            # If year is 2 digits, assume 2000s
            if year < 100:
                year += 2000

            return date(year, month, day)
        except (ValueError, TypeError):
            return None

    @classmethod
    def _extract_date(cls, text: str) -> Optional[date]:
        """Extract date from text using various patterns."""
        for pattern in DATE_PATTERNS:
            match = pattern.search(text)
            if match:
                groups = match.groups()
                try:
                    # Determine date format based on values
                    parts = [int(g) for g in groups]

                    # YYYY-MM-DD format
                    if parts[0] > 1900:
                        return date(parts[0], parts[1], parts[2])
                    # DD-MM-YYYY format
                    elif parts[2] > 1900:
                        return date(parts[2], parts[1], parts[0])
                    # YY-MM-DD format
                    else:
                        year = parts[0] + 2000 if parts[0] < 100 else parts[0]
                        return date(year, parts[1], parts[2])
                except (ValueError, TypeError):
                    continue
        return None

    @classmethod
    def _parse_remaining(cls, text: str, result: ParsedScene) -> None:
        """Parse the remaining text after site and date extraction."""
        # Clean the text
        text = QUALITY_PATTERNS.sub("", text)
        text = RESOLUTION_PATTERN.sub("", text)
        text = SEPARATORS.sub(" ", text).strip()

        if not text:
            return

        # Split by common performer separators
        parts = PERFORMER_SEPARATOR.split(text)

        if len(parts) == 1:
            # No performer separator found - might be "Performer Name Title Here"
            # Try to identify performer names (typically 2-3 words at start)
            words = text.split()
            if len(words) >= 3:
                # Assume first 2 words are performer, rest is title
                result.performers = [" ".join(words[:2]).title()]
                result.title = " ".join(words[2:])
            else:
                result.title = text
        else:
            # Multiple parts - assume performers are first, title is last
            for part in parts[:-1]:
                part = part.strip()
                if part and len(part) > 2:
                    result.performers.append(part.title())

            # Last part is likely the title
            result.title = parts[-1].strip()

    @classmethod
    def _clean_title(cls, text: str) -> str:
        """Clean and normalize a title."""
        # Remove common noise
        text = QUALITY_PATTERNS.sub("", text)
        text = RESOLUTION_PATTERN.sub("", text)

        # Remove date patterns
        for pattern in DATE_PATTERNS:
            text = pattern.sub("", text)

        # Clean up separators
        text = SEPARATORS.sub(" ", text)

        # Remove multiple spaces and trim
        text = " ".join(text.split())

        return text.strip()
