from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter
from fastapi import HTTPException
from pydantic import BaseModel

from app.core.settings import settings
from app.generator.diagram import DiagramGenerateRequest
from app.generator.integration import IntegrationGenerateRequest
from app.generator.service import generate_diagram, generate_integration_plan

router = APIRouter()


# Dev-friendly fallback when Redis/Celery broker isn't available.
_INPROC_TASKS: Dict[str, Dict[str, Any]] = {}


def _get_celery_app():
    try:
        from app.jobs.celery_app import celery_app  # local import: optional dependency

        return celery_app
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=(
                "Celery is not available. Install backend dependencies and/or set TASK_MODE=inproc. "
                f"(import error: {e})"
            ),
        )


def _get_async_result(task_id: str, celery_app):
    try:
        from celery.result import AsyncResult  # local import: optional dependency

        return AsyncResult(task_id, app=celery_app)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=(
                "Celery is not available. Install backend dependencies and/or set TASK_MODE=inproc. "
                f"(import error: {e})"
            ),
        )


def _celery_broker_available(celery_app) -> bool:
    url = getattr(celery_app.conf, "broker_url", None)
    if not url:
        return False

    try:
        from kombu import Connection
        from kombu.exceptions import OperationalError

        with Connection(url, connect_timeout=0.5) as conn:
            conn.ensure_connection(max_retries=1)
        return True
    except OperationalError:
        return False
    except ImportError:
        # kombu isn't installed (often because celery extras aren't installed).
        return False
    except Exception:
        return False


class TaskSubmitResponse(BaseModel):
    task_id: str


class TaskStatusResponse(BaseModel):
    task_id: str
    state: str
    result: Optional[Dict[str, Any]] = None


@router.post("/diagram", response_model=TaskSubmitResponse)
def submit_diagram(req: DiagramGenerateRequest):
    payload = req.model_dump()
    try:
        if (settings.TASK_MODE or "inproc").lower() != "celery":
            raise RuntimeError("TASK_MODE!=celery")
        celery_app = _get_celery_app()
        if not _celery_broker_available(celery_app):
            raise RuntimeError("celery broker unavailable")
        r = celery_app.send_task("pdc.diagram.generate", kwargs={}, args=[payload])
        return TaskSubmitResponse(task_id=r.id)
    except Exception:
        task_id = f"inproc-{uuid.uuid4()}"
        try:
            result = generate_diagram(req).model_dump()
            _INPROC_TASKS[task_id] = {"state": "SUCCESS", "result": result}
            return TaskSubmitResponse(task_id=task_id)
        except Exception as e:
            _INPROC_TASKS[task_id] = {"state": "FAILURE", "result": {"error": str(e)}}
            return TaskSubmitResponse(task_id=task_id)


@router.post("/integration", response_model=TaskSubmitResponse)
def submit_integration(req: IntegrationGenerateRequest):
    payload = req.model_dump()
    try:
        if (settings.TASK_MODE or "inproc").lower() != "celery":
            raise RuntimeError("TASK_MODE!=celery")
        celery_app = _get_celery_app()
        if not _celery_broker_available(celery_app):
            raise RuntimeError("celery broker unavailable")
        r = celery_app.send_task("pdc.integration.generate", kwargs={}, args=[payload])
        return TaskSubmitResponse(task_id=r.id)
    except Exception:
        task_id = f"inproc-{uuid.uuid4()}"
        try:
            result = generate_integration_plan(req).model_dump()
            _INPROC_TASKS[task_id] = {"state": "SUCCESS", "result": result}
            return TaskSubmitResponse(task_id=task_id)
        except Exception as e:
            _INPROC_TASKS[task_id] = {"state": "FAILURE", "result": {"error": str(e)}}
            return TaskSubmitResponse(task_id=task_id)


@router.get("/{task_id}", response_model=TaskStatusResponse)
def task_status(task_id: str):
    if task_id in _INPROC_TASKS:
        item = _INPROC_TASKS[task_id]
        return TaskStatusResponse(task_id=task_id, state=item.get("state", "PENDING"), result=item.get("result"))

    # If we're not in celery mode, we don't have an external task backend.
    if (settings.TASK_MODE or "inproc").lower() != "celery":
        raise HTTPException(status_code=404, detail="task not found")

    celery_app = _get_celery_app()

    ar = _get_async_result(task_id, celery_app)
    res = ar.result if ar.successful() else None
    if isinstance(res, BaseException):
        res = {"error": str(res)}
    return TaskStatusResponse(task_id=task_id, state=ar.state, result=res if isinstance(res, dict) else None)
