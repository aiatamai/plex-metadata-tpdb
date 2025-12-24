"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "ThePornDB Plex Provider"
    debug: bool = False

    # Server
    provider_host: str = "0.0.0.0"
    provider_port: int = 8000

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/tpdb_provider.db"

    # Redis (optional - falls back to in-memory cache if not set)
    redis_url: Optional[str] = None

    # ThePornDB API
    tpdb_api_key: str = ""
    tpdb_base_url: str = "https://api.theporndb.net"
    tpdb_rate_limit: float = 2.0  # requests per second

    # Caching TTLs (in seconds)
    cache_ttl_site_list: int = 86400  # 24 hours
    cache_ttl_site_detail: int = 604800  # 7 days
    cache_ttl_scene_search: int = 300  # 5 minutes
    cache_ttl_scene_detail: int = 86400  # 24 hours
    cache_ttl_movie_detail: int = 86400  # 24 hours

    # Rate Limiting (incoming requests)
    rate_limit_default: str = "100/minute"
    rate_limit_search: str = "30/minute"

    # Admin Authentication
    admin_username: str = "admin"
    admin_password: str = "change_me_in_production"

    @property
    def is_redis_configured(self) -> bool:
        """Check if Redis is configured."""
        return self.redis_url is not None and len(self.redis_url) > 0


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
