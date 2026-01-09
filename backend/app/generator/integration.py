from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel


class IntegrationGenerateRequest(BaseModel):
    text: str
    swagger_text: Optional[str] = None


class IntegrationGenerateResponse(BaseModel):
    markdown: str
    spec: Optional[Dict[str, Any]] = None
