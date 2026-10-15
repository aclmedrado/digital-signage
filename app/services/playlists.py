"""Playlists e vínculos; todas as mutações são serializadas antes da leitura."""
from contextlib import contextmanager
import re

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from app.models import MediaAsset, Playlist, PlaylistItem, Screen, ScreenPlaylistAssignment, utc_now

MAX_ITEMS = 100


class PlaylistError(Exception):
    def __init__(self, message, status_code=422):
        self.status_code = status_code
        super().__init__(message)


@contextmanager
def mutation(session):
    # As rotas fornecem uma sessão sem escritas pendentes. O lock do SQLite
    # precede contagens/validações, inclusive entre adicionar, remover e associar.
    try:
        session.execute(text("BEGIN IMMEDIATE"))
        session.expire_all()
        yield
        session.commit()
    except (IntegrityError, OperationalError):
        session.rollback()
        raise PlaylistError("Conflito ao salvar. Recarregue a página e tente novamente.", 409) from None
    except SQLAlchemyError:
        session.rollback()
        raise PlaylistError("Não foi possível salvar. Tente novamente mais tarde.", 503) from None
    except Exception:
        session.rollback()
        raise


def identifier(value, label, status_code=404):
    if type(value) is int:
        number = value
    elif isinstance(value, str) and re.fullmatch(r"[0-9]{1,19}", value):
        number = int(value)
    else:
        raise PlaylistError(f"{label} inválido.", status_code)
    if not 1 <= number <= 9223372036854775807:
        raise PlaylistError(f"{label} inválido.", status_code)
    return number


def find_playlist(playlist_id, session):
    playlist = session.get(Playlist, identifier(playlist_id, "Identificador da playlist"))
    if playlist is None:
        raise PlaylistError("Playlist não encontrada.", 404)
    return playlist


def find_screen(screen_id, session):
    screen = session.get(Screen, identifier(screen_id, "Identificador da tela"))
    if screen is None:
        raise PlaylistError("Tela não encontrada.", 404)
    return screen


def find_item(playlist_id, item_id, session):
    item = session.get(PlaylistItem, identifier(item_id, "Identificador do item"))
    if item is None or item.playlist_id != playlist_id:
        raise PlaylistError("Item não encontrado nesta playlist.", 404)
    return item


def list_playlists(session):
    items = select(PlaylistItem.playlist_id, func.count().label("total")).group_by(PlaylistItem.playlist_id).subquery()
    screens = select(ScreenPlaylistAssignment.playlist_id, func.count().label("total")).group_by(ScreenPlaylistAssignment.playlist_id).subquery()
    return session.execute(select(Playlist, func.coalesce(items.c.total, 0), func.coalesce(screens.c.total, 0))
                           .outerjoin(items, items.c.playlist_id == Playlist.id)
                           .outerjoin(screens, screens.c.playlist_id == Playlist.id)
                           .order_by(Playlist.id)).all()


def list_items(playlist_id, session):
    return session.execute(select(PlaylistItem, MediaAsset).join(MediaAsset, MediaAsset.id == PlaylistItem.media_id)
                           .where(PlaylistItem.playlist_id == playlist_id)
                           .order_by(PlaylistItem.position, PlaylistItem.id)).all()


def assigned_screens(playlist_id, session):
    return session.scalars(select(Screen).join(ScreenPlaylistAssignment, ScreenPlaylistAssignment.screen_id == Screen.id)
                           .where(ScreenPlaylistAssignment.playlist_id == playlist_id).order_by(Screen.id)).all()


def screen_playlists(session):
    return dict(session.execute(select(ScreenPlaylistAssignment.screen_id, Playlist)
                                .join(Playlist, Playlist.id == ScreenPlaylistAssignment.playlist_id)).all())


def available_playlists(session):
    has_items = select(PlaylistItem.id).where(PlaylistItem.playlist_id == Playlist.id).exists()
    return session.scalars(select(Playlist).where(Playlist.active.is_(True), has_items).order_by(Playlist.id)).all()


def playlist_values(name, description):
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 200:
        raise PlaylistError("Informe um nome de 1 a 200 caracteres.")
    if description is not None and (not isinstance(description, str) or len(description) > 1000):
        raise PlaylistError("A descrição deve ter no máximo 1000 caracteres.")
    normalized_description = (description.strip() or None) if description is not None else None
    return name.strip(), normalized_description


def create_playlist(name, description, session):
    with mutation(session):
        name, description = playlist_values(name, description)
        playlist = Playlist(name=name, description=description, active=True)
        session.add(playlist)
        session.flush()
        return playlist.id


def update_playlist(playlist_id, name, description, session):
    with mutation(session):
        playlist = find_playlist(playlist_id, session)
        playlist.name, playlist.description = playlist_values(name, description)
        playlist.updated_at = utc_now()


