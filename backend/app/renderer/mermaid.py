from __future__ import annotations

import re

from app.generator.spec import FlowSpec, SequenceSpec, StateSpec


_FLOW_RESERVED_IDS = {
    # Mermaid keywords / directives that can break parsing when used as node ids.
    "end",
    "subgraph",
    "flowchart",
    "graph",
    "direction",
    "class",
    "classdef",
    "click",
    "style",
    "linkstyle",
}


def _safe_flow_id(raw: str, used: set[str]) -> str:
    s = (raw or "").strip()
    s = re.sub(r"[^0-9A-Za-z_]", "_", s)
    if not s:
        s = "node"
    if s[0].isdigit():
        s = f"n_{s}"

    if s.lower() in _FLOW_RESERVED_IDS:
        s = f"n_{s}"

    candidate = s
    i = 2
    while candidate in used:
        candidate = f"{s}_{i}"
        i += 1
    used.add(candidate)
    return candidate


def render_flow(spec: FlowSpec) -> str:
    lines: list[str] = []
    direction = spec.direction or "TD"
    lines.append(f"flowchart {direction}")

    used: set[str] = set()
    id_map: dict[str, str] = {}

    for n in spec.nodes:
        if n.id not in id_map:
            id_map[n.id] = _safe_flow_id(n.id, used)

    for n in spec.nodes:
        safe_label = n.label.replace("\n", " ")
        nid = id_map.get(n.id) or _safe_flow_id(n.id, used)
        id_map[n.id] = nid
        lines.append(f"  {nid}[\"{safe_label}\"]")

    for e in spec.edges:
        from_id = id_map.get(e.from_)
        if not from_id:
            from_id = _safe_flow_id(e.from_, used)
            id_map[e.from_] = from_id

        to_id = id_map.get(e.to)
        if not to_id:
            to_id = _safe_flow_id(e.to, used)
            id_map[e.to] = to_id

        label = (e.label or "").strip()
        if label:
            lines.append(f"  {from_id} -->|{label}| {to_id}")
        else:
            lines.append(f"  {from_id} --> {to_id}")

    return "\n".join(lines)


def render_sequence(spec: SequenceSpec) -> str:
    lines: list[str] = ["sequenceDiagram"]

    for p in spec.participants:
        lines.append(f"  participant {p}")

    for m in spec.messages:
        lines.append(f"  {m.from_}->>{m.to}: {m.label}")

    if spec.note:
        lines.append(f"  Note over {spec.participants[0]},{spec.participants[-1]}: {spec.note}")

    return "\n".join(lines)


def render_state(spec: StateSpec) -> str:
    lines: list[str] = ["stateDiagram-v2"]

    # Mermaid stateDiagram doesn't require explicit state declarations, but adding improves readability.
    for s in spec.states:
        lines.append(f"  state {s}")

    for t in spec.transitions:
        label = (t.label or "").strip()
        if label:
            lines.append(f"  {t.from_} --> {t.to}: {label}")
        else:
            lines.append(f"  {t.from_} --> {t.to}")

    return "\n".join(lines)
