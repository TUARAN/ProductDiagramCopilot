from __future__ import annotations

import re

from app.generator.spec import CmicReportSpec, FlowSpec, SequenceSpec, StateSpec


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


def _limit_items(items: list[str], max_items: int) -> list[str]:
    out: list[str] = []
    for it in items or []:
        s = (it or "").strip()
        if not s:
            continue
        out.append(s)
        if len(out) >= max_items:
            break
    return out


def render_cmic_report(spec: CmicReportSpec) -> str:
    # Mermaid can't perfectly match PPT's nested rounded rectangles,
    # but we approximate via layered subgraphs + styled nodes.
    # Structure is fixed; text is filled from `spec`.
    lines: list[str] = []

    # Keep labels plain-text so this renders under Mermaid's `securityLevel: strict`
    # (frontend uses strict). We use `\\n` sequences for line breaks.
    lines.append('%%{init: {"flowchart": {"curve": "linear"}} }%%')
    lines.append("flowchart TB")
    lines.append("")

    # Palette (fresh blue-green) + typography approximations.
    # Note: Mermaid themeVariables are global; node classDefs are used for most styling.
    lines.append("%% --- CMIC Report Diagram Styles ---")
    # Fresh blue-green palette
    lines.append("classDef cmic_outer fill:#EFF9F7,stroke:#2FA7A0,stroke-width:2px,color:#0B1F2A;")
    lines.append("classDef cmic_layer fill:#E3F4F1,stroke:#2FA7A0,stroke-width:1.5px,color:#0B1F2A;")
    # Title bar
    lines.append("classDef cmic_title fill:#0E3A63,stroke:#0E3A63,stroke-width:1px,color:#FFFFFF;")
    # Body
    lines.append("classDef cmic_body fill:#FFFFFF,stroke:#2FA7A0,stroke-width:1px,color:#22303A;")
    # Pills
    lines.append("classDef cmic_pill fill:#0E3A63,stroke:#0E3A63,stroke-width:1px,color:#FFFFFF;")
    # Separator anchor
    lines.append("classDef cmic_sep fill:transparent,stroke:#B6C2CC,stroke-width:1px,color:transparent;")
    lines.append("")

    # Outer frame (acts as the big rounded rectangle background).
    title = (spec.title or "智能体平台总体架构图").strip() or "智能体平台总体架构图"
    lines.append(f'subgraph CMIC["{title}"]')
    lines.append("  direction TB")
    lines.append("")

    # Layer 1: Application Layer
    app_items = _limit_items(spec.application_agents, 8)
    if not app_items:
        app_items = ["用户交互型智能体", "场景任务型智能体", "安全与治理型智能体", "可扩展入口"]

    lines.append('  subgraph L1["1️⃣ 应用层（Application Layer）"]')
    lines.append("    direction TB")
    lines.append('    L1T["应用层智能体入口"]:::cmic_title')
    lines.append("    subgraph L1G[\" \"]")
    lines.append("      direction LR")
    for i, it in enumerate(app_items, start=1):
        lines.append(f'      APP_{i}["{it}"]:::cmic_body')
    lines.append("    end")
    lines.append("  end")
    lines.append("")

    lines.append('  SEP1[" "]:::cmic_sep')
    lines.append("  L1T -.-> SEP1")
    lines.append("")

    # Layer 2: Agent Service Layer
    plat_labels = _limit_items(spec.platform_labels, 5)
    if not plat_labels:
        plat_labels = ["消息智能体平台", "行业智能体平台", "企业 AI 中台", "智能体协同操作系统"]

    svc_items = _limit_items(spec.agent_service_capabilities, 10)
    if not svc_items:
        svc_items = [
            "多智能体协同与编排",
            "认知与决策引擎",
            "领域知识与知识体系",
            "多模型接入与调度",
            "通用智能组件能力池",
            "用户画像与标签",
        ]

    lines.append('  subgraph L2["2️⃣ 智能体服务层（Agent Service Layer）"]')
    lines.append("    direction TB")
    lines.append('    L2T["平台能力中枢"]:::cmic_title')
    lines.append("    subgraph L2P[\" \"]")
    lines.append("      direction LR")
    for i, it in enumerate(plat_labels, start=1):
        lines.append(f'      PLAT_{i}["{it}"]:::cmic_pill')
    lines.append("    end")
    lines.append("    subgraph L2G[\" \"]")
    lines.append("      direction LR")
    for i, it in enumerate(svc_items, start=1):
        lines.append(f'      SVC_{i}["{it}"]:::cmic_body')
    lines.append("    end")
    lines.append("  end")
    lines.append("")

    lines.append('  SEP2[" "]:::cmic_sep')
    lines.append("  L2T -.-> SEP2")
    lines.append("")

    # Layer 3: Orchestration Layer
    orch_items = _limit_items(spec.orchestration_capabilities, 6)
    if not orch_items:
        orch_items = ["请求路由与策略调度", "业务系统接入适配", "消息/事件驱动", "生态与第三方接入"]

    lines.append('  subgraph L3["3️⃣ 调度与运行层（Orchestration Layer）"]')
    lines.append("    direction TB")
    lines.append('    L3T["调度与运行能力"]:::cmic_title')
    lines.append("    subgraph L3G[\" \"]")
    lines.append("      direction LR")
    for i, it in enumerate(orch_items, start=1):
        lines.append(f'      ORCH_{i}["{it}"]:::cmic_body')
    lines.append("    end")
    lines.append("  end")
    lines.append("")

    lines.append('  SEP3[" "]:::cmic_sep')
    lines.append("  L3T -.-> SEP3")
    lines.append("")

    # Layer 4: Foundation Layer
    f_items = _limit_items(spec.foundation_capabilities, 6)
    if not f_items:
        f_items = ["身份与权限管理", "注册/发现/授权机制", "安全与合规能力", "协议与协作标准"]

    lines.append('  subgraph L4["4️⃣ 基础支撑层（Foundation Layer）"]')
    lines.append("    direction TB")
    lines.append('    L4T["基础支撑能力"]:::cmic_title')
    lines.append("    subgraph L4G[\" \"]")
    lines.append("      direction LR")
    for i, it in enumerate(f_items, start=1):
        lines.append(f'      FND_{i}["{it}"]:::cmic_body')
    lines.append("    end")
    lines.append("  end")

    lines.append("end")
    lines.append("")

    # Apply subgraph styling by attaching classes to representative invisible anchors.
    # Mermaid doesn't support class on subgraph directly in all versions, so style via `style`.
    lines.append("%% --- Subgraph box styling ---")
    lines.append("style CMIC fill:#EFF9F7,stroke:#2FA7A0,stroke-width:2px")
    lines.append("style L1 fill:#E3F4F1,stroke:#2FA7A0,stroke-width:1.5px")
    lines.append("style L2 fill:#E3F4F1,stroke:#2FA7A0,stroke-width:1.5px")
    lines.append("style L3 fill:#E3F4F1,stroke:#2FA7A0,stroke-width:1.5px")
    lines.append("style L4 fill:#E3F4F1,stroke:#2FA7A0,stroke-width:1.5px")

    # Dotted separators
    lines.append("linkStyle 0 stroke:#B6C2CC,stroke-width:1px,stroke-dasharray:4 3")
    lines.append("linkStyle 1 stroke:#B6C2CC,stroke-width:1px,stroke-dasharray:4 3")
    lines.append("linkStyle 2 stroke:#B6C2CC,stroke-width:1px,stroke-dasharray:4 3")

    return "\n".join(lines)
