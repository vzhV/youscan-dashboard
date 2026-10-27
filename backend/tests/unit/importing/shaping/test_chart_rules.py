import pytest

from app.charts.chart_data import ChartData, Series
from app.core.enums import ChartType
from app.core.errors import ChartTypeMismatchError
from app.importing.shaping.chart_rules import validate_for, violation

LINE_CATEGORY_COUNT = 5000


def chart(*series_values: list[float | None]) -> ChartData:
    """Categories c0, c1, ... sized to the first series; every series must be that long."""
    return ChartData(
        categories=[f"c{index}" for index in range(len(series_values[0]))],
        series=[Series(name=f"s{index}", values=values) for index, values in enumerate(series_values)],
    )


def flat(category_count: int, value: float | None = 1) -> ChartData:
    return chart([value] * category_count)


@pytest.mark.parametrize(
    ("data", "expected_reason"),
    [
        (chart([1, 2], [3, 4]), "A pie chart needs exactly one series; this data has 2"),
        (chart([1, -3]), "A pie chart cannot show negative values; found -3 in series 's0'"),
        (chart([1, None]), "A pie chart cannot have empty values; series 's0' is empty at category 'c1'"),
        (flat(21), "A pie chart supports at most 20 categories; this data has 21"),
    ],
)
def test_pie_rule_violations(data: ChartData, expected_reason: str) -> None:
    assert violation(ChartType.PIE, data) == expected_reason


def test_pie_accepts_single_non_negative_series() -> None:
    values: list[float | None] = [0, 5] * 10
    assert violation(ChartType.PIE, chart(values)) is None


@pytest.mark.parametrize("chart_type", [ChartType.BAR, ChartType.STACKED_BAR])
def test_bar_rules_reject_101_categories(chart_type: ChartType) -> None:
    reason = violation(chart_type, flat(101))

    assert reason is not None
    assert "at most 100 categories; this data has 101" in reason


def test_bar_rules_allow_gaps_and_negatives() -> None:
    assert violation(ChartType.BAR, chart([None, -1, 2], [1, 1, 1])) is None


def test_line_accepts_5000_categories() -> None:
    assert violation(ChartType.LINE, chart([1] * LINE_CATEGORY_COUNT, [2] * LINE_CATEGORY_COUNT)) is None


def test_validate_for_raises_chart_type_mismatch_with_reason() -> None:
    with pytest.raises(ChartTypeMismatchError) as raised:
        validate_for(ChartType.PIE, chart([1, 2], [3, 4]))

    assert raised.value.message == "A pie chart needs exactly one series; this data has 2"
    assert raised.value.details == {"chart_type": "pie"}


def test_validate_for_passes_when_data_fits() -> None:
    validate_for(ChartType.LINE, flat(3))
