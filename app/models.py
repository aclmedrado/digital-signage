from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Screen(Base):
    __tablename__ = "screens"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    location: Mapped[str] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class MediaAsset(Base):
    __tablename__ = "media_assets"
    __table_args__ = (
        CheckConstraint("kind IN ('video', 'image')", name="media_kind"),
        CheckConstraint("length(title) BETWEEN 1 AND 200", name="media_title"),
        CheckConstraint("size_bytes > 0 AND width > 0 AND height > 0", name="media_dimensions"),
        CheckConstraint(
            "(kind = 'video' AND duration_seconds IS NOT NULL AND duration_seconds > 0 "
            "AND video_codec IS NOT NULL AND frame_rate IS NOT NULL "
            "AND frame_rate > 0 AND frame_count IS NULL) OR "
            "(kind = 'image' AND duration_seconds IS NULL AND video_codec IS NULL "
            "AND audio_codec IS NULL AND frame_rate IS NULL "
            "AND frame_count IS NOT NULL AND frame_count > 0)",
            name="media_metadata",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(5))
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(41), unique=True)
    mime_type: Mapped[str] = mapped_column(String(32))
    size_bytes: Mapped[int]
    width: Mapped[int]
    height: Mapped[int]
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    video_codec: Mapped[str | None] = mapped_column(String(16))
    audio_codec: Mapped[str | None] = mapped_column(String(16))
    frame_rate: Mapped[float | None] = mapped_column(Float)
    frame_count: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
