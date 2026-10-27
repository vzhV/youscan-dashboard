from dataclasses import dataclass

from app.charts.chart_data import ChartData
from app.charts.thinning import thin
from app.core.enums import ChartType, DatasetOrigin, WidgetType
from app.models import Dataset, Widget
from app.repositories.protocols import WidgetRepository


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    origin: DatasetOrigin
    chart_type: ChartType
    data: ChartData
    row_count: int
    source_filename: str | None = None
    source_sheet: str | None = None


@dataclass(frozen=True)
class WidgetDraft:
    type: WidgetType
    title: str
    dataset: Dataset | None = None
    text_content: str | None = None


def new_dataset(spec: DatasetSpec) -> Dataset:
    return Dataset(
        name=spec.name,
        origin=spec.origin,
        chart_type=spec.chart_type,
        source_filename=spec.source_filename,
        source_sheet=spec.source_sheet,
        row_count=spec.row_count,
        data=spec.data.model_dump(),
        display_data=thin(spec.data).model_dump(),
    )


async def append_widget(widgets: WidgetRepository, draft: WidgetDraft) -> Widget:
    widget = Widget(
        type=draft.type,
        title=draft.title,
        position=await widgets.next_position(),
        dataset_id=draft.dataset.id if draft.dataset is not None else None,
        text_content=draft.text_content,
    )
    return await widgets.add(widget)
