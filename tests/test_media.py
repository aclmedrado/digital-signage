from dataclasses import replace
from io import BytesIO
from pathlib import Path
import subprocess
import sys
from uuid import UUID

from fastapi.testclient import TestClient
from PIL import Image
import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.config import MediaSettings, get_media_settings
from app.main import app
from app.models import MediaAsset
from app.services import media


def image_bytes(format="PNG", size=(16, 12), frames=1):
    images = [Image.new("RGB", size, (index * 37 % 256, 90, 150)) for index in range(frames)]
    with BytesIO() as output:
        images[0].save(output, format=format, save_all=frames > 1,
                       **({"append_images": images[1:], "duration": 100, "loop": 0} if frames > 1 else {}))
        return output.getvalue()


def upload(client, content=None, filename="campaign.png", title="Campanha", content_type="application/octet-stream"):
    if content is None:
        content = image_bytes()
    return client.post("/admin/media", data={"title": title},
                       files={"file": (filename, content, content_type)}, follow_redirects=False)


def assets(engine):
    with Session(engine) as session:
        return session.scalars(select(MediaAsset).order_by(MediaAsset.id)).all()


def assert_rejected(response, engine, settings, message, code=422):
    assert response.status_code == code
    assert response.headers["content-type"].startswith("text/html")
    assert message in response.text
    assert "Traceback" not in response.text
    assert assets(engine) == []
    assert list(settings.directory.iterdir()) == []


def configure(settings, **changes):
    changed = replace(settings, **changes)
    app.dependency_overrides[get_media_settings] = lambda: changed
    return changed


@pytest.fixture(scope="session")
def videos(tmp_path_factory):
    # FFmpeg existe somente na imagem. Não há fixtures binárias no Git.
    directory = tmp_path_factory.mktemp("synthetic-video")
    results = {}
    for name, codec, audio in [("h264", "libx264", True), ("silent", "libx264", False),
                               ("incompatible", "mpeg4", False)]:
        path = directory / f"{name}.mp4"
        command = ["ffmpeg", "-v", "error", "-nostdin", "-f", "lavfi", "-i",
                   "color=c=blue:s=64x48:r=24"]
        if audio:
            command += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100"]
        command += ["-t", "0.5", "-c:v", codec, "-threads", "1", "-pix_fmt", "yuv420p"]
        if audio:
            command += ["-c:a", "aac"]
        command += ["-movflags", "+faststart", str(path)]
        subprocess.run(command, shell=False, check=True, timeout=15, capture_output=True)
        results[name] = path.read_bytes()
    return results


def test_empty_catalog_and_navigation(client):
    response = client.get("/admin/media")
    assert response.status_code == 200
    assert "Nenhuma mídia cadastrada" in response.text
    assert "/admin/media/new" in response.text
    assert "/admin/screens" in response.text
    assert "/admin/media" in client.get("/admin/screens").text


def test_upload_form(client, isolated_media):
    settings = configure(isolated_media, max_video_upload_mb=3, max_image_upload_mb=1)
    response = client.get("/admin/media/new")
    assert response.status_code == 200
    for fragment in ['enctype="multipart/form-data"', 'name="title"', 'name="file"',
                     '.mp4,.jpg,.jpeg,.png,.webp,.gif', '3 MiB', '1 MiB', 'H.264', 'SVG']:
        assert fragment in response.text
    assert str(settings.max_image_frames) in response.text