def has_assignments(playlist_id, session):
    return session.scalar(select(ScreenPlaylistAssignment.screen_id)
                          .where(ScreenPlaylistAssignment.playlist_id == playlist_id).limit(1)) is not None


def toggle_playlist(playlist_id, session):
    with mutation(session):
        playlist = find_playlist(playlist_id, session)
        if playlist.active and has_assignments(playlist.id, session):
            raise PlaylistError("Desvincule todas as telas antes de desativar a playlist.", 409)
        playlist.active = not playlist.active
        playlist.updated_at = utc_now()


def image_duration(value):
    if value is None or (isinstance(value, str) and not value.strip()):
        return 15
    if isinstance(value, str) and re.fullmatch(r"[0-9]{1,10}", value.strip()):
        value = int(value.strip())
    if type(value) is not int or not 5 <= value <= 600:
        raise PlaylistError("A duração da imagem deve ser um inteiro entre 5 e 600 segundos.")
    return value


def add_item(playlist_id, media_id, duration_seconds, session):
    with mutation(session):
        playlist = find_playlist(playlist_id, session)
        asset = session.get(MediaAsset, identifier(media_id, "Identificador da mídia", 422))
        if asset is None:
            raise PlaylistError("Mídia não encontrada.", 404)
        count = session.scalar(select(func.count()).select_from(PlaylistItem).where(PlaylistItem.playlist_id == playlist.id))
        if count >= MAX_ITEMS:
            raise PlaylistError("A playlist admite no máximo 100 itens, incluindo repetições.", 409)
        if asset.kind == "video":
            if duration_seconds is not None:
                raise PlaylistError("Vídeos usam reprodução integral; não envie duração.")
            duration = None
        else:
            duration = image_duration(duration_seconds)
        item = PlaylistItem(playlist_id=playlist.id, media_id=asset.id, position=count + 1, duration_seconds=duration)
        session.add(item)
        playlist.updated_at = utc_now()
        session.flush()
        return item.id


def remove_item(playlist_id, item_id, session):
    with mutation(session):
        playlist = find_playlist(playlist_id, session)
        item = find_item(playlist.id, item_id, session)
        count = session.scalar(select(func.count()).select_from(PlaylistItem).where(PlaylistItem.playlist_id == playlist.id))
        if count == 1 and has_assignments(playlist.id, session):
            raise PlaylistError("Não é possível remover o último item de uma playlist associada.", 409)
        position = item.position
        session.delete(item)
        session.flush()
        # O espaço livre avança do menor para o maior; cada flush evita que
        # a ordem dos UPDATEs dependa do id/ordem interna da unidade de trabalho.
        following = session.scalars(select(PlaylistItem).where(PlaylistItem.playlist_id == playlist.id,
                                                               PlaylistItem.position > position)
                                    .order_by(PlaylistItem.position, PlaylistItem.id)).all()
        for successor in following:
            successor.position -= 1
            session.flush()
        playlist.updated_at = utc_now()


def move_item(playlist_id, item_id, direction, session):
    with mutation(session):
        playlist = find_playlist(playlist_id, session)
        item = find_item(playlist.id, item_id, session)
        if direction not in (-1, 1) or type(direction) is not int:
            raise PlaylistError("Movimento inválido.")
        neighbor = session.scalar(select(PlaylistItem).where(PlaylistItem.playlist_id == playlist.id,
                                                              PlaylistItem.position == item.position + direction))
        if neighbor is None:
            return  # Limite da lista: sucesso sem alterar posições ou timestamps.
        previous, target = item.position, neighbor.position
        maximum = session.scalar(select(func.max(PlaylistItem.position)).where(PlaylistItem.playlist_id == playlist.id))
        item.position = maximum + 1
        session.flush()
        neighbor.position = previous
        session.flush()
        item.position = target
        session.flush()
        playlist.updated_at = utc_now()


def assign_playlist(screen_id, playlist_id, session):
    with mutation(session):
        screen = find_screen(screen_id, session)
        playlist_id = identifier(playlist_id, "Identificador da playlist", 422)
        playlist = find_playlist(playlist_id, session)
        has_items = session.scalar(select(PlaylistItem.id).where(PlaylistItem.playlist_id == playlist.id).limit(1))
        if not playlist.active or has_items is None:
            raise PlaylistError("Escolha uma playlist ativa e com pelo menos um item.", 409)
        assignment = session.get(ScreenPlaylistAssignment, screen.id)
        if assignment is None:
            session.add(ScreenPlaylistAssignment(screen_id=screen.id, playlist_id=playlist.id))
        elif assignment.playlist_id != playlist.id:
            assignment.playlist_id = playlist.id
            assignment.updated_at = utc_now()


def unassign_playlist(screen_id, session):
    with mutation(session):
        screen = find_screen(screen_id, session)
        assignment = session.get(ScreenPlaylistAssignment, screen.id)
        if assignment is not None:
            session.delete(assignment)
