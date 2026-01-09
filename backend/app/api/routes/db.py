from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import SQLAlchemyError

from app.core.db import engine
from app.core.settings import settings

router = APIRouter()


class DbPingResponse(BaseModel):
    ok: bool
    dialect: str
    driver: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    latency_ms: Optional[int] = None
    error: Optional[str] = None


@router.get("/ping", response_model=DbPingResponse)
def db_ping() -> DbPingResponse:
    url = make_url(settings.DATABASE_URL)
    started = time.perf_counter()
    try:
        with engine.connect() as conn:
            conn.execute(text("select 1"))
        latency_ms = int((time.perf_counter() - started) * 1000)
        return DbPingResponse(
            ok=True,
            dialect=url.get_backend_name(),
            driver=url.get_driver_name() or None,
            host=url.host,
            port=url.port,
            database=url.database,
            latency_ms=latency_ms,
        )
    except SQLAlchemyError as e:
        return DbPingResponse(
            ok=False,
            dialect=url.get_backend_name(),
            driver=url.get_driver_name() or None,
            host=url.host,
            port=url.port,
            database=url.database,
            error=str(e.__class__.__name__),
        )
