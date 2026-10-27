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


def explain_no_suggestion(shaped: ShapedTable) -> str:
    """Why the preferred chart type does not fit; used when `suggest_chart_type` found nothing."""
    reason = violation(_candidates(shaped)[0], shaped.data)
    if reason is None:
        raise ValueError("explain_no_suggestion called for data that has a suggested chart type")
    return reason
