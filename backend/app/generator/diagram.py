from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


DiagramType = Literal["flow", "sequence", "state", "cmic_report"]


class DiagramGenerateRequest(BaseModel):
    diagram_type: DiagramType = Field(description="flow | sequence | state | cmic_report")
    text: str
    scene: Optional[str] = None


class DiagramGenerateResponse(BaseModel):
    spec: dict[str, Any]
    mermaid: str
