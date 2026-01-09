from __future__ import annotations

import httpx

from app.core.settings import settings
from app.llm.base import LLMProvider
from app.llm.types import LLMChatRequest, LLMChatResponse


class OpenAICompatProvider:
    name = "openai_compat"

    def __init__(self) -> None:
        if not settings.OPENAI_COMPAT_BASE_URL:
            raise ValueError("OPENAI_COMPAT_BASE_URL is required")
        if not settings.OPENAI_COMPAT_API_KEY:
            raise ValueError("OPENAI_COMPAT_API_KEY is required")
        if not settings.OPENAI_COMPAT_MODEL:
            raise ValueError("OPENAI_COMPAT_MODEL is required")

    async def chat(self, req: LLMChatRequest) -> LLMChatResponse:
        style = (settings.OPENAI_COMPAT_API_STYLE or "chat_completions").strip().lower()
        headers = {"Authorization": f"Bearer {settings.OPENAI_COMPAT_API_KEY}"}

        if style == "responses":
            url = _build_v1_url("/responses")
            payload = {
                "model": settings.OPENAI_COMPAT_MODEL,
                "input": [
                    {
                        "role": m.role,
                        "content": [{"type": "input_text", "text": m.content}],
                    }
                    for m in req.messages
                ],
                # OpenAI Responses API uses max_output_tokens.
                "max_output_tokens": req.max_tokens,
                "temperature": req.temperature,
            }
        else:
            url = _build_v1_url("/chat/completions")
            payload = {
                "model": settings.OPENAI_COMPAT_MODEL,
                "messages": [m.model_dump() for m in req.messages],
                "temperature": req.temperature,
                "max_tokens": req.max_tokens,
            }

        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, json=payload, headers=headers)
            if not r.is_success:
                body = (r.text or "").strip()
                if len(body) > 1200:
                    body = body[:1200] + "…"
                raise RuntimeError(f"LLM gateway error HTTP {r.status_code}: {body}")
            data = r.json()

        if style == "responses":
            content = _extract_responses_text(data)
        else:
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return LLMChatResponse(content=content, raw=data)


def _build_v1_url(path: str) -> str:
    base = settings.OPENAI_COMPAT_BASE_URL.rstrip("/")
    # Accept either https://host or https://host/v1
    if base.endswith("/v1"):
        return base + path
    return base + "/v1" + path


def _extract_responses_text(data: dict) -> str:
    # Some gateways return a convenience field.
    if isinstance(data.get("output_text"), str) and data.get("output_text"):
        return data.get("output_text")

    output = data.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                text = part.get("text")
                if isinstance(text, str) and text:
                    return text
    return ""


def provider() -> LLMProvider:
    return OpenAICompatProvider()