@pytest.mark.parametrize("extension,format,mime", [
    (".jpg", "JPEG", "image/jpeg"), (".jpeg", "JPEG", "image/jpeg"),
    (".png", "PNG", "image/png"), (".webp", "WEBP", "image/webp"),
    (".gif", "GIF", "image/gif"), (".PNG", "PNG", "image/png"),
])
def test_image_upload(client, isolated_database, isolated_media, extension, format, mime):
    content = image_bytes(format)
    response = upload(client, content, "campaign" + extension, title="  Campanha  ", content_type="text/html")
    assert response.status_code == 303
    assert response.headers["location"].endswith("/admin/media?result=created")
    asset, = assets(isolated_database)
    assert asset.title == "Campanha"
    assert asset.kind == "image"
    assert asset.mime_type == mime
    assert asset.size_bytes == len(content)
    assert (asset.width, asset.height, asset.frame_count) == (16, 12, 1)
    assert asset.duration_seconds is asset.video_codec is asset.audio_codec is None
    assert asset.created_at is not None
    assert str(UUID(Path(asset.stored_filename).stem)) == Path(asset.stored_filename).stem
    assert (isolated_media.directory / asset.stored_filename).read_bytes() == content
    assert len(list(isolated_media.directory.iterdir())) == 1
    page = client.get(response.headers["location"])
    assert "Mídia cadastrada com sucesso." in page.text
    assert f"/media/{asset.id}/file" in page.text
    assert "16 × 12" in page.text
    client.get(response.headers["location"])
    assert len(assets(isolated_database)) == 1


@pytest.mark.parametrize("format,extension", [("GIF", ".gif"), ("WEBP", ".webp")])
def test_animation_preserved(client, isolated_database, isolated_media, format, extension):
    content = image_bytes(format, frames=3)
    assert upload(client, content, "animated" + extension).status_code == 303
    asset, = assets(isolated_database)
    assert asset.frame_count == 3
    stored = (isolated_media.directory / asset.stored_filename).read_bytes()
    assert stored == content
    with Image.open(BytesIO(stored)) as image:
        assert image.n_frames == 3


@pytest.mark.parametrize("name,audio", [("h264", "aac"), ("silent", None)])
def test_real_mp4_upload_and_metadata(client, isolated_database, isolated_media, videos, name, audio):
    content = videos[name]
    response = upload(client, content, "advertisement.mp4", content_type="image/png")
    assert response.status_code == 303
    asset, = assets(isolated_database)
    assert asset.kind == "video"
    assert asset.mime_type == "video/mp4"
    assert (asset.width, asset.height) == (64, 48)
    assert asset.duration_seconds == pytest.approx(0.5, abs=0.05)
    assert asset.frame_rate == 24
    assert asset.video_codec == "h264"
    assert asset.audio_codec == audio
    assert asset.frame_count is None
    assert (isolated_media.directory / asset.stored_filename).read_bytes() == content
    page = client.get("/admin/media")
    assert '<video controls muted preload="metadata"' in page.text
    assert "autoplay" not in page.text
    assert "0.50 s" in page.text


@pytest.mark.parametrize("filename,content,message", [
    ("file.txt", b"text", "Formato não permitido"),
    ("file.svg", b'<svg onload="alert(1)"></svg>', "SVG não é aceito"),
    ("file.png", b"not an image", "Imagem corrompida"),
    ("file.jpg", image_bytes("PNG"), "incompatível com a extensão"),
    ("file.png", b"", "arquivo está vazio"),
    ("file.mp4", b"", "arquivo está vazio"),
    ("file.png", image_bytes()[:-15], "Imagem corrompida"),
    ("file.mp4", b"not an mp4", "MP4"),
    ("x" * 256 + ".png", image_bytes(), "Nome de arquivo inválido"),
])
def test_invalid_upload(client, isolated_database, isolated_media, filename, content, message):
    response = upload(client, content, filename)
    assert_rejected(response, isolated_database, isolated_media, message)


@pytest.mark.parametrize("title", ["", "   ", "x" * 201])
def test_invalid_title(client, isolated_database, isolated_media, title):
    assert_rejected(upload(client, title=title), isolated_database, isolated_media, "título de 1 a 200")


def test_missing_file_is_html(client, isolated_database, isolated_media):
    response = client.post("/admin/media", data={"title": "Campanha"})
    assert_rejected(response, isolated_database, isolated_media, "Selecione um arquivo")


def test_non_file_form_value_is_html(client):
    response = client.post("/admin/media", data={"title": "Campanha", "file": "fake"})
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("text/html")


@pytest.mark.parametrize("extension", [".png", ".mp4"])
def test_received_size_limit(client, isolated_database, isolated_media, extension):
    configure(isolated_media, max_image_upload_mb=1, max_video_upload_mb=1)
    response = upload(client, b"x" * (1024 * 1024 + 1), "file" + extension)
    assert_rejected(response, isolated_database, isolated_media, "limite de 1 MiB", 413)


