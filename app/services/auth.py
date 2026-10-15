"""Senhas e sessões opacas; nenhum segredo é registrado em logs."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import hashlib
import hmac
import re
import secrets

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import delete, select, text, update
from sqlalchemy.orm import Session

from app.models import AuthSession, LoginChallenge, LoginLimit, User

# Perfil mínimo OWASP: 19 MiB, duas passagens, uma via; salt gerado pela biblioteca.
password_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1,
                                 hash_len=32, salt_len=16, type=Type.ID)
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}\Z")
USERNAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9_.-]{2,63}\Z")


class AuthError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        super().__init__(message)


class BootstrapError(Exception):
    pass


def timestamp(clock):
    value = clock()
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value


def token_hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def valid_token(value):
    return isinstance(value, str) and TOKEN_PATTERN.fullmatch(value) is not None


def normalize_username(value):
    normalized = value.strip().lower()
    if not USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError("Usuário: 3–64 caracteres ASCII; letras, números, ponto, hífen ou sublinhado.")
    return normalized


def validate_password(password):
    classes = [any(c.islower() for c in password), any(c.isupper() for c in password),
               any(c.isdigit() for c in password), any(not c.isalnum() for c in password)]
    if not 16 <= len(password) <= 128 or sum(classes) < 3:
        raise ValueError("Senha: 16–128 caracteres e pelo menos três classes: minúsculas, maiúsculas, números, símbolos.")


def hash_password(password):
    return password_hasher.hash(password)


@lru_cache(maxsize=1)
def dummy_hash():
    return hash_password(secrets.token_urlsafe(32))


def verify_password(password, stored_hash):
    try:
        return password_hasher.verify(stored_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def bootstrap_admin(engine, username, password):
    try:
        username = normalize_username(username)
        validate_password(password)
    except ValueError as exc:
        raise BootstrapError(str(exc)) from None
    with Session(engine) as session:
        # Serializa dois bootstraps simultâneos, inclusive com usernames distintos.
        session.execute(text("BEGIN IMMEDIATE"))
        if session.scalar(select(User.id).where(User.role == "admin").limit(1)) is not None:
            raise BootstrapError("Administrador já existe. Bootstrap encerrado; recuperação exige procedimento específico.")
        if session.scalar(select(User.id).where(User.username == username).limit(1)) is not None:
            raise BootstrapError("Usuário já existe. Nenhuma conta foi sobrescrita.")
        session.add(User(username=username, password_hash=hash_password(password), role="admin", active=True))
        session.commit()


def cleanup(session, model, key, condition):
    # Limita o trabalho de cada limpeza; nunca percorre/apaga todos os registros.
    expired = select(key).where(condition).limit(100)
    session.execute(delete(model).where(key.in_(expired)))


def create_challenge(engine, settings, clock, previous=None):
    now = timestamp(clock)
    cookie, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    with Session(engine) as session:
        cleanup(session, LoginChallenge, LoginChallenge.token_hash, LoginChallenge.expires_at <= now)
        if valid_token(previous):
            session.execute(delete(LoginChallenge).where(LoginChallenge.token_hash == token_hash(previous)))
        session.add(LoginChallenge(token_hash=token_hash(cookie), csrf_hash=token_hash(csrf),
                                   created_at=now, expires_at=now + timedelta(seconds=settings.login_challenge_seconds)))
        session.commit()
    return cookie, csrf


def reserve_attempt(session, key, maximum, now, window):
    identifier = token_hash(key)
    limit = session.get(LoginLimit, identifier)
    if limit is None:
        limit = LoginLimit(key_hash=identifier, attempts=0, expires_at=now + timedelta(seconds=window))
        session.add(limit)
    elif limit.expires_at <= now:
        limit.attempts = 0
        limit.expires_at = now + timedelta(seconds=window)
    if limit.attempts >= maximum:
        return False
    limit.attempts += 1
    return True


def login(engine, settings, clock, cookie, csrf, username, password, origin):
    now = timestamp(clock)
    if not valid_token(cookie) or not valid_token(csrf):
        raise AuthError(403, "Formulário expirado ou inválido. Abra novamente o login.")
    try:
        username = normalize_username(username)
    except ValueError:
        username = "~invalid"
    with Session(engine) as session:
        session.execute(text("BEGIN IMMEDIATE"))
        challenge = session.get(LoginChallenge, token_hash(cookie))
        if challenge is None or challenge.expires_at <= now or not hmac.compare_digest(challenge.csrf_hash, token_hash(csrf)):
            raise AuthError(403, "Formulário expirado ou inválido. Abra novamente o login.")
        session.delete(challenge)
        cleanup(session, LoginLimit, LoginLimit.key_hash, LoginLimit.expires_at <= now)
        account_ok = reserve_attempt(session, "account:" + username, settings.login_account_attempts,
                                     now, settings.login_attempt_window_seconds)
        origin_ok = reserve_attempt(session, "origin:" + origin, settings.login_origin_attempts,
                                    now, settings.login_attempt_window_seconds)
        user = session.scalar(select(User).where(User.username == username))
        # Capturar somente os campos necessários antes do commit/fechamento.
        credentials = (user.id, user.password_hash, user.active, user.role) if user else None
        session.commit()
    if not account_ok or not origin_ok:
        raise AuthError(429, "Não foi possível entrar. Confira as credenciais ou aguarde para tentar novamente.")
    usable_password = password if len(password) <= 128 else ""
    verified = verify_password(usable_password, credentials[1] if credentials else dummy_hash())
    if not verified or credentials is None or not credentials[2] or credentials[3] != "admin":
        raise AuthError(401, "Não foi possível entrar. Confira as credenciais ou aguarde para tentar novamente.")
    cookie, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    with Session(engine) as session:
        # Revalidar estado/papel após a verificação de senha, antes de emitir sessão.
        user = session.get(User, credentials[0])
        if user is None or not user.active or user.role != "admin" or user.password_hash != credentials[1]:
            raise AuthError(401, "Não foi possível entrar. Confira as credenciais ou aguarde para tentar novamente.")
        cleanup(session, AuthSession, AuthSession.id, AuthSession.expires_at <= now)
        session.add(AuthSession(user_id=user.id, token_hash=token_hash(cookie), csrf_token=csrf,
                                created_at=now, last_activity_at=now,
                                expires_at=now + timedelta(seconds=settings.session_absolute_seconds), revoked=False))
        session.commit()
    return cookie


@dataclass(frozen=True)
class AuthContext:
    session_id: int
    user_id: int
    username: str
    csrf_token: str
    last_activity_at: datetime


def authenticate(engine, settings, clock, cookie):
    if not valid_token(cookie):
        raise AuthError(401, "Autenticação necessária.")
    now = timestamp(clock)
    with Session(engine) as session:
        auth = session.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash(cookie)))
        if auth is None or auth.revoked or auth.expires_at <= now or auth.last_activity_at + timedelta(seconds=settings.session_idle_seconds) <= now:
            raise AuthError(401, "Autenticação necessária.")
        user = session.get(User, auth.user_id)
        if user is None or not user.active:
            raise AuthError(401, "Autenticação necessária.")
        if user.role != "admin":
            raise AuthError(403, "Acesso negado.")
        return AuthContext(auth.id, user.id, user.username, auth.csrf_token, auth.last_activity_at)


def csrf_matches(context, supplied):
    return valid_token(supplied) and hmac.compare_digest(context.csrf_token, supplied)


def touch_session(engine, settings, clock, context):
    now = timestamp(clock)
    if (now - context.last_activity_at).total_seconds() < settings.session_touch_seconds:
        return
    with Session(engine) as session:
        session.execute(update(AuthSession).where(
            AuthSession.id == context.session_id, AuthSession.revoked.is_(False),
            AuthSession.expires_at > now,
            AuthSession.last_activity_at <= now - timedelta(seconds=settings.session_touch_seconds),
        ).values(last_activity_at=now))
        session.commit()


def logout(engine, context):
    with Session(engine) as session:
        session.execute(update(AuthSession).where(AuthSession.id == context.session_id).values(revoked=True))
        session.commit()
