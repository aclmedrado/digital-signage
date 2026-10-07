from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import Screen, utc_now
from app.schemas import ScreenCreate, ScreenRead, ScreenUpdate

router = APIRouter(prefix="/api/screens")


def find_screen(screen_id, session):
    screen = session.get(Screen, screen_id)
    if screen is None:
        raise HTTPException(status_code=404, detail="Tela não encontrada")
    return screen


def save(screen, session):
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Slug já cadastrado") from None
    session.refresh(screen)
    return screen


@router.post("", response_model=ScreenRead, status_code=201)
def create_screen(data: ScreenCreate, session: Session = Depends(get_session)):
    screen = Screen(**data.model_dump())
    session.add(screen)
    return save(screen, session)


@router.get("", response_model=list[ScreenRead])
def list_screens(session: Session = Depends(get_session)):
    return session.scalars(select(Screen).order_by(Screen.id)).all()


@router.get("/{screen_id}", response_model=ScreenRead)
def read_screen(screen_id: int, session: Session = Depends(get_session)):
    return find_screen(screen_id, session)


@router.patch("/{screen_id}", response_model=ScreenRead)
def update_screen(screen_id: int, data: ScreenUpdate, session: Session = Depends(get_session)):
    screen = find_screen(screen_id, session)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(screen, field, value)
    screen.updated_at = utc_now()
    return save(screen, session)
