"""Application configuration using pydantic-settings.

This module defines all configuration settings for the application.
Settings are loaded from environment variables (via .env file or system env),
with sensible defaults provided. Using Pydantic allows type validation
and coercion (e.g., "true" string -> bool True).
"""

from functools import lru_cache
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Pydantic BaseSettings automatically:
    - Loads from .env file
    - Reads from environment variables
    - Validates types
    - Provides defaults

    Configuration can be overridden by setting environment variables, e.g.:
        export DEBUG=true
        export TPDB_API_KEY=your_key_here
    """

    # Configure how Pydantic loads settings
    model_config = SettingsConfigDict(
        env_file=".env",  # Load from .env file first
        env_file_encoding="utf-8",  # UTF-8 file encoding
        case_sensitive=False,  # Allow ENV_VAR or env_var
        extra="ignore",  # Ignore unknown environment variables
    )

    # ===== APPLICATION SETTINGS =====
    # Display name of the provider
    app_name: str = "ThePornDB Plex Provider"
    # Enable debug mode (console logging, auto-reload, API docs)
    debug: bool = False

    # ===== SERVER SETTINGS =====
    # IP address to bind to (0.0.0.0 = all interfaces)
    provider_host: str = "0.0.0.0"
    # Port to listen on
    provider_port: int = 8000

    # ===== DATABASE SETTINGS =====
    # Database connection string
    # SQLite by default (async driver needed), can be PostgreSQL, MySQL, etc.
    database_url: str = "sqlite+aiosqlite:///./data/tpdb_provider.db"

    # ===== REDIS SETTINGS (OPTIONAL) =====
    # If not set, application falls back to in-memory cache
    # Format: redis://localhost:6379/0
    redis_url: Optional[str] = None

    # ===== THEPORNDB API SETTINGS =====
    # API key from https://theporndb.net (required - must be set)
    tpdb_api_key: str
    # Base URL for ThePornDB API
    tpdb_base_url: str = "https://api.theporndb.net"
    # Rate limit for outgoing requests to TPDB (respect their limits)
    tpdb_rate_limit: float = 2.0  # requests per second (max 2 requests/sec)

    # ===== CACHE TIME-TO-LIVE (TTL) SETTINGS =====
    # How long to cache different types of responses (in seconds)
    # Longer TTL = fewer API requests but potentially stale data
    cache_ttl_site_list: int = 86400  # Site/Studio list: 24 hours
    cache_ttl_site_detail: int = 604800  # Site details: 7 days (doesn't change often)
    cache_ttl_scene_search: int = 300  # Scene search results: 5 minutes (frequent queries)
    cache_ttl_scene_detail: int = 86400  # Individual scene: 24 hours
    cache_ttl_movie_detail: int = 86400  # Movie details: 24 hours

    # ===== INCOMING REQUEST RATE LIMITING =====
    # Limit requests TO this provider (from Plex)
    # Helps prevent abuse or accidental overloading
    rate_limit_default: str = "100/minute"  # General endpoints
    rate_limit_search: str = "30/minute"  # Search endpoints (more expensive)

    # ===== ADMIN AUTHENTICATION =====
    # Credentials for accessing the admin dashboard
    # Both must be configured via environment variables for security
    admin_username: str = "admin"
    admin_password: str  # Required - must be set via ADMIN_PASSWORD env var

    @field_validator("tpdb_api_key")
    @classmethod
    def validate_tpdb_api_key(cls, v: str) -> str:
        """Ensure TPDB API key is configured.

        Args:
            v: The TPDB API key value

        Returns:
            The validated API key

        Raises:
            ValueError: If API key is empty
        """
        if not v or not v.strip():
            raise ValueError(
                "TPDB_API_KEY environment variable must be set. "
                "Get your API key from https://theporndb.net"
            )
        return v

    @field_validator("admin_password")
    @classmethod
    def validate_admin_password(cls, v: str) -> str:
        """Ensure admin password is not the insecure default.

        Args:
            v: The admin password value

        Returns:
            The validated password

        Raises:
            ValueError: If password is empty or is the insecure default
        """
        if not v or not v.strip():
            raise ValueError("ADMIN_PASSWORD environment variable must be set")
        if v == "change_me_in_production":
            raise ValueError(
                "ADMIN_PASSWORD cannot use the default insecure value. "
                "Please set a strong password via the ADMIN_PASSWORD environment variable."
            )
        return v

    @property
    def is_redis_configured(self) -> bool:
        """Check if Redis is configured and available for use.

        Returns:
            True if redis_url is set and non-empty, False otherwise
        """
        return self.redis_url is not None and len(self.redis_url) > 0


# ===== SETTINGS SINGLETON =====
@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Using @lru_cache ensures that Settings is only instantiated once
    and subsequent calls return the same instance, improving performance.

    Returns:
        Settings: Singleton instance of the application settings
    """
    return Settings()
