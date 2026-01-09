from fastapi import APIRouter

from app.generator.diagram import DiagramGenerateRequest, DiagramGenerateResponse
from app.generator.service import generate_diagram

router = APIRouter()


@router.post("/generate", response_model=DiagramGenerateResponse)
def generate(req: DiagramGenerateRequest):
    return generate_diagram(req)
