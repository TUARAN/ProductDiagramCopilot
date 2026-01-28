from __future__ import annotations

import json

from typing import Optional

from app.llm.types import ChatMessage


def diagram_prompt(diagram_type: str, text: str, scene: Optional[str]) -> list[ChatMessage]:
    if diagram_type == "cmic_report":
        sys = (
            "你是一名企业级 AI 平台架构图设计专家。\n"
            "你只输出严格 JSON（不要 markdown，不要解释）。\n"
            "输出必须是单个 JSON 对象：第一字符是 {，最后字符是 }。\n"
            "必须包含字段 type，且 type 必须等于输入的 diagram_type（cmic_report）。\n"
            "你要做的是：在固定的分层架构图结构里，产出用于‘替换填充’的文案字段。\n"
            "不要出现代码、不要出现实现细节、不要出现具体产品品牌名（强调平台能力）。\n"
            "文案要适合 PPT/方案文档，短句、克制、可汇报。\n"
            "输出字段（必须包含）：\n"
            "- title: 图标题（1 行）\n"
            "- platform_labels: 平台命名短语列表（3~5 个）\n"
            "- application_agents: 应用层智能体入口（4~8 个）\n"
            "- agent_service_capabilities: 服务层能力颗粒度（6~10 个）\n"
            "- orchestration_capabilities: 调度与运行层（4~6 个）\n"
            "- foundation_capabilities: 基础支撑层（4~6 个）\n"
            "注意：整张图的结构由系统固定渲染，你只负责输出这些可替换的文案。"
        )
    else:
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
        "cmic_report": {
            "type": "cmic_report",
            "title": "智能体平台总体架构图",
            "platform_labels": ["消息智能体平台", "行业智能体平台", "企业 AI 中台", "智能体协同操作系统"],
            "application_agents": [
                "用户交互型智能体",
                "场景任务型智能体",
                "安全与治理型智能体",
                "可扩展智能体入口",
            ],
            "agent_service_capabilities": [
                "多智能体协同与编排",
                "认知与决策引擎",
                "领域知识与知识体系",
                "多模型接入与调度",
                "通用智能组件能力池",
                "用户画像与标签",
                "场景能力 / 插件 / 应用货架",
            ],
            "orchestration_capabilities": [
                "请求路由与策略调度",
                "业务系统接入适配",
                "消息 / 事件驱动",
                "生态与第三方能力接入",
            ],
            "foundation_capabilities": [
                "身份与权限管理",
                "注册、发现与授权机制",
                "安全与合规能力",
                "协议与协作标准",
            ],
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
