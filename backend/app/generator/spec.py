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


class CmicReportSpec(BaseModel):
    type: Literal["cmic_report"]

    # 1) 图标题（可汇报）
    title: str = "智能体平台总体架构图"

    # 2) 平台定位/中台命名（通常 3~5 个短语）
    platform_labels: list[str] = [
        "消息智能体平台",
        "行业智能体平台",
        "企业 AI 中台",
        "智能体协同操作系统",
    ]

    # 3) 应用层：智能体类型入口（建议 4~8 个）
    application_agents: list[str] = [
        "用户交互型智能体",
        "场景任务型智能体",
        "安全与治理型智能体",
        "可扩展智能体入口",
    ]

    # 4) 服务层：能力颗粒度（建议 6~10 个）
    agent_service_capabilities: list[str] = [
        "多智能体协同与编排",
        "认知与决策引擎",
        "领域知识与知识体系",
        "多模型接入与调度",
        "通用智能组件能力池",
        "用户画像与标签",
        "场景能力 / 插件 / 应用货架",
    ]

    # 5) 调度与运行层（建议 4~6 个）
    orchestration_capabilities: list[str] = [
        "请求路由与策略调度",
        "业务系统接入适配",
        "消息 / 事件驱动",
        "生态与第三方能力接入",
    ]

    # 6) 基础支撑层（建议 4~6 个）
    foundation_capabilities: list[str] = [
        "身份与权限管理",
        "注册、发现与授权机制",
        "安全与合规能力",
        "协议与协作标准",
    ]
