"""Common mapping utilities."""

from datetime import date
from typing import Any, Optional


def extract_year(date_str: Optional[str]) -> Optional[int]:
    """Extract year from a date string.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Year as integer or None
    """
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str).year
    except ValueError:
        # Try extracting just the year portion
        if len(date_str) >= 4:
            try:
                return int(date_str[:4])
            except ValueError:
                pass
        return None


def format_duration_ms(duration_seconds: Optional[int]) -> Optional[int]:
    """Convert duration from seconds to milliseconds for Plex.

    Args:
        duration_seconds: Duration in seconds

    Returns:
        Duration in milliseconds or None
    """
    if duration_seconds is None:
        return None
    return duration_seconds * 1000


def safe_get(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Safely get a nested value from a dictionary.

    Args:
        data: Dictionary to traverse
        keys: Keys to traverse
        default: Default value if not found

    Returns:
        Value at path or default
    """
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
            if current is None:
                return default
        else:
            return default
    return current if current is not None else default


def clean_text(text: Optional[str]) -> Optional[str]:
    """Clean and normalize text content.

    Args:
        text: Text to clean

    Returns:
        Cleaned text or None
    """
    if not text:
        return None
    # Strip whitespace and normalize newlines
    cleaned = text.strip()
    # Remove excessive whitespace
    cleaned = " ".join(cleaned.split())
    return cleaned if cleaned else None
