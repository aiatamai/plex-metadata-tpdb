"""Scene (Episode) ORM model."""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.db.models.performer import ScenePerformer
    from app.db.models.site import Site


class Scene(Base):
    """Scene model - maps to Plex Episode."""

    __tablename__ = "scenes"

    id: Mapped[int] = mapped_column(primary_key=True)
    tpdb_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    slug: Mapped[Optional[str]] = mapped_column(String(500))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    release_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    duration: Mapped[Optional[int]] = mapped_column(Integer)  # seconds
    url: Mapped[Optional[str]] = mapped_column(String(1000))

    # Images
    poster_url: Mapped[Optional[str]] = mapped_column(String(1000))
    background_url: Mapped[Optional[str]] = mapped_column(String(1000))

    # Tags stored as JSON array
    tags: Mapped[Optional[list]] = mapped_column(JSON)

    # Raw API response for reference
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON)

    # Foreign key to site
    site_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sites.id", ondelete="SET NULL"), index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    site: Mapped[Optional["Site"]] = relationship(back_populates="scenes")
    scene_performers: Mapped[list["ScenePerformer"]] = relationship(
        back_populates="scene", cascade="all, delete-orphan"
    )

    @property
    def year(self) -> Optional[int]:
        """Get the release year."""
        return self.release_date.year if self.release_date else None

    def __repr__(self) -> str:
        return f"<Scene {self.title}>"
