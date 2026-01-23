import json

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.generator.diagram import DiagramGenerateRequest, DiagramGenerateResponse
from app.generator.service import generate_diagram

router = APIRouter()


@router.post("/generate", response_model=DiagramGenerateResponse)
def generate(req: DiagramGenerateRequest):
    try:
        return generate_diagram(req)
    except ValidationError as e:
        # Spec JSON is parseable but doesn't match our schema.
        raise HTTPException(status_code=422, detail=str(e))
    except json.JSONDecodeError as e:
        # Model returned non-JSON (or JSON embedded in other text but still unparsable).
        raise HTTPException(status_code=502, detail=f"LLM output is not valid JSON: {e}")
    except ValueError as e:
        # Common for model output shape issues (missing keys, wrong type, etc.).
        raise HTTPException(status_code=502, detail=str(e))
