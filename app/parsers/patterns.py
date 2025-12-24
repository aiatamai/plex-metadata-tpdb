"""Regex patterns for filename parsing."""

import re

# Common date patterns
DATE_PATTERNS = [
    # YYYY-MM-DD or YYYY.MM.DD
    re.compile(r"(\d{4})[-.](\d{2})[-.](\d{2})"),
    # DD-MM-YYYY or DD.MM.YYYY
    re.compile(r"(\d{2})[-.](\d{2})[-.](\d{4})"),
    # YYMMDD
    re.compile(r"(\d{2})(\d{2})(\d{2})(?!\d)"),
    # YYYY_MM_DD
    re.compile(r"(\d{4})_(\d{2})_(\d{2})"),
]

# Resolution patterns
RESOLUTION_PATTERN = re.compile(
    r"\b(2160p|1080p|720p|480p|4k|uhd|hd|sd)\b",
    re.IGNORECASE,
)

# Common file extensions to strip
FILE_EXTENSIONS = re.compile(
    r"\.(mp4|mkv|avi|wmv|mov|m4v|webm|flv|ts)$",
    re.IGNORECASE,
)

# Quality/codec patterns to remove
QUALITY_PATTERNS = re.compile(
    r"\b(x264|x265|hevc|h\.?264|h\.?265|avc|xvid|divx|"
    r"aac|ac3|dts|mp3|"
    r"bluray|blu-ray|bdrip|brrip|web-?dl|webrip|hdtv|dvdrip|"
    r"xxx|porn|adult)\b",
    re.IGNORECASE,
)

# Common separators
SEPARATORS = re.compile(r"[._\-\s]+")

# Known site name patterns (commonly used formats)
SITE_PATTERNS = [
    # Site.YY.MM.DD.Performer.Title pattern
    re.compile(
        r"^([A-Za-z0-9]+(?:[A-Za-z0-9]+)*)"  # Site name
        r"[.\-_\s]+"
        r"(\d{2})[.\-_](\d{2})[.\-_](\d{2})"  # Date YY.MM.DD
        r"[.\-_\s]+"
        r"(.+)$",  # Rest (performers + title)
        re.IGNORECASE,
    ),
    # Site - YYYY-MM-DD - Title pattern
    re.compile(
        r"^([A-Za-z0-9\s]+?)"  # Site name
        r"\s*[-–]\s*"
        r"(\d{4})[.\-](\d{2})[.\-](\d{2})"  # Date YYYY-MM-DD
        r"\s*[-–]\s*"
        r"(.+)$",  # Title
        re.IGNORECASE,
    ),
]

# JAV code pattern (e.g., ABC-123, ABCD-12345)
JAV_CODE_PATTERN = re.compile(
    r"\b([A-Z]{2,6})-?(\d{2,5})\b",
    re.IGNORECASE,
)

# Performer name extraction (between site and title, often comma-separated)
PERFORMER_SEPARATOR = re.compile(r"[,&]")

# Common words to filter out when identifying site names
COMMON_WORDS = {
    "the", "and", "of", "in", "on", "at", "to", "for", "with",
    "a", "an", "is", "are", "was", "were", "be", "been",
}

# Scene numbering pattern
SCENE_NUMBER_PATTERN = re.compile(r"\b(?:scene|ep|episode|part)\s*(\d+)\b", re.IGNORECASE)
