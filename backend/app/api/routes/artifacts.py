from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.db import SessionLocal
from app.models.artifact import Artifact

router = APIRouter()


class ArtifactOut(BaseModel):
    id: str
    kind: str
    status: str
    request: Dict[str, Any]
    spec: Optional[Dict[str, Any]] = None
    mermaid: Optional[str] = None
    markdown: Optional[str] = None
    object_key: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@router.get("/", response_model=List[ArtifactOut])
def list_artifacts(limit: int = 50):
    try:
        with SessionLocal() as db:
            rows = db.execute(select(Artifact).order_by(Artifact.created_at.desc()).limit(limit)).scalars().all()
            return [
                ArtifactOut(
                    id=a.id,
                    kind=a.kind,
                    status=a.status,
                    request=a.request or {},
                    spec=a.spec,
                    mermaid=a.mermaid,
                    markdown=a.markdown,
                    object_key=a.object_key,
                    error=a.error,
                    created_at=a.created_at.isoformat() if a.created_at else None,
                    updated_at=a.updated_at.isoformat() if a.updated_at else None,
                )
                for a in rows
            ]
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="database unavailable")


@router.get("/{artifact_id}", response_model=ArtifactOut)
def get_artifact(artifact_id: str):
    try:
        with SessionLocal() as db:
            a = db.get(Artifact, artifact_id)
            if a is None:
                raise HTTPException(status_code=404, detail="artifact not found")
            return ArtifactOut(
                id=a.id,
                kind=a.kind,
                status=a.status,
                request=a.request or {},
                spec=a.spec,
                mermaid=a.mermaid,
                markdown=a.markdown,
                object_key=a.object_key,
                error=a.error,
                created_at=a.created_at.isoformat() if a.created_at else None,
                updated_at=a.updated_at.isoformat() if a.updated_at else None,
            )
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="database unavailable")
