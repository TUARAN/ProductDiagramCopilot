from __future__ import annotations

from typing import Literal
from typing import Optional

from pydantic import BaseModel, Field


class FlowNode(BaseModel):
    id: str
    label: str


class FlowEdge(BaseModel):
    from_: str = Field(alias="from")
    to: str
    label: Optional[str] = None


class FlowSpec(BaseModel):
    type: Literal["flow"]
    direction: str = "TD"
    nodes: list[FlowNode]
    edges: list[FlowEdge]
    note: Optional[str] = None


class SequenceMessage(BaseModel):
    from_: str = Field(alias="from")
    to: str
    label: str


class SequenceSpec(BaseModel):
    type: Literal["sequence"]
    participants: list[str]
    messages: list[SequenceMessage]
    note: Optional[str] = None


class StateTransition(BaseModel):
    from_: str = Field(alias="from")
    to: str
    label: Optional[str] = None


class StateSpec(BaseModel):
    type: Literal["state"]
    states: list[str]
    transitions: list[StateTransition]
    note: Optional[str] = None
