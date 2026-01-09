from __future__ import annotations

import httpx

from app.core.settings import settings
from app.llm.base import LLMProvider
from app.llm.types import LLMChatRequest, LLMChatResponse


class OllamaProvider:
    name = "ollama"

    async def chat(self, req: LLMChatRequest) -> LLMChatResponse:
        url = settings.OLLAMA_BASE_URL.rstrip("/") + "/api/chat"
        payload = {
            "model": settings.OLLAMA_MODEL,
            "messages": [m.model_dump() for m in req.messages],
            "stream": False,
            "options": {
                "temperature": req.temperature,
                # Ollama doesn't use max_tokens universally; keep it best-effort.
            },
        }

        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()

        content = data.get("message", {}).get("content", "")
        return LLMChatResponse(content=content, raw=data)


def provider() -> LLMProvider:
    return OllamaProvider()
