from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.settings import settings
from app.models.base import Base


_connect_args = None
if settings.DATABASE_URL.startswith("sqlite:"):
    # FastAPI runs handlers in a threadpool; SQLite needs this for multi-thread access.
    _connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, connect_args=_connect_args or {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


if getattr(settings, "AUTO_CREATE_DB", False):
    # Desktop packaging path: create tables on first run.
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
