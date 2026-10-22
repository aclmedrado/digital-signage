"""Credenciais de TV independentes do login. Nenhum segredo é registrado."""
from base64 import b32encode
from contextlib import contextmanager
from datetime import timedelta
import hmac
import re
import secrets

from sqlalchemy import delete, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import (DeviceActivationChallenge, DeviceActivationLimit, Screen,
                        ScreenDeviceSession, ScreenPairingCode, User)
from app.services import auth

PAIRING_SECONDS = CHALLENGE_SECONDS = 600
DEVICE_SECONDS = 90 * 24 * 60 * 60
WINDOW_SECONDS = 900
MAX_FAILURES = 10
INVALID_CODE = "Não foi possível ativar. Confira o código ou aguarde para tentar novamente."


@contextmanager
def mutation(engine):
    # Sessão própria e lock ANTES das leituras; não reutiliza transação de GET.
    with Session(engine) as session:
        try:
            session.execute(text("BEGIN IMMEDIATE"))
            yield session
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise auth.AuthError(503, "Pareamento temporariamente indisponível.") from None
        except Exception:
            session.rollback()
            raise


def normalized_code(value):
    # Base32 canônico de 16 bytes (128 bits). Aceita só espaços ASCII/hífens
    # de apresentação e caixa; a última letra tem apenas os bits canônicos.
    if not isinstance(value, str) or not value.isascii() or len(value) > 128:
        return None
    code = value.replace(" ", "").replace("-", "").upper()
    return code if re.fullmatch(r"[A-Z2-7]{25}[AEIMQUY4]", code) else None


def screen_for_admin(session, screen_id):
    if not isinstance(screen_id, str) or not re.fullmatch(r"[0-9]{1,19}", screen_id):
        raise auth.AuthError(404, "Tela não encontrada.")
    number = int(screen_id)
    screen = session.get(Screen, number) if 1 <= number <= 9223372036854775807 else None
    if screen is None:
        raise auth.AuthError(404, "Tela não encontrada.")
    return screen


def issue_code(engine, clock, screen_id, user_id):
    code = b32encode(secrets.token_bytes(16)).decode("ascii").rstrip("=")
    with mutation(engine) as session:
        now = auth.timestamp(clock)
        screen = screen_for_admin(session, screen_id)
        user = session.get(User, user_id)
        if user is None or not user.active or user.role != "admin":
            raise auth.AuthError(403, "Acesso negado.")
        if not screen.active:
            raise auth.AuthError(409, "Ative a tela antes de gerar um código.")
        pairing = session.get(ScreenPairingCode, screen.id)
        if pairing is None:
            pairing = ScreenPairingCode(screen_id=screen.id)
            session.add(pairing)
        pairing.code_hash = auth.token_hash(code)
        pairing.created_by_user_id = user.id
        pairing.created_at = now
        pairing.expires_at = now + timedelta(seconds=PAIRING_SECONDS)
    return "-".join(code[i:i + 4] for i in range(0, len(code), 4))


def revoke(engine, screen_id):
    with mutation(engine) as session:
        screen = screen_for_admin(session, screen_id)
        session.execute(delete(ScreenPairingCode).where(ScreenPairingCode.screen_id == screen.id))
        session.execute(delete(ScreenDeviceSession).where(ScreenDeviceSession.screen_id == screen.id))


def create_challenge(engine, clock, previous=None):
    cookie, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    with mutation(engine) as session:
        now = auth.timestamp(clock)
        auth.cleanup(session, DeviceActivationChallenge, DeviceActivationChallenge.token_hash,
                     DeviceActivationChallenge.expires_at <= now)
        auth.cleanup(session, DeviceActivationLimit, DeviceActivationLimit.key_hash,
                     DeviceActivationLimit.expires_at <= now)
        if auth.valid_token(previous):
            session.execute(delete(DeviceActivationChallenge).where(
                DeviceActivationChallenge.token_hash == auth.token_hash(previous)))
        session.add(DeviceActivationChallenge(token_hash=auth.token_hash(cookie), csrf_hash=auth.token_hash(csrf),
                                              created_at=now, expires_at=now + timedelta(seconds=CHALLENGE_SECONDS)))
    return cookie, csrf


