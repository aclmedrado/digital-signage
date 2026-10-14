import os
from dataclasses import dataclass
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////app/data/signage.db")


@dataclass(frozen=True)
class MediaSettings:
    directory: Path = Path("/app/media")
    max_video_upload_mb: int = 250
    max_image_upload_mb: int = 10
    max_image_pixels: int = 20_000_000
    max_image_frames: int = 100
    max_image_total_pixels: int = 100_000_000
    ffprobe_timeout_seconds: int = 15

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            if name != "directory" and getattr(self, name) <= 0:
                raise ValueError(f"{name} deve ser positivo")


def get_media_settings():
    return MediaSettings(**{
        name: int(os.getenv(name.upper(), str(field.default)))
        for name, field in MediaSettings.__dataclass_fields__.items()
        if name != "directory"
    })
