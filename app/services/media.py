import json
import logging
import math
import os
import selectors
import struct
import subprocess
import tempfile
import time
import warnings
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
from uuid import UUID, uuid4

from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models import MediaAsset

logger = logging.getLogger(__name__)
CHUNK_BYTES = 1024 * 1024
PROBE_OUTPUT_BYTES = 64 * 1024
IMAGE_FORMATS = {
    ".jpg": ("JPEG", "image/jpeg"),
    ".jpeg": ("JPEG", "image/jpeg"),
    ".png": ("PNG", "image/png"),
    ".webp": ("WEBP", "image/webp"),
    ".gif": ("GIF", "image/gif"),
}


class MediaError(Exception):
    def __init__(self, message, status_code=422):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class Metadata:
    kind: str
    mime_type: str
    width: int
    height: int
    duration_seconds: float | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    frame_rate: float | None = None
    frame_count: int | None = None


def list_media(session):
    return session.scalars(select(MediaAsset).order_by(MediaAsset.id)).all()


def stored_path(asset, settings):
    # Defesa adicional contra metadados físicos inválidos, mesmo vindos do banco.
    filename = asset.stored_filename
    try:
        path = Path(filename)
        if path.name != filename or path.suffix not in {".mp4", *IMAGE_FORMATS}:
            return None
        if str(UUID(path.stem)) != path.stem:
            return None
        root = settings.directory.resolve()
        resolved = (root / filename).resolve()
        if resolved.parent != root or not resolved.is_file():
            return None
        return resolved
    except (ValueError, OSError):
        return None


def validate_image(path, extension, settings):
    expected, mime_type = IMAGE_FORMATS[extension]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path, formats=[expected]) as image:
                width, height = image.size
                if width * height > settings.max_image_pixels:
                    raise MediaError(f"Imagem excede o limite de {settings.max_image_pixels} pixels.")
                if image.format != expected:
                    raise MediaError("O conteúdo da imagem não corresponde à extensão.")
                image.verify()
            # verify não decodifica pixels. Reabrir e carregar todos os quadros,
            # sem n_frames (que pode percorrer uma animação inteira sem limite).
            total_pixels = 0
            count = 0
            with Image.open(path, formats=[expected]) as image:
                for index in range(settings.max_image_frames + 1):
                    try:
                        image.seek(index)
                    except EOFError:
                        break
                    if index == settings.max_image_frames:
                        raise MediaError(f"Imagem excede o limite de {settings.max_image_frames} quadros.")
                    pixels = image.width * image.height
                    if pixels > settings.max_image_pixels:
                        raise MediaError(f"Imagem excede o limite de {settings.max_image_pixels} pixels.")
                    total_pixels += pixels
                    if total_pixels > settings.max_image_total_pixels:
                        raise MediaError("Imagem excede o limite de pixels acumulados dos quadros.")
                    image.load()
                    count += 1
            return Metadata("image", mime_type, width, height, frame_count=count)
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise MediaError("Imagem excessivamente grande para análise segura.") from None
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, EOFError, struct.error):
        raise MediaError("Imagem corrompida ou conteúdo incompatível com a extensão.") from None


