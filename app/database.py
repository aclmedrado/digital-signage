from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


def make_engine(url):
    engine = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            if cursor.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
                raise RuntimeError("SQLite deve aplicar as chaves estrangeiras.")
        finally:
            cursor.close()

    return engine


engine = make_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def get_session():
    with SessionLocal() as session:
        yield session
