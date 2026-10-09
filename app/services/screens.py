from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Screen, utc_now


def find_screen(screen_id, session):
    screen = session.get(Screen, screen_id)
    if screen is None:
        raise HTTPException(status_code=404, detail="Tela não encontrada")
    return screen


def list_screens(session):
    return session.scalars(select(Screen).order_by(Screen.id)).all()


def save(screen, session):
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Slug já cadastrado") from None
    session.refresh(screen)
    return screen


def create_screen(data, session):
    screen = Screen(**data.model_dump())
    session.add(screen)
    return save(screen, session)


def update_screen(screen, data, session):
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(screen, field, value)
    screen.updated_at = utc_now()
    return save(screen, session)
