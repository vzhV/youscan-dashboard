from app.core.enums import ChartType
from app.importing.shaping.chart_rules import violation
from app.importing.shaping.shaper import ShapedTable


def suggest_chart_type(shaped: ShapedTable) -> ChartType | None:
    candidates = _candidates(shaped)
    return next((chart_type for chart_type in candidates if violation(chart_type, shaped.data) is None), None)


def _candidates(shaped: ShapedTable) -> list[ChartType]:
    if shaped.categories_are_dates:
        return [ChartType.LINE]
    if len(shaped.data.series) == 1:
        return [ChartType.PIE, ChartType.BAR]
    return [ChartType.STACKED_BAR, ChartType.BAR]
