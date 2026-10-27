from fastapi import APIRouter

from app.api.routes import dashboard, datasets, health, imports, widgets

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(widgets.router)
api_router.include_router(imports.router)
api_router.include_router(datasets.router)
api_router.include_router(dashboard.router)
