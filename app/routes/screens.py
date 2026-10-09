from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_session
from app.schemas import ScreenCreate, ScreenRead, ScreenUpdate
from app.services import screens

router = APIRouter(prefix="/api/screens")


@router.post("", response_model=ScreenRead, status_code=201)
def create_screen(data: ScreenCreate, session: Session = Depends(get_session)):
    return screens.create_screen(data, session)


@router.get("", response_model=list[ScreenRead])
def list_screens(session: Session = Depends(get_session)):
    return screens.list_screens(session)


@router.get("/{screen_id}", response_model=ScreenRead)
def read_screen(screen_id: int, session: Session = Depends(get_session)):
    return screens.find_screen(screen_id, session)


@router.patch("/{screen_id}", response_model=ScreenRead)
def update_screen(screen_id: int, data: ScreenUpdate, session: Session = Depends(get_session)):
    screen = screens.find_screen(screen_id, session)
    return screens.update_screen(screen, data, session)
