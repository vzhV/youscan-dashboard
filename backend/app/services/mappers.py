from app.models import Dataset, Widget
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
