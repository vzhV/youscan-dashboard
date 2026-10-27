from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import session_scope
from app.services.dashboard_service import DashboardService
from app.services.dataset_service import DatasetService
from app.services.factories import (
    build_dashboard_service,
    build_dataset_service,
    build_import_service,
    build_widget_service,
)
from app.services.import_service import ImportService
from app.services.widget_service import WidgetService


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with session_scope(request.app.state.session_factory) as session:
        yield session


# Function scope: the commit must finish before the response is sent, so a failed commit is an error response.
SessionDep = Annotated[AsyncSession, Depends(get_session, scope="function")]


async def get_widget_service(session: SessionDep) -> WidgetService:
    return build_widget_service(session)


WidgetServiceDep = Annotated[WidgetService, Depends(get_widget_service)]


async def get_import_service(session: SessionDep) -> ImportService:
    return build_import_service(session)


ImportServiceDep = Annotated[ImportService, Depends(get_import_service)]


async def get_dataset_service(session: SessionDep) -> DatasetService:
    return build_dataset_service(session)


DatasetServiceDep = Annotated[DatasetService, Depends(get_dataset_service)]


async def get_dashboard_service(session: SessionDep) -> DashboardService:
    return build_dashboard_service(session)


DashboardServiceDep = Annotated[DashboardService, Depends(get_dashboard_service)]
