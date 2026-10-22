from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, String, UniqueConstraint
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


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('admin', 'viewer')", name="user_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="admin")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_token: Mapped[str] = mapped_column(String(43))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class LoginChallenge(Base):
    __tablename__ = "login_challenges"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class LoginLimit(Base):
    __tablename__ = "login_limits"

    key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    attempts: Mapped[int]
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class Playlist(Base):
    __tablename__ = "playlists"
    __table_args__ = (
        CheckConstraint("length(trim(name)) BETWEEN 1 AND 200", name="playlist_name"),
        CheckConstraint("description IS NULL OR length(description) <= 1000", name="playlist_description"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(1000))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class PlaylistItem(Base):
    __tablename__ = "playlist_items"
    __table_args__ = (
        UniqueConstraint("playlist_id", "position", name="playlist_item_position"),
        CheckConstraint("typeof(position) = 'integer' AND position > 0", name="playlist_item_positive_position"),
        CheckConstraint(
            "duration_seconds IS NULL OR "
            "(typeof(duration_seconds) = 'integer' AND duration_seconds BETWEEN 5 AND 600)",
            name="playlist_item_duration",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    playlist_id: Mapped[int] = mapped_column(ForeignKey("playlists.id"), index=True)
    media_id: Mapped[int] = mapped_column(ForeignKey("media_assets.id"), index=True)
    position: Mapped[int]
    duration_seconds: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class ScreenPlaylistAssignment(Base):
    __tablename__ = "screen_playlist_assignments"

    screen_id: Mapped[int] = mapped_column(ForeignKey("screens.id"), primary_key=True)
    playlist_id: Mapped[int] = mapped_column(ForeignKey("playlists.id"), index=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class ScreenPairingCode(Base):
    __tablename__ = "screen_pairing_codes"
    __table_args__ = (CheckConstraint("expires_at > created_at", name="pairing_expiry"),)

    screen_id: Mapped[int] = mapped_column(ForeignKey("screens.id"), primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class ScreenDeviceSession(Base):
    __tablename__ = "screen_device_sessions"
    __table_args__ = (CheckConstraint("expires_at > created_at", name="device_expiry"),)

    screen_id: Mapped[int] = mapped_column(ForeignKey("screens.id"), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class DeviceActivationChallenge(Base):
    __tablename__ = "device_activation_challenges"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class DeviceActivationLimit(Base):
    __tablename__ = "device_activation_limits"
    __table_args__ = (CheckConstraint("failures >= 0", name="activation_failures"),)

    key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    failures: Mapped[int]
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
