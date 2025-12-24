"""Site (Show) ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.db.models.scene import Scene


class Site(Base):
    """Site/Studio model - maps to Plex Show."""

    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(primary_key=True)
    tpdb_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    slug: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    short_name: Mapped[Optional[str]] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(String(500))
    logo_url: Mapped[Optional[str]] = mapped_column(String(1000))
    poster_url: Mapped[Optional[str]] = mapped_column(String(1000))
    network: Mapped[Optional[str]] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    scenes: Mapped[list["Scene"]] = relationship(back_populates="site")

    def __repr__(self) -> str:
        return f"<Site {self.name} ({self.slug})>"
