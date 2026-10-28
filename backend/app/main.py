from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.openapi import TAGS_METADATA, DashboardApi, generate_operation_id
from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.db import create_engine, create_session_factory
from app.core.logging import configure_logging

API_PREFIX = "/api/v1"
APP_TITLE = "Dashboard API"
APP_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = create_engine(app.state.settings)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    try:
        yield
    finally:
        await engine.dispose()


def create_app(settings: Settings | None = None) -> DashboardApi:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    app = DashboardApi(
        lifespan=lifespan,
        title=APP_TITLE,
        version=APP_VERSION,
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=f"{API_PREFIX}/redoc",
        openapi_url=f"{API_PREFIX}/openapi.json",
        swagger_ui_oauth2_redirect_url=f"{API_PREFIX}/docs/oauth2-redirect",
        openapi_tags=TAGS_METADATA,
        generate_unique_id_function=generate_operation_id,
    )
    app.state.settings = settings
    register_error_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
