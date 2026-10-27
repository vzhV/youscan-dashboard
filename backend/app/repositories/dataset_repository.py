from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.charts.chart_data import ChartData
from app.core.enums import DatasetOrigin
from app.models import Dataset, Widget


class SqlDatasetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_with_widget_counts(self) -> list[tuple[Dataset, int]]:
        statement = (
            select(Dataset, func.count(Widget.id))
            .outerjoin(Widget, Widget.dataset_id == Dataset.id)
            .where(Dataset.origin != DatasetOrigin.GENERATED)
            .group_by(Dataset.id)
            .order_by(Dataset.created_at, Dataset.id)
        )
        return [(dataset, count) for dataset, count in (await self._session.execute(statement)).all()]

    async def get(self, dataset_id: UUID) -> Dataset | None:
        return await self._session.scalar(select(Dataset).where(Dataset.id == dataset_id))

    async def get_display_data(self, dataset_id: UUID) -> ChartData | None:
        # Selecting the bare column avoids materialising (and caching) a Dataset just to read its payload.
        statement = select(Dataset.display_data).where(Dataset.id == dataset_id)
        payload = await self._session.scalar(statement)
        return None if payload is None else ChartData.model_validate(payload)

    async def add(self, dataset: Dataset) -> Dataset:
        self._session.add(dataset)
        await self._session.flush()
        return dataset

    async def delete(self, dataset: Dataset) -> None:
        # The widgets go with it through the ON DELETE CASCADE foreign key.
        await self._session.delete(dataset)
        await self._session.flush()

    async def delete_all(self) -> None:
        await self._session.execute(delete(Dataset))
        self._session.expunge_all()
