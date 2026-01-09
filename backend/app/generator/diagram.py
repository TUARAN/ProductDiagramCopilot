from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


DiagramType = Literal["flow", "sequence", "state"]


class DiagramGenerateRequest(BaseModel):
    diagram_type: DiagramType = Field(description="flow | sequence | state")
    text: str
    scene: Optional[str] = None


class DiagramGenerateResponse(BaseModel):
    spec: dict[str, Any]
    mermaid: str
