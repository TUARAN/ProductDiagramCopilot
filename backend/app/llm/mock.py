from __future__ import annotations

import json

from app.llm.base import LLMProvider
from app.llm.types import LLMChatRequest, LLMChatResponse


class MockLLMProvider:
    name = "mock"

    async def chat(self, req: LLMChatRequest) -> LLMChatResponse:
        # Deterministic minimal behavior:
        # - If system asks for JSON-only, we return a usable flow spec.
        # - Otherwise return a markdown integration plan.
        system = next((m.content for m in req.messages if m.role == "system"), "")
        user = next((m.content for m in req.messages if m.role == "user"), "")

        if "严格 JSON" in system or "JSON" in system:
            try:
                obj = json.loads(user)
            except Exception:
                obj = {"diagram_type": "flow", "text": user}

            diagram_type = obj.get("diagram_type", "flow")
            text = obj.get("text", "")

            if diagram_type == "sequence":
                spec = {
                    "type": "sequence",
                    "participants": ["用户", "产品智绘官", "模型"],
                    "messages": [
                        {"from": "用户", "to": "产品智绘官", "label": "提交描述"},
                        {"from": "产品智绘官", "to": "模型", "label": "生成 Diagram Spec"},
                        {"from": "模型", "to": "产品智绘官", "label": "返回 JSON"},
                        {"from": "产品智绘官", "to": "用户", "label": "渲染 Mermaid"},
                    ],
                    "note": text[:120],
                }
            elif diagram_type == "state":
                spec = {
                    "type": "state",
                    "states": ["Draft", "Reviewing", "Approved", "Rejected"],
                    "transitions": [
                        {"from": "Draft", "to": "Reviewing", "label": "submit"},
                        {"from": "Reviewing", "to": "Approved", "label": "pass"},
                        {"from": "Reviewing", "to": "Rejected", "label": "deny"},
                    ],
                    "note": text[:120],
                }
            else:
                spec = {
                    "type": "flow",
                    "direction": "TD",
                    "nodes": [
                        {"id": "start", "label": "开始"},
                        {"id": "parse", "label": "解析文本"},
                        {"id": "spec", "label": "生成 Diagram Spec"},
                        {"id": "render", "label": "渲染 Mermaid"},
                        {"id": "end", "label": "结束"},
                    ],
                    "edges": [
                        {"from": "start", "to": "parse", "label": ""},
                        {"from": "parse", "to": "spec", "label": ""},
                        {"from": "spec", "to": "render", "label": ""},
                        {"from": "render", "to": "end", "label": ""},
                    ],
                    "note": text[:120],
                }

            return LLMChatResponse(content=json.dumps(spec, ensure_ascii=False), raw={"mock": True})

        # integration markdown
        md = (
            "# 系统接入方案（Mock）\n\n"
            "## 1. 角色与系统边界\n- 用户\n- A系统（调用方）\n- B系统（被调用方）\n\n"
            "## 2. 调用链路\n1) A -> B：查询订单\n2) A -> B：发起退款\n3) B -> A：回调通知\n\n"
            "## 3. 关键接口（示例）\n- GET /orders/{id}\n- POST /refunds\n- POST /callbacks/refund\n\n"
            "## 4. 鉴权\n- 推荐：HMAC 或 OAuth2 Client Credentials\n\n"
            "## 5. 幂等\n- 退款接口必须支持 Idempotency-Key\n\n"
            "## 6. 异常与重试\n- 5xx 可退避重试；4xx 直接失败\n\n"
            "## 7. 回调与对账\n- 回调必须签名；每日对账文件或查询接口\n\n"
            "## 8. 监控告警\n- 成功率、耗时、回调堆积、对账差异\n\n"
            "## 9. 待确认\n- 退款状态机、超时阈值、对账口径\n"
        )
        return LLMChatResponse(content=md, raw={"mock": True})


def provider() -> LLMProvider:
    return MockLLMProvider()