def activate(engine, clock, challenge_cookie, csrf, supplied_code, origin):
    if not auth.valid_token(challenge_cookie) or not auth.valid_token(csrf):
        raise auth.AuthError(403, "Formulário expirado ou inválido. Abra novamente a ativação.")
    error = None
    token = slug = None
    with mutation(engine) as session:
        now = auth.timestamp(clock)
        challenge = session.get(DeviceActivationChallenge, auth.token_hash(challenge_cookie))
        if challenge is None or challenge.expires_at <= now or not hmac.compare_digest(challenge.csrf_hash, auth.token_hash(csrf)):
            raise auth.AuthError(403, "Formulário expirado ou inválido. Abra novamente a ativação.")
        session.delete(challenge)  # Uso único inclusive em erro/429.
        auth.cleanup(session, DeviceActivationLimit, DeviceActivationLimit.key_hash, DeviceActivationLimit.expires_at <= now)
        auth.cleanup(session, ScreenPairingCode, ScreenPairingCode.screen_id, ScreenPairingCode.expires_at <= now)
        key = auth.token_hash("device-activation:" + origin)
        limit = session.get(DeviceActivationLimit, key)
        if limit is not None and limit.failures >= MAX_FAILURES:
            error = 429
        else:
            code = normalized_code(supplied_code)
            pairing = session.scalar(select(ScreenPairingCode).where(
                ScreenPairingCode.code_hash == auth.token_hash(code))) if code else None
            screen = session.get(Screen, pairing.screen_id) if pairing else None
            if pairing is None or pairing.expires_at <= now or screen is None or not screen.active:
                if limit is None:
                    limit = DeviceActivationLimit(key_hash=key, failures=0,
                                                  expires_at=now + timedelta(seconds=WINDOW_SECONDS))
                    session.add(limit)
                limit.failures += 1
                error = 401
            else:
                token, slug = secrets.token_urlsafe(32), screen.slug
                device = session.get(ScreenDeviceSession, screen.id)
                if device is None:
                    device = ScreenDeviceSession(screen_id=screen.id)
                    session.add(device)
                device.token_hash = auth.token_hash(token)
                device.created_at = now
                device.expires_at = now + timedelta(seconds=DEVICE_SECONDS)
                session.delete(pairing)
    # Erros de código precisam COMMIT do contador/consumo; falhas SQL fazem rollback.
    if error:
        raise auth.AuthError(error, INVALID_CODE)
    return token, slug


def authenticated_screen(request, session, slug):
    """Prévia admin OU cookie de dispositivo da própria tela; leituras sem escrita."""
    settings = request.app.state.auth_settings
    admin_cookie = request.cookies.get(settings.session_cookie_name)
    if admin_cookie:
        try:
            auth.authenticate(request.app.state.engine, settings, request.app.state.auth_clock, admin_cookie)
        except auth.AuthError as exc:
            if exc.status_code != 401:
                raise
        else:
            screen = session.scalar(select(Screen).where(Screen.slug == slug))
            if screen is None:
                raise auth.AuthError(404, "Conteúdo indisponível.")
            return screen
    cookie = request.cookies.get(settings.device_cookie_name)
    if not auth.valid_token(cookie):
        raise auth.AuthError(401, "Ativação necessária.")
    now = auth.timestamp(request.app.state.auth_clock)
    screen = session.scalar(select(Screen).join(ScreenDeviceSession, ScreenDeviceSession.screen_id == Screen.id)
                            .where(Screen.slug == slug, ScreenDeviceSession.token_hash == auth.token_hash(cookie),
                                   ScreenDeviceSession.expires_at > now))
    if screen is None:
        raise auth.AuthError(403, "Acesso indisponível. Ative novamente o dispositivo.")
    # Tela inativa continua autorizada somente para HTML/manifesto neutro.
    # O guard de mídia nega entrega; reativação pode retomar sem novo pareamento.
    return screen
