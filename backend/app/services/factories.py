"""Composition root: the only service module that builds the concrete SQL repositories."""

import random
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.dataset_repository import SqlDatasetRepository
from app.repositories.widget_repository import SqlWidgetRepository
from app.services.widget_service import WidgetService


def build_widget_service(session: AsyncSession) -> WidgetService:
    # Demo chart data only, so a non-cryptographic generator is the right tool.
    rng = random.Random()  # noqa: S311
    return WidgetService(SqlWidgetRepository(session), SqlDatasetRepository(session), rng, date.today)
