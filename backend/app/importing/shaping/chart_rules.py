from collections.abc import Callable, Mapping
from dataclasses import dataclass

from app.charts.chart_data import ChartData
from app.core.enums import ChartType
from app.core.errors import ChartTypeMismatchError

MAX_BAR_CATEGORIES = 100
MAX_PIE_CATEGORIES = 20


@dataclass(frozen=True)
class ChartRule:
    chart_type: ChartType
    max_categories: int | None
    requires_single_series: bool
    requires_non_negative: bool
    allows_gaps: bool


CHART_RULES: Mapping[ChartType, ChartRule] = {
    ChartType.LINE: ChartRule(
        chart_type=ChartType.LINE,
        max_categories=None,
        requires_single_series=False,
        requires_non_negative=False,
        allows_gaps=True,
    ),
    ChartType.BAR: ChartRule(
        chart_type=ChartType.BAR,
        max_categories=MAX_BAR_CATEGORIES,
        requires_single_series=False,
        requires_non_negative=False,
        allows_gaps=True,
    ),
    ChartType.STACKED_BAR: ChartRule(
        chart_type=ChartType.STACKED_BAR,
        max_categories=MAX_BAR_CATEGORIES,
        requires_single_series=False,
        requires_non_negative=False,
        allows_gaps=True,
    ),
    ChartType.PIE: ChartRule(
        chart_type=ChartType.PIE,
        max_categories=MAX_PIE_CATEGORIES,
        requires_single_series=True,
        requires_non_negative=True,
        allows_gaps=False,
    ),
}


def violation(chart_type: ChartType, data: ChartData) -> str | None:
    """Why the data cannot be drawn as this chart type, or None when it fits."""
    rule = CHART_RULES[chart_type]
    return next((reason for check in _CHECKS if (reason := check(rule, data)) is not None), None)


def validate_for(chart_type: ChartType, data: ChartData) -> None:
    reason = violation(chart_type, data)
    if reason is not None:
        raise ChartTypeMismatchError(reason, details={"chart_type": chart_type.value})


def _subject(rule: ChartRule) -> str:
    return f"A {rule.chart_type.value.replace('_', ' ')} chart"


def _category_cap(rule: ChartRule, data: ChartData) -> str | None:
    if rule.max_categories is None or len(data.categories) <= rule.max_categories:
        return None
    limit, actual = rule.max_categories, len(data.categories)
    return f"{_subject(rule)} supports at most {limit} categories; this data has {actual}"


def _single_series(rule: ChartRule, data: ChartData) -> str | None:
    if not rule.requires_single_series or len(data.series) == 1:
        return None
    return f"{_subject(rule)} needs exactly one series; this data has {len(data.series)}"


def _non_negative(rule: ChartRule, data: ChartData) -> str | None:
    if not rule.requires_non_negative:
        return None
    for series in data.series:
        negative = next((value for value in series.values if value is not None and value < 0), None)
        if negative is not None:
            return (
                f"{_subject(rule)} cannot show negative values; found {negative:g} in series '{series.name}'"
            )
    return None


def _no_gaps(rule: ChartRule, data: ChartData) -> str | None:
    if rule.allows_gaps:
        return None
    for series in data.series:
        for category, value in zip(data.categories, series.values, strict=True):
            if value is None:
                where = f"series '{series.name}' is empty at category '{category}'"
                return f"{_subject(rule)} cannot have empty values; {where}"
    return None


_CHECKS: tuple[Callable[[ChartRule, ChartData], str | None], ...] = (
    _category_cap,
    _single_series,
    _non_negative,
    _no_gaps,
)
