from fastapi import APIRouter

from app.api.routes import artifacts, db, diagram, integration, llm, settlement, tasks

api_router = APIRouter()

api_router.include_router(diagram.router, prefix="/diagram", tags=["diagram"])
api_router.include_router(integration.router, prefix="/integration", tags=["integration"])
api_router.include_router(settlement.router, prefix="/settlement", tags=["settlement"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(artifacts.router, prefix="/artifacts", tags=["artifacts"])
api_router.include_router(llm.router, prefix="/llm", tags=["llm"])
api_router.include_router(db.router, prefix="/db", tags=["db"])
