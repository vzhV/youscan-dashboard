from uuid import UUID

from app.core.enums import DatasetOrigin, widget_type_of
from app.core.errors import NotFoundError
from app.models import Dataset
from app.repositories.protocols import DatasetRepository, WidgetRepository
from app.schemas.dataset import DatasetRead
from app.schemas.widget import WidgetRead
from app.services.mappers import to_dataset_read, to_widget_read
from app.services.records import WidgetDraft, append_widget


class DatasetService:
    def __init__(self, datasets: DatasetRepository, widgets: WidgetRepository) -> None:
        self._datasets = datasets
        self._widgets = widgets

    async def list_datasets(self) -> list[DatasetRead]:
        # The repository already hides generated datasets.
        return [
            to_dataset_read(dataset, count)
            for dataset, count in await self._datasets.list_with_widget_counts()
        ]

    async def add_to_dashboard(self, dataset_id: UUID) -> WidgetRead:
        # Locks the dataset against a concurrent delete until commit; see get_for_widget.
        dataset = _visible_or_not_found(await self._datasets.get_for_widget(dataset_id), dataset_id)
        draft = WidgetDraft(type=widget_type_of(dataset.chart_type), title=dataset.name, dataset=dataset)
        return to_widget_read(await append_widget(self._widgets, draft))

    async def delete_dataset(self, dataset_id: UUID) -> None:
        # The widgets go with it through the foreign key cascade.
        dataset = _visible_or_not_found(await self._datasets.get(dataset_id), dataset_id)
        await self._datasets.delete(dataset)


def _visible_or_not_found(dataset: Dataset | None, dataset_id: UUID) -> Dataset:
    # Generated datasets belong to their widget: sharing or deleting one would remove that widget's data.
    if dataset is None or dataset.origin is DatasetOrigin.GENERATED:
        raise NotFoundError("Dataset not found", details={"dataset_id": str(dataset_id)})
    return dataset
