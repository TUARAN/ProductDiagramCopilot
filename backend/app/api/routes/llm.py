from __future__ import annotations

import time
from typing import Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.settings import settings
from app.llm.factory import get_provider
from app.llm.types import ChatMessage, LLMChatRequest

router = APIRouter()


class LlmConfigOut(BaseModel):
    mode: str
    provider: str
    model: Optional[str] = None
    base_url: Optional[str] = None


class LlmConfigIn(BaseModel):
    mode: Literal["openai_compat", "ollama"] = Field(..., description="LLM mode to use")
    ollama_base_url: Optional[str] = Field(None, description="Override OLLAMA_BASE_URL when mode=ollama")
    ollama_model: Optional[str] = Field(None, description="Override OLLAMA_MODEL when mode=ollama")


def _current_llm_config() -> LlmConfigOut:
    provider = get_provider()
    mode = settings.LLM_MODE

    if mode == "openai_compat":
        model = settings.OPENAI_COMPAT_MODEL or None
        base_url = settings.OPENAI_COMPAT_BASE_URL or None
    else:  # ollama
        model = settings.OLLAMA_MODEL or None
        base_url = settings.OLLAMA_BASE_URL or None

    return LlmConfigOut(
        mode=mode,
        provider=getattr(provider, "name", provider.__class__.__name__),
        model=model,
        base_url=base_url,
    )


@router.get("/config")
async def llm_get_config() -> LlmConfigOut:
    """Return current LLM runtime config.

    Notes:
    - Does not return any secrets (e.g. API keys).
    - This is process-local; if you run multiple backend processes, each has its own setting.
    """

    return _current_llm_config()


@router.post("/config")
async def llm_set_config(body: LlmConfigIn) -> LlmConfigOut:
    """Update current LLM runtime config.

    This updates the in-memory Settings instance so it takes effect immediately.
    """

    settings.LLM_MODE = body.mode

    if body.mode == "ollama":
        if body.ollama_base_url:
            settings.OLLAMA_BASE_URL = body.ollama_base_url
        if body.ollama_model:
            settings.OLLAMA_MODEL = body.ollama_model

    return _current_llm_config()


@router.get("/ping")
async def llm_ping() -> dict:
    """Lightweight connectivity check for the configured LLM provider.

    - Does not return any secrets.
    - Intended for quick smoke tests and debugging env configuration.
    """

    provider = get_provider()

    started = time.time()
    req = LLMChatRequest(
        messages=[
            ChatMessage(role="system", content="You are a helpful assistant."),
            ChatMessage(role="user", content="Reply with exactly: pong"),
        ],
        temperature=0.0,
        max_tokens=16,
    )

    try:
        resp = await provider.chat(req)
        elapsed_ms = int((time.time() - started) * 1000)
        text = (resp.content or "").strip()
        ok = text.lower().startswith("pong")

        return {
            "ok": ok,
            "provider": getattr(provider, "name", provider.__class__.__name__),
            "mode": settings.LLM_MODE,
            "model": settings.OPENAI_COMPAT_MODEL if settings.LLM_MODE == "openai_compat" else settings.OLLAMA_MODEL,
            "base_url": settings.OPENAI_COMPAT_BASE_URL if settings.LLM_MODE == "openai_compat" else settings.OLLAMA_BASE_URL,
            "latency_ms": elapsed_ms,
            "text": text[:200],
        }
    except Exception as e:
        elapsed_ms = int((time.time() - started) * 1000)
        return {
            "ok": False,
            "provider": getattr(provider, "name", provider.__class__.__name__),
            "mode": settings.LLM_MODE,
            "latency_ms": elapsed_ms,
            "error": str(e),
        }
