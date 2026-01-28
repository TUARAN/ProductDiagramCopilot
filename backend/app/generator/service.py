from __future__ import annotations

import json
import re

from typing import Optional

from pydantic import ValidationError

from app.generator.diagram import DiagramGenerateRequest, DiagramGenerateResponse
from app.generator.integration import IntegrationGenerateRequest, IntegrationGenerateResponse
from app.generator.spec import CmicReportSpec, FlowSpec, SequenceSpec, StateSpec
from app.llm.factory import get_provider
from app.llm.prompts import diagram_prompt, integration_prompt
from app.llm.types import LLMChatRequest
from app.renderer.mermaid import render_cmic_report, render_flow, render_sequence, render_state


def _extract_first_json_object(text: str) -> Optional[str]:
    start = text.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    return None


def _parse_json_maybe(text: str) -> dict:
    # Best-effort parse: models sometimes wrap JSON in markdown fences or add extra prose.
    t = (text or "").strip()
    try:
        return json.loads(t)
    except Exception:
        pass

    candidate = _extract_first_json_object(t)
    if not candidate:
        raise ValueError("LLM output does not contain a JSON object")

    return json.loads(candidate)


def _coerce_spec_type(spec_obj: dict, req_type: str) -> str:
    t = (spec_obj.get("type") or spec_obj.get("diagram_type") or req_type or "").strip().lower()
    if not t:
        raise ValueError("Spec is missing required field: type")
    spec_obj["type"] = t
    return t


def _fallback_flow_spec_from_text(text: str) -> dict:
    raw = (text or "").strip()
    if not raw:
        return {
            "type": "flow",
            "direction": "TD",
            "nodes": [{"id": "n1", "label": "开始"}, {"id": "n2", "label": "结束"}],
            "edges": [{"from": "n1", "to": "n2", "label": ""}],
        }

    parts = re.split(r"\s*(?:->|→|⇒|=>)\s*", raw)
    steps = [p.strip() for p in parts if p and p.strip()]
    if len(steps) == 1:
        steps = ["开始", steps[0], "结束"]

    nodes = [{"id": f"n{i+1}", "label": label} for i, label in enumerate(steps)]
    edges = [
        {"from": f"n{i+1}", "to": f"n{i+2}", "label": ""}
        for i in range(len(steps) - 1)
    ]

    return {
        "type": "flow",
        "direction": "TD",
        "nodes": nodes,
        "edges": edges,
    }


def generate_diagram(req: DiagramGenerateRequest) -> DiagramGenerateResponse:
    provider = get_provider()
    messages = diagram_prompt(req.diagram_type, req.text, req.scene)

    # Run provider in sync FastAPI handler (simple MVP). If later need perf, switch to async routes.
    import anyio

    async def _run():
        return await provider.chat(LLMChatRequest(messages=messages))

    resp = anyio.run(_run)
    spec_obj = _parse_json_maybe(resp.content)

    if not isinstance(spec_obj, dict):
        raise ValueError("LLM output JSON must be an object")

    t = _coerce_spec_type(spec_obj, req.diagram_type)
    mermaid = ""
    if t == "flow":
        try:
            spec = FlowSpec.model_validate(spec_obj)
        except ValidationError:
            # Some models (esp. local) may echo the input JSON without producing nodes/edges.
            # In that case, fall back to a deterministic flow derived from the user's text.
            spec_obj = _fallback_flow_spec_from_text(req.text)
            spec = FlowSpec.model_validate(spec_obj)
        mermaid = render_flow(spec)
    elif t == "sequence":
        spec = SequenceSpec.model_validate(spec_obj)
        mermaid = render_sequence(spec)
    elif t == "state":
        spec = StateSpec.model_validate(spec_obj)
        mermaid = render_state(spec)
    elif t == "cmic_report":
        # Fixed structure template + LLM-filled placeholders.
        spec = CmicReportSpec.model_validate(spec_obj)
        mermaid = render_cmic_report(spec)
    else:
        raise ValueError(f"Unsupported spec.type: {t}")

    return DiagramGenerateResponse(spec=spec_obj, mermaid=mermaid)


def generate_integration_plan(req: IntegrationGenerateRequest) -> IntegrationGenerateResponse:
    provider = get_provider()
    messages = integration_prompt(req.text, req.swagger_text)

    import anyio

    async def _run():
        return await provider.chat(LLMChatRequest(messages=messages, max_tokens=2048))

    resp = anyio.run(_run)
    return IntegrationGenerateResponse(markdown=resp.content)
