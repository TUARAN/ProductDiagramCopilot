from fastapi import APIRouter

from app.data_pipeline.settlement import (
    SettlementMetricsRequest,
    SettlementMetricsResponse,
    compute_settlement_metrics,
)

router = APIRouter()


@router.post("/metrics", response_model=SettlementMetricsResponse)
def metrics(req: SettlementMetricsRequest):
    return compute_settlement_metrics(req)
