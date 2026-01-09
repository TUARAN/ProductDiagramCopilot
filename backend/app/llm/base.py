from __future__ import annotations

from typing import Protocol

from app.llm.types import LLMChatRequest, LLMChatResponse


class LLMProvider(Protocol):
    name: str

    async def chat(self, req: LLMChatRequest) -> LLMChatResponse: ...
