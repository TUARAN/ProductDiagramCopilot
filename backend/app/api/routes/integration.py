from fastapi import APIRouter

from app.generator.integration import IntegrationGenerateRequest, IntegrationGenerateResponse
from app.generator.service import generate_integration_plan

router = APIRouter()


@router.post("/generate", response_model=IntegrationGenerateResponse)
def generate(req: IntegrationGenerateRequest):
    return generate_integration_plan(req)
