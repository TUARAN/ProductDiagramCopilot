from __future__ import annotations

import json

from app.generator.diagram import DiagramGenerateRequest, DiagramGenerateResponse
from app.generator.integration import IntegrationGenerateRequest, IntegrationGenerateResponse
from app.generator.spec import FlowSpec, SequenceSpec, StateSpec
from app.llm.factory import get_provider
from app.llm.prompts import diagram_prompt, integration_prompt
from app.llm.types import LLMChatRequest
from app.renderer.mermaid import render_flow, render_sequence, render_state


def _parse_json_maybe(text: str) -> dict:
    # Best-effort parse: model might include code fences; strip them.
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        # Some models prefix language, e.g. ```json
        t = t.split("\n", 1)[-1]
    t = t.strip()
    return json.loads(t)


def generate_diagram(req: DiagramGenerateRequest) -> DiagramGenerateResponse:
    provider = get_provider()
    messages = diagram_prompt(req.diagram_type, req.text, req.scene)

    # Run provider in sync FastAPI handler (simple MVP). If later need perf, switch to async routes.
    import anyio

    async def _run():
        return await provider.chat(LLMChatRequest(messages=messages))

    resp = anyio.run(_run)
    spec_obj = _parse_json_maybe(resp.content)

    t = spec_obj.get("type")
    mermaid = ""
    if t == "flow":
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
