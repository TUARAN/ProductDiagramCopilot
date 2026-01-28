from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET

from typing import Optional

from pydantic import ValidationError

from app.generator.diagram import (
    DiagramGenerateRequest,
    DiagramGenerateResponse,
    DrawioXmlGenerateRequest,
    DrawioXmlGenerateResponse,
)
from app.generator.integration import IntegrationGenerateRequest, IntegrationGenerateResponse
from app.generator.spec import FlowSpec, SequenceSpec, StateSpec
from app.llm.factory import get_provider
from app.llm.prompts import diagram_prompt, drawio_xml_prompt, integration_prompt
from app.llm.types import LLMChatRequest
from app.renderer.mermaid import render_flow, render_sequence, render_state


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


def _extract_first_mxfile_xml(text: str) -> Optional[str]:
    """Extract first <mxfile>...</mxfile> block from a possibly wrapped LLM response."""

    t = (text or "").strip()
    if not t:
        return None

    start = t.find("<mxfile")
    if start < 0:
        return None
    end = t.find("</mxfile>", start)
    if end < 0:
        return None
    end += len("</mxfile>")
    return t[start:end].strip()


def _validate_mxfile_xml(xml: str) -> None:
    x = (xml or "").strip()
    if not x:
        raise ValueError("draw.io XML 为空")
    if len(x) > 400_000:
        raise ValueError("draw.io XML 过大")

    try:
        root = ET.fromstring(x)
    except Exception as e:
        raise ValueError(f"draw.io XML 解析失败: {e}")

    if root.tag != "mxfile":
        raise ValueError("draw.io XML 根节点必须是 mxfile")
    if not list(root.findall("diagram")):
        raise ValueError("draw.io XML 必须包含 diagram")


_FALLBACK_MXFILE_XML = (
    '<mxfile host="app.diagrams.net" modified="2026-01-28T00:00:00.000Z" agent="ProductDiagramCopilot" version="22.1.0">'
    '<diagram id="generated" name="Generated">'
    '<mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1600" pageHeight="900" math="0" shadow="0">'
    '<root><mxCell id="0"/><mxCell id="1" parent="0"/>'
    '<mxCell id="t1" value="通用系统架构（待完善）" style="text;html=1;align=center;verticalAlign=middle;fontSize=22;fontStyle=1;" vertex="1" parent="1">'
    '<mxGeometry x="420" y="20" width="760" height="40" as="geometry"/></mxCell>'
    '<mxCell id="n1" value="待确认：请补充系统角色/模块/数据存储/调用链路" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#666666;" vertex="1" parent="1">'
    '<mxGeometry x="300" y="140" width="1000" height="120" as="geometry"/></mxCell>'
    '</root></mxGraphModel></diagram></mxfile>'
)


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


def generate_drawio_xml(req: DrawioXmlGenerateRequest) -> DrawioXmlGenerateResponse:
    text = (req.text or "").strip()
    if not text:
        raise ValueError("text 不能为空")

    provider = get_provider()
    messages = drawio_xml_prompt(text)

    import anyio

    async def _run():
        # XML may be longer than JSON specs.
        return await provider.chat(LLMChatRequest(messages=messages, max_tokens=4096))

    resp = anyio.run(_run)
    raw = (resp.content or "").strip()
    xml = _extract_first_mxfile_xml(raw)
    if not xml:
        # Some providers may ignore instructions; keep UX functional.
        xml = _FALLBACK_MXFILE_XML

    _validate_mxfile_xml(xml)
    return DrawioXmlGenerateResponse(xml=xml)
