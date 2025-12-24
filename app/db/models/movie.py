"""Movie ORM model."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Movie(Base):
    """Movie model - maps to Plex Movie."""

    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True)
    tpdb_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    slug: Mapped[Optional[str]] = mapped_column(String(500))
    title: Mapped[str] = mapped_column(String(500), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    release_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    duration: Mapped[Optional[int]] = mapped_column(Integer)  # seconds
    url: Mapped[Optional[str]] = mapped_column(String(1000))

    # Studio info
    studio_name: Mapped[Optional[str]] = mapped_column(String(255))
    studio_id: Mapped[Optional[str]] = mapped_column(String(50))

    # Images
    poster_url: Mapped[Optional[str]] = mapped_column(String(1000))
    background_url: Mapped[Optional[str]] = mapped_column(String(1000))

    # Directors stored as JSON array
    directors: Mapped[Optional[list]] = mapped_column(JSON)

    # Tags stored as JSON array
    tags: Mapped[Optional[list]] = mapped_column(JSON)

    # Performers stored as JSON array (simplified)
    performers: Mapped[Optional[list]] = mapped_column(JSON)

    # Raw API response for reference
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Movie {self.title}>"
