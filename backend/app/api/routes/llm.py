from __future__ import annotations

import time

from fastapi import APIRouter

from app.core.settings import settings
from app.llm.factory import get_provider
from app.llm.types import ChatMessage, LLMChatRequest

router = APIRouter()


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
