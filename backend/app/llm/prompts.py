from __future__ import annotations

import json

from typing import Optional

from app.llm.types import ChatMessage


def diagram_prompt(diagram_type: str, text: str, scene: Optional[str]) -> list[ChatMessage]:
    sys = (
        "你是资深产品/系统分析助手。\n"
        "你只输出严格 JSON（不要 markdown，不要解释）。\n"
        "输出必须是单个 JSON 对象：第一字符是 {，最后字符是 }。\n"
        "必须包含字段 type，且 type 必须等于输入的 diagram_type。\n"
        "根据输入文本提取结构化图规范（Diagram Spec）。\n"
        "必须可用于生成 Mermaid。"
    )

    schema_hint = {
        "flow": {
            "type": "flow",
            "direction": "TD",
            "nodes": [{"id": "n1", "label": "开始"}],
            "edges": [{"from": "n1", "to": "n2", "label": ""}],
        },
        "sequence": {
            "type": "sequence",
            "participants": ["用户", "系统"],
            "messages": [{"from": "用户", "to": "系统", "label": "发起请求"}],
        },
        "state": {
            "type": "state",
            "states": ["Idle", "Processing", "Done"],
            "transitions": [{"from": "Idle", "to": "Processing", "label": "start"}],
        },
    }

    user_obj = {
        "diagram_type": diagram_type,
        "scene": scene,
        "text": text,
        "output_schema_example": schema_hint.get(diagram_type, schema_hint["flow"]),
    }

    return [
        ChatMessage(role="system", content=sys),
        ChatMessage(role="user", content=json.dumps(user_obj, ensure_ascii=False)),
    ]


def integration_prompt(text: str, swagger_text: Optional[str]) -> list[ChatMessage]:
    sys = (
        "你是资深对接方案架构师。输出 Markdown 方案（可直接粘贴到产品方案文档）。\n"
        "内容必须包含：角色与系统边界、调用链路、关键接口、鉴权、幂等、异常与重试、回调/对账、监控告警、落地步骤。\n"
        "若缺少信息，请用‘待确认’列出问题。"
    )
    payload = {"text": text, "swagger_text": swagger_text}
    import json

    return [
        ChatMessage(role="system", content=sys),
        ChatMessage(role="user", content=json.dumps(payload, ensure_ascii=False)),
    ]
