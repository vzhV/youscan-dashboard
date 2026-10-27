from app.models import Dataset, Widget
from app.schemas.dataset import DatasetRead
from app.schemas.widget import WidgetRead, WidgetSource


def _to_widget_source(dataset: Dataset | None) -> WidgetSource | None:
    if dataset is None:
        return None
    return WidgetSource(
        dataset_id=dataset.id,
        origin=dataset.origin,
        filename=dataset.source_filename,
        sheet=dataset.source_sheet,
    )


def to_widget_read(widget: Widget) -> WidgetRead:
    return WidgetRead(
        id=widget.id,
        type=widget.type,
        title=widget.title,
        position=widget.position,
        text_content=widget.text_content,
        source=_to_widget_source(widget.dataset),
        created_at=widget.created_at,
        updated_at=widget.updated_at,
    )


def to_dataset_read(dataset: Dataset, widget_count: int) -> DatasetRead:
    return DatasetRead(
        id=dataset.id,
        name=dataset.name,
        origin=dataset.origin,
        chart_type=dataset.chart_type,
        source_filename=dataset.source_filename,
        source_sheet=dataset.source_sheet,
        row_count=dataset.row_count,
        widget_count=widget_count,
        created_at=dataset.created_at,
    )