def test_image_pixels_limit(client, isolated_database, isolated_media):
    configure(isolated_media, max_image_pixels=100)
    assert_rejected(upload(client), isolated_database, isolated_media, "limite de 100 pixels")


@pytest.mark.parametrize("format,extension", [("GIF", ".gif"), ("WEBP", ".webp")])
@pytest.mark.parametrize("limit,message", [({"max_image_frames": 2}, "limite de 2 quadros"),
                                           ({"max_image_total_pixels": 400}, "pixels acumulados")])
def test_animation_resource_limits(client, isolated_database, isolated_media, format, extension, limit, message):
    configure(isolated_media, **limit)
    response = upload(client, image_bytes(format, frames=3), "animated" + extension)
    assert_rejected(response, isolated_database, isolated_media, message)


@pytest.mark.parametrize("filename", ["../../outside.png", r"..\..\outside.png", "/absolute.png",
                                      "../<script>alert(1)</script>.png"])
def test_original_name_never_controls_path(client, isolated_database, isolated_media, filename):
    assert upload(client, filename=filename).status_code == 303
    asset, = assets(isolated_database)
    assert asset.original_filename == filename
    assert media.stored_path(asset, isolated_media).parent == isolated_media.directory
    assert len(list(isolated_media.directory.iterdir())) == 1
    assert not (isolated_media.directory.parent / "outside.png").exists()
    assert "<script>" not in client.get("/admin/media").text


def test_catalog_order_and_html_escape(client):
    upload(client, title='<script>alert("x")</script>')
    upload(client, title="Segunda campanha")
    response = client.get("/admin/media")
    assert "<script>" not in response.text
    assert "&lt;script&gt;" in response.text
    assert response.text.index("&lt;script&gt;") < response.text.index("Segunda campanha")
    rejected = upload(client, b"bad", title='<script>alert("x")</script>')
    assert "&lt;script&gt;" in rejected.text
    assert "<script>" not in rejected.text


def test_image_delivery_headers(client, isolated_database):
    content = image_bytes()
    upload(client, content)
    asset, = assets(isolated_database)
    response = client.get(f"/media/{asset.id}/file")
    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"] == "image/png"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in response.headers["content-security-policy"]
    assert response.headers["content-disposition"].startswith("inline;")
    assert "campaign.png" not in response.headers["content-disposition"]


def test_mp4_delivery_and_range(client, isolated_database, videos):
    content = videos["h264"]
    upload(client, content, "campaign.mp4")
    asset, = assets(isolated_database)
    url = f"/media/{asset.id}/file"
    full = client.get(url)
    assert full.status_code == 200
    assert full.content == content
    assert full.headers["content-type"] == "video/mp4"
    response = client.get(url, headers={"Range": "bytes=0-99"})
    assert response.status_code == 206
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-range"] == f"bytes 0-99/{len(content)}"
    assert len(response.content) == 100
    assert response.content == content[:100]
    invalid = client.get(url, headers={"Range": f"bytes={len(content)}-"})
    assert invalid.status_code == 416
    assert invalid.headers["content-range"] == f"*/{len(content)}"
    malformed = client.get(url, headers={"Range": "bytes=wrong"})
    assert malformed.status_code == 400


def test_missing_file_and_missing_asset(client, isolated_database, isolated_media):
    assert client.get("/media/999999/file").status_code == 404
    assert client.get("/media/../../etc/passwd/file").status_code == 404
    upload(client)
    asset, = assets(isolated_database)
    (isolated_media.directory / asset.stored_filename).unlink()
    assert client.get(f"/media/{asset.id}/file").status_code == 404


def test_stored_path_rejects_outside_and_symlinks(client, isolated_database, isolated_media, tmp_path):
    upload(client)
    asset, = assets(isolated_database)
    path = isolated_media.directory / asset.stored_filename
    outside = tmp_path / "outside.png"
    outside.write_bytes(image_bytes())
    path.unlink()
    path.symlink_to(outside)
    assert client.get(f"/media/{asset.id}/file").status_code == 404
    asset.stored_filename = "../../outside.png"
    assert media.stored_path(asset, isolated_media) is None


