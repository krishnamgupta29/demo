"""API Router configuration aggregating v1 versioned endpoints."""

from fastapi import APIRouter
from backend.api.routes import health, models, studies

api_router = APIRouter(prefix="/api/v1")

# Mount endpoints
api_router.include_router(health.router)
api_router.include_router(studies.router)
api_router.include_router(models.router)

# Health routes remain at root and v1
root_router = APIRouter()
root_router.include_router(health.router)
root_router.include_router(api_router)

