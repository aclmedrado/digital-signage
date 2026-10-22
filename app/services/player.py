"""Manifesto determinístico e guard da programação atual, sem dados de credenciais."""
import hashlib
import json

from sqlalchemy import select

from app.models import MediaAsset, Playlist, PlaylistItem, Screen, ScreenPlaylistAssignment


def manifest(screen_id, session):
    # Um SELECT: vínculo, estado e sequência pertencem ao mesmo snapshot SQLite.
    rows = session.execute(select(Screen, ScreenPlaylistAssignment, Playlist, PlaylistItem, MediaAsset)
                           .outerjoin(ScreenPlaylistAssignment, ScreenPlaylistAssignment.screen_id == Screen.id)
                           .outerjoin(Playlist, Playlist.id == ScreenPlaylistAssignment.playlist_id)
                           .outerjoin(PlaylistItem, PlaylistItem.playlist_id == Playlist.id)
                           .outerjoin(MediaAsset, MediaAsset.id == PlaylistItem.media_id)
                           .where(Screen.id == screen_id)
                           .order_by(PlaylistItem.position, PlaylistItem.id)
                           .execution_options(populate_existing=True)).all()
    screen, assignment, playlist, _, _ = rows[0]
    state = "playing"
    if not screen.active:
        state = "screen_inactive"
    elif assignment is None:
        state = "no_playlist"
    elif playlist is None or not playlist.active or rows[0][3] is None or any(row[4] is None for row in rows):
        state = "playlist_unavailable"
    items = []
    if state == "playing":
        items = [{"id": item.id, "kind": asset.kind,
                  "duration_seconds": item.duration_seconds if asset.kind == "image" else None,
                  "url": f"/player/s/{screen.slug}/media/{asset.id}"}
                 for _, _, _, item, asset in rows]
    # Inclui versões e metadados relevantes, sem expô-los na resposta.
    identity = [screen.id, screen.slug, screen.name, screen.active, screen.updated_at, state,
                [assignment.playlist_id, assignment.assigned_at, assignment.updated_at] if assignment else None,
                [playlist.id, playlist.name, playlist.description, playlist.active, playlist.updated_at] if playlist else None,
                [[item.id, item.media_id, item.position, item.duration_seconds,
                  [asset.title, asset.kind, asset.stored_filename, asset.mime_type, asset.size_bytes,
                   asset.width, asset.height, asset.duration_seconds, asset.video_codec, asset.audio_codec,
                   asset.frame_rate, asset.frame_count, asset.created_at] if asset else None]
                 for _, _, _, item, asset in rows if item is not None]]
    revision = hashlib.sha256(json.dumps(identity, ensure_ascii=True, separators=(",", ":"),
                                         default=str).encode("utf-8")).hexdigest()
    return {"screen": {"slug": screen.slug, "name": screen.name}, "state": state,
            "revision": revision, "poll_after_seconds": 20, "items": items}


def current_asset(screen_id, media_id, session):
    if not media_id.isascii() or not media_id.isdecimal() or len(media_id) > 19:
        return None
    number = int(media_id)
    if not 1 <= number <= 9223372036854775807:
        return None
    return session.scalar(select(MediaAsset).join(PlaylistItem, PlaylistItem.media_id == MediaAsset.id)
                          .join(Playlist, Playlist.id == PlaylistItem.playlist_id)
                          .join(ScreenPlaylistAssignment, ScreenPlaylistAssignment.playlist_id == Playlist.id)
                          .join(Screen, Screen.id == ScreenPlaylistAssignment.screen_id)
                          .where(Screen.id == screen_id, Screen.active.is_(True), Playlist.active.is_(True),
                                 MediaAsset.id == number).limit(1))
