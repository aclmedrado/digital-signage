import os
from ipaddress import ip_address
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


@dataclass(frozen=True)
class AuthSettings:
    session_cookie_secure: bool = True
    local_auth_test_mode: bool = False
    bind_ip: str = "127.0.0.1"
    port: int = 8080
    forwarded_allow_ips: str = ""
    session_absolute_seconds: int = 8 * 60 * 60
    session_idle_seconds: int = 30 * 60
    session_touch_seconds: int = 5 * 60
    login_challenge_seconds: int = 10 * 60
    login_attempt_window_seconds: int = 15 * 60
    login_account_attempts: int = 5
    login_origin_attempts: int = 20

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            if name.endswith(("_seconds", "_attempts")) and getattr(self, name) <= 0:
                raise ValueError(f"{name} deve ser positivo")
        if not 1 <= self.port <= 65535:
            raise ValueError("SIGNAGE_PORT inválida")
        if self.session_touch_seconds >= self.session_idle_seconds:
            raise ValueError("SESSION_TOUCH_SECONDS deve ser menor que SESSION_IDLE_SECONDS")
        if self.session_idle_seconds > self.session_absolute_seconds:
            raise ValueError("Inatividade não pode exceder a duração absoluta")
        if self.local_auth_test_mode:
            if self.session_cookie_secure or self.bind_ip != "127.0.0.1" or self.port != 8080 or self.forwarded_allow_ips:
                raise ValueError("Teste local exige Secure=false, binding 127.0.0.1:8080 e nenhum proxy confiável")
        elif not self.session_cookie_secure:
            raise ValueError("Secure=false exige LOCAL_AUTH_TEST_MODE explícito")
        for value in self.forwarded_allow_ips.split(","):
            if value.strip():
                try:
                    ip_address(value.strip())
                except ValueError:
                    raise ValueError("FORWARDED_ALLOW_IPS aceita somente IPs explícitos, nunca *") from None

    @property
    def session_cookie_name(self):
        return "__Host-signage-session" if self.session_cookie_secure else "signage-local-session"

    @property
    def challenge_cookie_name(self):
        return "__Host-signage-login" if self.session_cookie_secure else "signage-local-login"


def get_auth_settings():
    def boolean(name, default):
        value = os.getenv(name, str(default)).lower()
        if value not in {"true", "false"}:
            raise ValueError(f"{name} deve ser true ou false")
        return value == "true"

    settings = {
        "session_cookie_secure": boolean("SESSION_COOKIE_SECURE", True),
        "local_auth_test_mode": boolean("LOCAL_AUTH_TEST_MODE", False),
        "bind_ip": os.getenv("SIGNAGE_BIND_IP", "127.0.0.1"),
        "port": int(os.getenv("SIGNAGE_PORT", "8080")),
        "forwarded_allow_ips": os.getenv("FORWARDED_ALLOW_IPS", ""),
    }
    for name, field in AuthSettings.__dataclass_fields__.items():
        if name.endswith(("_seconds", "_attempts")):
            settings[name] = int(os.getenv(name.upper(), str(field.default)))
    return AuthSettings(**settings)
