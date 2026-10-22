"""Dados sintéticos isolados; não representam teste de decodificação de vídeo."""
from html.parser import HTMLParser
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MediaAsset, Playlist, PlaylistItem, Screen, ScreenPlaylistAssignment, User
from app.services import device_auth
from tests.helpers import csrf_from


class PairingCodeParser(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.capturing = False
        self.code = None
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.capturing = tag == "strong" and dict(attrs).get("id") == "pairing-code"

    def handle_data(self, value):
        if self.capturing:
            self.code = value

    def handle_endtag(self, tag):
        self.capturing = False


def issue(client, screen_id):
    response = client.post(f"/admin/screens/{screen_id}/player/pairing")
    assert response.status_code == 200
    code = PairingCodeParser(response.text).code
    assert code
    return code


def activate(client, code, **kwargs):
    page = client.get("/device/activate")
    return client.post("/device/activate", data={"code": code, "csrf_token": csrf_from(page)},
                       follow_redirects=False, **kwargs)


def seed(engine, settings):
    result = {"screens": [], "assets": [], "items": []}
    with Session(engine) as session:
        playlist = Playlist(name="Campanha")
        session.add(playlist)
        session.flush()
        result["playlist"] = playlist.id
        for kind in ("image", "video"):
            filename = f"{uuid4()}.{'png' if kind == 'image' else 'mp4'}"
            payload = bytes(range(256)) * 2
            (settings.directory / filename).write_bytes(payload)
            asset = MediaAsset(title="Campanha " + kind, kind=kind, original_filename="original",
                               stored_filename=filename, mime_type="image/png" if kind == "image" else "video/mp4",
                               size_bytes=len(payload), width=16, height=12,
                               frame_count=1 if kind == "image" else None,
                               duration_seconds=1.25 if kind == "video" else None,
                               video_codec="h264" if kind == "video" else None,
                               frame_rate=24 if kind == "video" else None)
            session.add(asset)
            session.flush()
            result["assets"].append(asset.id)
        for position, media_id in enumerate([*result["assets"], result["assets"][0]], 1):
            item = PlaylistItem(playlist_id=playlist.id, media_id=media_id, position=position,
                                duration_seconds=5 + position if position != 2 else None)
            session.add(item)
            session.flush()
            result["items"].append(item.id)
        for slug in ("tv-piloto", "tv-patio"):
            screen = Screen(name=slug, slug=slug, location="Teste")
            session.add(screen)
            session.flush()
            result["screens"].append(screen.id)
            session.add(ScreenPlaylistAssignment(screen_id=screen.id, playlist_id=playlist.id))
        result["user"] = session.scalar(select(User.id).where(User.role == "admin"))
        session.commit()
    return result


def service_code(engine, clock, data, index=0):
    return device_auth.issue_code(engine, clock, str(data["screens"][index]), data["user"])


def service_activate(engine, clock, code, origin="isolated"):
    cookie, csrf = device_auth.create_challenge(engine, clock)
    return device_auth.activate(engine, clock, cookie, csrf, code, origin)
