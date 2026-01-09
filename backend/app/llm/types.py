from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Role = Literal["system", "user", "assistant"]


class ChatMessage(BaseModel):
    role: Role
    content: str


class LLMChatRequest(BaseModel):
    messages: list[ChatMessage]
    temperature: float = 0.2
    max_tokens: int = 2048


class LLMChatResponse(BaseModel):
    content: str
    raw: dict = Field(default_factory=dict)
