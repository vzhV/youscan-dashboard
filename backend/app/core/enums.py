from enum import StrEnum


class ChartType(StrEnum):
    LINE = "line"
    BAR = "bar"
    STACKED_BAR = "stacked_bar"
    PIE = "pie"


class WidgetType(StrEnum):
    LINE = "line"
    BAR = "bar"
    STACKED_BAR = "stacked_bar"
    PIE = "pie"
    TEXT = "text"


class DatasetOrigin(StrEnum):
    SEED = "seed"
    UPLOAD = "upload"
    GENERATED = "generated"


def chart_type_of(widget_type: WidgetType) -> ChartType | None:
    if widget_type is WidgetType.TEXT:
        return None
    return ChartType(widget_type.value)
