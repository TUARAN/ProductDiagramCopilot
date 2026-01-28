from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _desktop_data_dir() -> str:
    return os.getenv("PDC_DATA_DIR", "").strip()


def _default_database_url() -> str:
    data_dir = _desktop_data_dir()
    if data_dir:
        db_path = Path(data_dir) / "pdc.sqlite3"
        return f"sqlite:///{db_path}"
    return "postgresql+psycopg://pdc:pdc@localhost:5432/pdc"


def _default_storage_mode() -> str:
    return "local" if _desktop_data_dir() else "minio"


def _default_local_storage_dir() -> str:
    data_dir = _desktop_data_dir()
    return str(Path(data_dir) / "storage") if data_dir else ""


def _default_auto_create_db() -> bool:
    # Desktop package uses SQLite and should auto-create tables on first run.
    return bool(_desktop_data_dir())


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Product Diagram Copilot"

    CORS_ALLOW_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://tauri.localhost",
        "https://tauri.localhost",
        "tauri://localhost",
    ]

    # Provided by Tauri sidecar at runtime for desktop packaging.
    # Example: /Users/<you>/Library/Application Support/<App>/
    PDC_DATA_DIR: str = ""

    DATABASE_URL: str = Field(default_factory=_default_database_url)

    AUTO_CREATE_DB: bool = Field(default_factory=_default_auto_create_db)

    REDIS_URL: str = "redis://localhost:6379/0"

    STORAGE_MODE: str = Field(default_factory=_default_storage_mode)  # minio | local

    # Local storage (desktop) writes object payloads to disk.
    LOCAL_STORAGE_DIR: str = Field(default_factory=_default_local_storage_dir)

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minio"
    MINIO_SECRET_KEY: str = "minio123456"
    MINIO_SECURE: bool = False
    MINIO_BUCKET: str = "pdc"

    LLM_MODE: str = "ollama"  # ollama | openai_compat

    TASK_MODE: str = "inproc"  # inproc | celery

    OPENAI_COMPAT_BASE_URL: str = ""
    OPENAI_COMPAT_API_KEY: str = ""
    OPENAI_COMPAT_MODEL: str = ""
    # chat_completions | responses
    OPENAI_COMPAT_API_STYLE: str = "chat_completions"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:1b"


settings = Settings()
