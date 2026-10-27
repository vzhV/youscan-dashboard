from app.core.errors import BoardNotEmptyError
from app.repositories.protocols import DatasetRepository, WidgetRepository
from app.schemas.widget import WidgetRead
from app.services.import_service import ImportService


class DashboardService:
    def __init__(
        self, widgets: WidgetRepository, datasets: DatasetRepository, importer: ImportService
    ) -> None:
        self._widgets = widgets
        self._datasets = datasets
        self._importer = importer

    async def seed(self) -> list[WidgetRead]:
        if await self._widgets.list_ordered():
            raise BoardNotEmptyError("Board is not empty")
        return (await self._importer.import_seed()).widgets

    async def reset(self) -> list[WidgetRead]:
        await self._widgets.delete_all()
        await self._datasets.delete_all()
        return (await self._importer.import_seed()).widgets