def test_database_failure_rolls_back_and_removes_file(client, isolated_database, isolated_media, monkeypatch):
    with monkeypatch.context() as scoped:
        def fail_commit(self):
            raise OperationalError("INSERT", {}, Exception("forced test failure"))
        scoped.setattr(Session, "commit", fail_commit)
        response = upload(client)
    assert_rejected(response, isolated_database, isolated_media, "Não foi possível registrar", 500)
    assert upload(client).status_code == 303
    assert len(assets(isolated_database)) == 1


def test_uuid_collision_does_not_overwrite(client, isolated_database, isolated_media, monkeypatch):
    identifier = UUID("12345678-1234-4234-8234-123456789012")
    path = isolated_media.directory / f"{identifier}.png"
    path.write_bytes(b"existing")
    monkeypatch.setattr(media, "uuid4", lambda: identifier)
    response = upload(client)
    assert response.status_code == 503
    assert assets(isolated_database) == []
    assert path.read_bytes() == b"existing"
    assert list(isolated_media.directory.iterdir()) == [path]


def test_metadata_persists_across_startup(isolated_database, isolated_media):
    with TestClient(app) as client:
        upload(client, title="Persistente")
    original, = assets(isolated_database)
    isolated_database.dispose()
    with TestClient(app) as client:
        assert "Persistente" in client.get("/admin/media").text
        assert client.get(f"/media/{original.id}/file").content == image_bytes()
    restored, = assets(isolated_database)
    assert restored.stored_filename == original.stored_filename
    assert restored.created_at == original.created_at


def test_test_paths_are_isolated(client, isolated_database, isolated_media):
    assert Path(isolated_database.url.database).parent == isolated_media.directory.parent
    assert isolated_media.directory.resolve() != Path("/app/media")
    assert not isolated_media.directory.resolve().is_relative_to(Path("/app/media"))
    assert not Path(isolated_database.url.database).is_relative_to(Path("/app/data"))
    assert app.state.engine is isolated_database
    assert inspect(isolated_database).has_table("media_assets")


def test_existing_screen_is_preserved(client, isolated_database):
    data = {"name": "TV Piloto", "slug": "tv-piloto", "location": "Sala"}
    screen = client.post("/api/screens", json=data).json()
    upload(client)
    assert client.get(f"/api/screens/{screen['id']}").json() == screen
    assert {column["name"] for column in inspect(isolated_database).get_columns("screens")} == {
        "id", "name", "slug", "location", "active", "created_at", "updated_at"}


def test_real_incompatible_codec(client, isolated_database, isolated_media, videos):
    response = upload(client, videos["incompatible"], "campaign.mp4")
    assert_rejected(response, isolated_database, isolated_media, "Codec de vídeo incompatível")


def test_real_truncated_mp4(client, isolated_database, isolated_media, videos):
    response = upload(client, videos["h264"][:-100], "campaign.mp4")
    assert_rejected(response, isolated_database, isolated_media, "MP4 truncado")


def probe_metadata():
    return {"format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "0.5",
                       "tags": {"major_brand": "isom"}},
            "streams": [{"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p",
                         "width": 64, "height": 48, "duration": "0.5",
                         "avg_frame_rate": "24/1", "r_frame_rate": "24/1", "nb_read_packets": "12"}]}


@pytest.mark.parametrize("field,value,message", [
    ("codec_name", "hevc", "H.264"), ("codec_name", "av1", "H.264"),
    ("pix_fmt", "yuv420p10le", "8 bits"), ("pix_fmt", "yuv444p", "yuv420p"),
    ("width", 1921, "1920 × 1080"), ("height", 1081, "1920 × 1080"),
    ("width", 0, "Resolução"), ("duration", "N/A", "Metadados"),
    ("duration", "nan", "Metadados"), ("duration", "0", "Metadados"),
    ("avg_frame_rate", "31/1", "30 FPS"), ("r_frame_rate", "60/1", "30 FPS"),
    ("avg_frame_rate", "0/0", "Metadados"), ("nb_read_packets", "0", "pacotes"),
])
def test_video_metadata_rejections(client, isolated_database, isolated_media, videos, monkeypatch, field, value, message):
    data = probe_metadata()
    data["streams"][0][field] = value
    monkeypatch.setattr(media, "probe_video", lambda path, settings: data)
    response = upload(client, videos["silent"], "campaign.mp4")
    assert_rejected(response, isolated_database, isolated_media, message)


