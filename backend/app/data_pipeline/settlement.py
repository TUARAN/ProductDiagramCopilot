from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SettlementMetricsRequest(BaseModel):
    month: str = Field(description="YYYY-MM")
    rows: list[dict[str, Any]]


class SettlementMetricsResponse(BaseModel):
    month: str
    metrics: dict[str, float]


def compute_settlement_metrics(req: SettlementMetricsRequest) -> SettlementMetricsResponse:
    # MVP: accept generic rows and compute a stable set of 5+ core metrics.
    # Expected (best-effort) fields: amount, status, channel.
    total_count = len(req.rows)
    total_amount = 0.0
    success_amount = 0.0
    success_count = 0
    failed_count = 0
    pending_count = 0

    for r in req.rows:
        amount = r.get("amount", 0)
        try:
            amount_f = float(amount)
        except Exception:
            amount_f = 0.0

        status = str(r.get("status", "")).lower()
        total_amount += amount_f

        if status in {"success", "succeeded", "ok"}:
            success_count += 1
            success_amount += amount_f
        elif status in {"failed", "fail", "error"}:
            failed_count += 1
        else:
            pending_count += 1

    success_rate = (success_count / total_count) if total_count else 0.0

    metrics: dict[str, float] = {
        "total_count": float(total_count),
        "total_amount": round(total_amount, 2),
        "success_count": float(success_count),
        "success_amount": round(success_amount, 2),
        "failed_count": float(failed_count),
        "pending_count": float(pending_count),
        "success_rate": round(success_rate, 4),
    }

    return SettlementMetricsResponse(month=req.month, metrics=metrics)