def probe_video(path, settings):
    command = [
        "ffprobe", "-v", "error", "-protocol_whitelist", "file",
        "-format_whitelist", "mov", "-enable_drefs", "0", "-use_absolute_path", "0",
        "-threads", "1", "-max_alloc", "67108864",
        "-probesize", "5242880", "-analyzeduration", "5000000", "-count_packets",
        "-show_entries",
        "format=format_name,duration:format_tags=major_brand:"
        "stream=codec_type,codec_name,pix_fmt,width,height,duration,avg_frame_rate,r_frame_rate,nb_read_packets",
        "-of", "json", str(path),
    ]
    # Ler pipes em blocos com teto conjunto evita communicate/capture_output
    # acumularem saída ilimitada de um processo que analisa dados não confiáveis.
    try:
        with subprocess.Popen(command, shell=False, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
            output, errors = bytearray(), bytearray()
            deadline = time.monotonic() + settings.ffprobe_timeout_seconds
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(process.stdout, selectors.EVENT_READ, output)
                    selector.register(process.stderr, selectors.EVENT_READ, errors)
                    while selector.get_map():
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise subprocess.TimeoutExpired(command, settings.ffprobe_timeout_seconds)
                        for key, _ in selector.select(remaining):
                            block = os.read(key.fileobj.fileno(), 8192)
                            if not block:
                                selector.unregister(key.fileobj)
                                continue
                            if len(output) + len(errors) + len(block) > PROBE_OUTPUT_BYTES:
                                raise MediaError("A análise do MP4 excedeu o limite de saída permitido.")
                            key.data.extend(block)
                code = process.wait(timeout=max(0.001, deadline - time.monotonic()))
                if code != 0 or errors:
                    raise MediaError("MP4 inválido, truncado ou não reconhecido pelo ffprobe.")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
    except subprocess.TimeoutExpired:
        raise MediaError("A análise do MP4 excedeu o tempo permitido. Confira o arquivo.") from None
    except OSError:
        raise MediaError("A ferramenta de análise de vídeo está indisponível.", 503) from None
    try:
        return json.loads(output)
    except (ValueError, UnicodeError):
        raise MediaError("O ffprobe retornou metadados inválidos para este MP4.") from None


def check_mp4_boxes(path):
    # Recusar truncamento mesmo quando moov/ftyp antecedem um mdat incompleto.
    size = path.stat().st_size
    seen = set()
    with path.open("rb") as source:
        offset = 0
        for _ in range(10_000):
            if offset == size:
                break
            source.seek(offset)
            header = source.read(8)
            if len(header) != 8:
                raise MediaError("MP4 truncado ou estrutura inválida.")
            box_size = int.from_bytes(header[:4], "big")
            header_size = 8
            if box_size == 1:
                extended = source.read(8)
                if len(extended) != 8:
                    raise MediaError("MP4 truncado ou estrutura inválida.")
                box_size = int.from_bytes(extended, "big")
                header_size = 16
            elif box_size == 0:
                box_size = size - offset
            if box_size < header_size or offset + box_size > size:
                raise MediaError("MP4 truncado ou estrutura inválida.")
            seen.add(header[4:8])
            offset += box_size
        else:
            raise MediaError("MP4 excede o limite de complexidade da estrutura.")
    if not {b"ftyp", b"moov", b"mdat"}.issubset(seen):
        raise MediaError("Arquivo não contém uma estrutura MP4 de vídeo válida.")


def positive_number(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError("Número inválido")
    return number


def validate_video(path, settings):
    check_mp4_boxes(path)
    data = probe_video(path, settings)
    try:
        formats = data["format"]["format_name"].split(",")
        brand = data["format"].get("tags", {}).get("major_brand", "").strip()
        brands = {"isom", "mp41", "mp42", "avc1", "M4V", "MSNV", "dash", "cmfc", "cmfs"}
        brands.update(f"iso{i}" for i in range(2, 10))
        if "mp4" not in formats or brand not in brands:
            raise MediaError("O contêiner deve ser MP4; MOV e outros formatos não são aceitos.")
        streams = data["streams"]
        videos = [stream for stream in streams if stream["codec_type"] == "video"]
        audios = [stream for stream in streams if stream["codec_type"] == "audio"]
        if not videos:
            raise MediaError("O MP4 não contém uma trilha de vídeo.")
        if len(videos) != 1 or len(audios) > 1 or len(streams) != len(videos) + len(audios):
            raise MediaError("Use MP4 com uma trilha de vídeo e, opcionalmente, uma trilha AAC.")
        video = videos[0]
        if video["codec_name"] != "h264":
            raise MediaError("Codec de vídeo incompatível. Use H.264; H.265 e AV1 não são aceitos.")
        if video["pix_fmt"] != "yuv420p":
            raise MediaError("Pixel format incompatível. Use H.264 de 8 bits com yuv420p.")
        width, height = int(video["width"]), int(video["height"])
        if width <= 0 or height <= 0 or width > 1920 or height > 1080:
            raise MediaError("Resolução incompatível. O máximo é 1920 × 1080.")
        duration = positive_number(video.get("duration", data["format"].get("duration")))
        rates = [positive_number(Fraction(video[name])) for name in ("avg_frame_rate", "r_frame_rate")]
        if max(rates) > 30:
            raise MediaError("Taxa de quadros incompatível. O máximo é 30 FPS.")
        if int(video["nb_read_packets"]) <= 0:
            raise MediaError("O MP4 não contém pacotes de vídeo válidos.")
        audio_codec = audios[0]["codec_name"] if audios else None
        if audio_codec not in (None, "aac"):
            raise MediaError("Codec de áudio incompatível. Use AAC ou vídeo sem áudio.")
        return Metadata("video", "video/mp4", width, height, duration,
                        "h264", audio_codec, frame_rate=rates[0])
    except (KeyError, TypeError, ValueError, OverflowError, ZeroDivisionError, AttributeError):
        raise MediaError("Metadados MP4 inválidos: confira duração, dimensões e taxa de quadros.") from None


def create_media(title, upload, session, settings):
    title = title.strip()
    if not title or len(title) > 200:
        raise MediaError("Informe um título de 1 a 200 caracteres.")
    if upload is None or not upload.filename:
        raise MediaError("Selecione um arquivo para enviar.")
    original = upload.filename
    if len(original) > 255 or any(ord(char) < 32 for char in original):
        raise MediaError("Nome de arquivo inválido ou maior que 255 caracteres.")
    extension = Path(original.replace("\\", "/")).suffix.lower()
    if extension == ".svg":
        raise MediaError("SVG não é aceito nesta etapa; requer sanitização ou conversão segura.")
    if extension not in {".mp4", *IMAGE_FORMATS}:
        raise MediaError("Formato não permitido. Use MP4, JPG, JPEG, PNG, WebP ou GIF.")
    maximum = settings.max_video_upload_mb if extension == ".mp4" else settings.max_image_upload_mb
    temporary = final = None
    saved = False
    try:
        with tempfile.NamedTemporaryFile(dir=settings.directory, prefix=".upload-", suffix=".tmp",
                                         delete=False) as destination:
            temporary = Path(destination.name)
            size = 0
            while block := upload.file.read(CHUNK_BYTES):
                size += len(block)
                if size > maximum * CHUNK_BYTES:
                    raise MediaError(f"Arquivo excede o limite de {maximum} MiB.", 413)
                destination.write(block)
        if size == 0:
            raise MediaError("O arquivo está vazio.")
        metadata = (validate_video(temporary, settings) if extension == ".mp4"
                    else validate_image(temporary, extension, settings))
        filename = f"{uuid4()}{extension}"
        candidate = settings.directory / filename
        # Publicação atômica no mesmo volume, sem sobrescrever em uma colisão UUID.
        os.link(temporary, candidate)
        final = candidate
        temporary.unlink()
        asset = MediaAsset(title=title, original_filename=original, stored_filename=filename,
                           size_bytes=size, **asdict(metadata))
        session.add(asset)
        session.flush()
        session.commit()
        saved = True
        return asset
    except SQLAlchemyError:
        session.rollback()
        logger.exception("Falha ao registrar metadados de mídia")
        raise MediaError("Não foi possível registrar a mídia. Tente novamente.", 500) from None
    except OSError:
        session.rollback()
        logger.exception("Falha no armazenamento de mídia")
        raise MediaError("Não foi possível armazenar a mídia. Verifique espaço e permissões.", 503) from None
    finally:
        cleanup_failed = False
        for path in (temporary, final if not saved else None):
            if path is not None:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    cleanup_failed = True
                    logger.exception("Falha ao limpar arquivo de upload: %s", path)
        if cleanup_failed:
            raise MediaError("Não foi possível limpar os arquivos do envio. Verifique as permissões.", 503)
