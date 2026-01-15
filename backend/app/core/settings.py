from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    DATABASE_URL: str = "postgresql+psycopg://pdc:pdc@localhost:5432/pdc"

    REDIS_URL: str = "redis://localhost:6379/0"

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minio"
    MINIO_SECRET_KEY: str = "minio123456"
    MINIO_SECURE: bool = False
    MINIO_BUCKET: str = "pdc"

    LLM_MODE: str = "mock"  # mock | openai_compat | ollama

    TASK_MODE: str = "inproc"  # inproc | celery

    OPENAI_COMPAT_BASE_URL: str = ""
    OPENAI_COMPAT_API_KEY: str = ""
    OPENAI_COMPAT_MODEL: str = ""
    # chat_completions | responses
    OPENAI_COMPAT_API_STYLE: str = "chat_completions"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"


settings = Settings()
