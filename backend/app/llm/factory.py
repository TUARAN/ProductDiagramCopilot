from __future__ import annotations

from app.core.settings import settings
from app.llm.base import LLMProvider


def get_provider() -> LLMProvider:
    mode = (settings.LLM_MODE or "ollama").lower()

    if mode == "openai_compat":
        from app.llm.openai_compat import provider

        return provider()

    if mode == "ollama":
        from app.llm.ollama import provider

        return provider()

    raise ValueError(f"Unsupported LLM_MODE: {settings.LLM_MODE}. Supported: ollama | openai_compat")
