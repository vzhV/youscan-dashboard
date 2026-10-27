from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import session_scope
from app.services.factories import build_widget_service
from app.services.widget_service import WidgetService


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with session_scope(request.app.state.session_factory) as session:
        yield session


# Function scope: the commit must finish before the response is sent, so a failed commit is an error response.
SessionDep = Annotated[AsyncSession, Depends(get_session, scope="function")]


async def get_widget_service(session: SessionDep) -> WidgetService:
    return build_widget_service(session)


WidgetServiceDep = Annotated[WidgetService, Depends(get_widget_service)]
