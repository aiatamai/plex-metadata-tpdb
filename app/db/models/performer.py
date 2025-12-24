"""Performer ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.db.models.scene import Scene


class Performer(Base):
    """Performer model."""

    __tablename__ = "performers"

    id: Mapped[int] = mapped_column(primary_key=True)
    tpdb_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    slug: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    bio: Mapped[Optional[str]] = mapped_column(Text)

    # Physical attributes
    gender: Mapped[Optional[str]] = mapped_column(String(20))
    birthdate: Mapped[Optional[datetime]] = mapped_column(Date)
    birthplace: Mapped[Optional[str]] = mapped_column(String(255))
    ethnicity: Mapped[Optional[str]] = mapped_column(String(50))
    height: Mapped[Optional[int]] = mapped_column(Integer)  # cm
    weight: Mapped[Optional[int]] = mapped_column(Integer)  # kg
    measurements: Mapped[Optional[str]] = mapped_column(String(50))

    # Images
    image_url: Mapped[Optional[str]] = mapped_column(String(1000))

    # Aliases stored as JSON array
    aliases: Mapped[Optional[list]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    scenes: Mapped[list["ScenePerformer"]] = relationship(back_populates="performer")

    def __repr__(self) -> str:
        return f"<Performer {self.name}>"


class ScenePerformer(Base):
    """Association table for Scene-Performer many-to-many relationship."""

    __tablename__ = "scene_performers"

    scene_id: Mapped[int] = mapped_column(
        ForeignKey("scenes.id", ondelete="CASCADE"), primary_key=True
    )
    performer_id: Mapped[int] = mapped_column(
        ForeignKey("performers.id", ondelete="CASCADE"), primary_key=True
    )

    scene: Mapped["Scene"] = relationship(back_populates="scene_performers")
    performer: Mapped["Performer"] = relationship(back_populates="scenes")
