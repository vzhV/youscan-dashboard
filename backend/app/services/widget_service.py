import random
from collections.abc import Callable, Mapping
from datetime import date
from uuid import UUID

from app.charts.chart_data import ChartData
from app.charts.random_data import generate_chart_data
from app.core.enums import ChartType, DatasetOrigin, WidgetType, chart_type_of
from app.core.errors import DomainValidationError, NotFoundError, WidgetHasNoDataError
from app.models import Dataset, Widget
from app.repositories.protocols import DatasetRepository, WidgetRepository
from app.schemas.widget import WidgetCreate, WidgetRead, WidgetUpdate
from app.services.mappers import to_widget_read
from app.services.records import DatasetSpec, WidgetDraft, append_widget, new_dataset

WIDGET_TYPE_LABELS: Mapping[WidgetType, str] = {
    WidgetType.LINE: "Line chart",
    WidgetType.BAR: "Bar chart",
    WidgetType.STACKED_BAR: "Stacked bar chart",
    WidgetType.PIE: "Pie chart",
    WidgetType.TEXT: "Text",
}
TEXT_PLACEHOLDER = "New note. Use Edit to change this text."


class WidgetService:
    def __init__(
        self,
        widgets: WidgetRepository,
        datasets: DatasetRepository,
        rng: random.Random,
        today: Callable[[], date],
    ) -> None:
        self._widgets = widgets
        self._datasets = datasets
        self._rng = rng
        self._today = today

    async def list_widgets(self) -> list[WidgetRead]:
        return [to_widget_read(widget) for widget in await self._widgets.list_ordered()]

    async def create_widget(self, payload: WidgetCreate) -> WidgetRead:
        title = payload.title or await self._default_title(payload.type)
        chart_type = chart_type_of(payload.type)
        if chart_type is None:
            draft = WidgetDraft(type=payload.type, title=title, text_content=TEXT_PLACEHOLDER)
        else:
            dataset = await self._datasets.add(self._generated_dataset(title, chart_type))
            draft = WidgetDraft(type=payload.type, title=title, dataset=dataset)
        return to_widget_read(await append_widget(self._widgets, draft))

    async def update_widget(self, widget_id: UUID, payload: WidgetUpdate) -> WidgetRead:
        widget = await self._require_widget(widget_id)
        if payload.text_content is not None:
            if widget.type is not WidgetType.TEXT:
                raise DomainValidationError("text_content can only be set on text widgets")
            widget.text_content = payload.text_content
        if payload.title is not None:
            widget.title = payload.title
        # Flush now so updated_at is refreshed before the response is built.
        return to_widget_read(await self._widgets.save(widget))

    async def delete_widget(self, widget_id: UUID) -> None:
        widget = await self._require_widget(widget_id)
        dataset = widget.dataset
        # Widget first: deleting the dataset first would cascade behind the session's back.
        await self._widgets.delete(widget)
        if dataset is not None and dataset.origin is DatasetOrigin.GENERATED:
            await self._datasets.delete(dataset)

    async def get_widget_data(self, widget_id: UUID) -> ChartData:
        widget = await self._require_widget(widget_id)
        if widget.dataset_id is None:
            raise WidgetHasNoDataError("Text widgets have no chart data")
        data = await self._datasets.get_display_data(widget.dataset_id)
        if data is None:
            raise NotFoundError("Dataset not found", details={"dataset_id": str(widget.dataset_id)})
        return data

    async def _default_title(self, widget_type: WidgetType) -> str:
        count = await self._widgets.count_by_type(widget_type)
        return f"{WIDGET_TYPE_LABELS[widget_type]} {count + 1}"

    def _generated_dataset(self, title: str, chart_type: ChartType) -> Dataset:
        data = generate_chart_data(chart_type, self._rng, self._today())
        return new_dataset(
            DatasetSpec(
                name=title,
                origin=DatasetOrigin.GENERATED,
                chart_type=chart_type,
                data=data,
                row_count=len(data.categories),
            )
        )

    async def _require_widget(self, widget_id: UUID) -> Widget:
        widget = await self._widgets.get(widget_id)
        if widget is None:
            raise NotFoundError("Widget not found", details={"widget_id": str(widget_id)})
        return widget
