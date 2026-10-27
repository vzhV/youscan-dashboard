"""In-memory repositories for service unit tests.

Payload columns (`Dataset.data` / `display_data`) must be read only through `get_display_data`: the SQL
repositories leave them deferred and raise on direct access, while these fakes would silently allow it.
"""

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from app.charts.chart_data import ChartData
from app.core.enums import DatasetOrigin, WidgetType
from app.models import Dataset, Widget
from app.models.base import utc_now


@dataclass
class InMemoryStore:
    widgets: dict[UUID, Widget] = field(default_factory=dict)
    datasets: dict[UUID, Dataset] = field(default_factory=dict)


def _fill_database_defaults(entity: Widget | Dataset) -> None:
    """Assign what the database or the column defaults would on flush."""
    entity.id = entity.id or uuid4()
    entity.created_at = entity.created_at or utc_now()
    if isinstance(entity, Widget):
        entity.updated_at = entity.updated_at or utc_now()


class InMemoryWidgetRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def list_ordered(self) -> list[Widget]:
        return sorted(
            self._store.widgets.values(), key=lambda widget: (widget.position, widget.created_at, widget.id)
        )

    async def get(self, widget_id: UUID) -> Widget | None:
        return self._store.widgets.get(widget_id)

    async def add(self, widget: Widget) -> Widget:
        self._check_constraints(widget)
        _fill_database_defaults(widget)
        widget.dataset = self._store.datasets.get(widget.dataset_id) if widget.dataset_id else None
        self._store.widgets[widget.id] = widget
        return widget

    async def save(self, widget: Widget) -> Widget:
        widget.updated_at = utc_now()
        return widget

    async def delete(self, widget: Widget) -> None:
        del self._store.widgets[widget.id]

    async def next_position(self) -> int:
        return max((widget.position for widget in self._store.widgets.values()), default=-1) + 1

    async def count_by_type(self, widget_type: WidgetType) -> int:
        return sum(widget.type == widget_type for widget in self._store.widgets.values())

    async def delete_all(self) -> None:
        self._store.widgets.clear()

    def _check_constraints(self, widget: Widget) -> None:
        """Fail where the database would: the foreign key and both widget CHECK constraints."""
        if widget.dataset_id is not None and widget.dataset_id not in self._store.datasets:
            raise ValueError(f"Foreign key violation: dataset {widget.dataset_id} does not exist")
        if (widget.type == WidgetType.TEXT) != (widget.dataset_id is None):
            raise ValueError("Check violation: a widget has a dataset if and only if it is not text")
        if widget.type != WidgetType.TEXT and widget.text_content is not None:
            raise ValueError("Check violation: only text widgets have text content")


class InMemoryDatasetRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def list_with_widget_counts(self) -> list[tuple[Dataset, int]]:
        listed = [
            dataset for dataset in self._store.datasets.values() if dataset.origin != DatasetOrigin.GENERATED
        ]
        listed.sort(key=lambda dataset: (dataset.created_at, dataset.id))
        return [(dataset, self._count_widgets(dataset)) for dataset in listed]

    async def get(self, dataset_id: UUID) -> Dataset | None:
        return self._store.datasets.get(dataset_id)

    async def get_display_data(self, dataset_id: UUID) -> ChartData | None:
        dataset = self._store.datasets.get(dataset_id)
        return None if dataset is None else ChartData.model_validate(dataset.display_data)

    async def add(self, dataset: Dataset) -> Dataset:
        _fill_database_defaults(dataset)
        self._store.datasets[dataset.id] = dataset
        return dataset

    async def delete(self, dataset: Dataset) -> None:
        # Mirrors the ON DELETE CASCADE foreign key.
        del self._store.datasets[dataset.id]
        self._remove_widgets_of({dataset.id})

    async def delete_all(self) -> None:
        self._remove_widgets_of(set(self._store.datasets))
        self._store.datasets.clear()

    def _count_widgets(self, dataset: Dataset) -> int:
        return sum(widget.dataset_id == dataset.id for widget in self._store.widgets.values())

    def _remove_widgets_of(self, dataset_ids: set[UUID]) -> None:
        doomed = [
            widget_id for widget_id, widget in self._store.widgets.items() if widget.dataset_id in dataset_ids
        ]
        for widget_id in doomed:
            del self._store.widgets[widget_id]
