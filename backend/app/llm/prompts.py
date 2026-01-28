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


def drawio_xml_prompt(text: str) -> list[ChatMessage]:
    sys = (
        "你是资深企业架构师与 diagrams.net（draw.io）制图助手。\n"
        "你的任务：把用户的业务/系统描述转成可直接导入 draw.io 的 mxfile XML。\n"
        "输出要求（必须严格遵守）：\n"
        "1) 只输出 XML：必须以 <mxfile 开头，以 </mxfile> 结尾；不要 markdown、不要解释、不要代码块标记。\n"
        "2) XML 必须可被 draw.io 正常打开；必须包含一个 <diagram> 与 <mxGraphModel>/<root>。\n"
        "3) 合规与安全：不要包含任何个人敏感信息、密钥、Token、真实账号；不要包含外链、图片、脚本；避免使用 foreignObject。\n"
        "4) 生成‘通用业务系统架构’风格：按层级组织（客户端层/接入层/业务服务层/数据与中间件/可观测性&运维）。\n"
        "5) 如果用户信息不足：用‘待确认’作为节点文本提出问题，而不是编造具体数值或真实系统名。\n"
        "6) 文本默认中文，必要时保留英文缩写（如 API Gateway、Redis）。"
    )

    user_obj = {"text": text}
    return [
        ChatMessage(role="system", content=sys),
        ChatMessage(role="user", content=json.dumps(user_obj, ensure_ascii=False)),
    ]
