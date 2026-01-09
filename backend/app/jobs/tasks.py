from __future__ import annotations

import json

from sqlalchemy.exc import SQLAlchemyError

from app.core.db import SessionLocal
from app.core.storage import safe_put_text
from app.generator.diagram import DiagramGenerateRequest
from app.generator.integration import IntegrationGenerateRequest
from app.generator.service import generate_diagram, generate_integration_plan
from app.jobs.celery_app import celery_app
from app.models.artifact import Artifact


@celery_app.task(name="pdc.ping")
def ping() -> str:
    return "pong"


@celery_app.task(name="pdc.diagram.generate")
def generate_diagram_task(payload: dict) -> dict:
    req = DiagramGenerateRequest.model_validate(payload)
    result = generate_diagram(req)

    artifact_id = None
    try:
        with SessionLocal() as db:
            a = Artifact(
                kind="diagram",
                status="done",
                request=req.model_dump(),
                spec=result.spec,
                mermaid=result.mermaid,
            )
            # Store a copy in MinIO (best-effort)
            object_key = f"artifacts/{a.id}/diagram.mmd"
            a.object_key = safe_put_text(object_key, result.mermaid, content_type="text/plain; charset=utf-8")
            db.add(a)
            db.commit()
            artifact_id = a.id
    except SQLAlchemyError:
        artifact_id = None
    except Exception:
        artifact_id = None

    return {"artifact_id": artifact_id, **result.model_dump()}


@celery_app.task(name="pdc.integration.generate")
def generate_integration_task(payload: dict) -> dict:
    req = IntegrationGenerateRequest.model_validate(payload)
    result = generate_integration_plan(req)

    artifact_id = None
    try:
        with SessionLocal() as db:
            a = Artifact(
                kind="integration",
                status="done",
                request=req.model_dump(),
                markdown=result.markdown,
            )
            object_key = f"artifacts/{a.id}/integration.md"
            a.object_key = safe_put_text(object_key, result.markdown, content_type="text/markdown; charset=utf-8")
            db.add(a)
            db.commit()
            artifact_id = a.id
    except SQLAlchemyError:
        artifact_id = None
    except Exception:
        artifact_id = None

    return {"artifact_id": artifact_id, **result.model_dump()}