@pytest.mark.parametrize("case,message", [("no-video", "trilha de vídeo"), ("audio", "áudio incompatível"),
                                         ("mov", "contêiner deve ser MP4"), ("extra", "uma trilha"),
                                         ("json-shape", "Metadados MP4 inválidos")])
def test_other_probe_metadata_errors(client, isolated_database, isolated_media, videos, monkeypatch, case, message):
    data = probe_metadata()
    if case == "no-video":
        data["streams"] = []
    elif case == "audio":
        data["streams"].append({"codec_type": "audio", "codec_name": "mp3"})
    elif case == "mov":
        data["format"]["tags"]["major_brand"] = "qt  "
    elif case == "extra":
        data["streams"].append({"codec_type": "subtitle", "codec_name": "mov_text"})
    else:
        data = []
    monkeypatch.setattr(media, "probe_video", lambda path, settings: data)
    assert_rejected(upload(client, videos["silent"], "campaign.mp4"), isolated_database, isolated_media, message)


@pytest.mark.parametrize("code,message,status", [
    ("import time; time.sleep(2)", "tempo permitido", 422),
    ("print('not json')", "metadados inválidos", 422),
    ("import sys; sys.exit(1)", "MP4 inválido", 422),
    ("import sys; sys.stderr.write('corrupt'); print('{}')", "MP4 inválido", 422),
    ("import sys; sys.stdout.write('x' * 100000)", "limite de saída", 422),
    ("import sys; sys.stderr.write('x' * 100000)", "limite de saída", 422),
])
def test_probe_process_failures(client, isolated_database, isolated_media, videos, monkeypatch, code, message, status):
    configure(isolated_media, ffprobe_timeout_seconds=0.1 if "sleep" in code else 5)
    original_popen = subprocess.Popen
    def fake_probe(command, **kwargs):
        assert command[0] == "ffprobe"
        assert kwargs["shell"] is False
        assert Path(command[-1]).parent == isolated_media.directory
        assert Path(command[-1]).name.startswith(".upload-")
        assert "campaign.mp4" not in command
        return original_popen([sys.executable, "-c", code], **kwargs)
    monkeypatch.setattr(media.subprocess, "Popen", fake_probe)
    response = upload(client, videos["silent"], "campaign.mp4")
    assert_rejected(response, isolated_database, isolated_media, message, status)


def test_probe_missing_binary(client, isolated_database, isolated_media, videos, monkeypatch):
    def fail(*args, **kwargs):
        raise FileNotFoundError("test")
    monkeypatch.setattr(media.subprocess, "Popen", fail)
    response = upload(client, videos["silent"], "campaign.mp4")
    assert_rejected(response, isolated_database, isolated_media, "indisponível", 503)


def test_incremental_reads_and_exact_limit(client, isolated_database, isolated_media):
    from fastapi import UploadFile
    settings = replace(isolated_media, max_image_upload_mb=1)
    content = image_bytes()
    content += b"\0" * (1024 * 1024 - len(content))
    class BoundedReader(BytesIO):
        def read(self, size=-1):
            assert size == 1024 * 1024
            return super().read(size)
    with Session(isolated_database) as session:
        media.create_media("Limite exato", UploadFile(BoundedReader(content), filename="file.png"), session, settings)
    asset, = assets(isolated_database)
    assert asset.size_bytes == 1024 * 1024


@pytest.mark.parametrize("name", ["max_video_upload_mb", "max_image_upload_mb", "max_image_pixels",
                                  "max_image_frames", "max_image_total_pixels", "ffprobe_timeout_seconds"])
def test_configuration_rejects_nonpositive_limits(name):
    with pytest.raises(ValueError, match="positivo"):
        MediaSettings(**{name: 0})


def test_no_media_delete(client):
    assert client.delete("/admin/media").status_code == 405
    assert client.delete("/media/1/file").status_code == 405
