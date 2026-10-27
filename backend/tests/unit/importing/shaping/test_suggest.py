import pytest

from app.charts.chart_data import ChartData, Series
from app.core.enums import ChartType
from app.importing.shaping.shaper import ColumnMapping, ShapedTable
from app.importing.shaping.suggest import suggest_chart_type

MAPPING = ColumnMapping(categories="c", series=None, values=("v",))


def shaped(category_count: int, series_count: int, *, are_dates: bool = False) -> ShapedTable:
    data = ChartData(
        categories=[f"c{index}" for index in range(category_count)],
        series=[Series(name=f"s{index}", values=[1.0] * category_count) for index in range(series_count)],
    )
    return ShapedTable(MAPPING, data, row_count=category_count, categories_are_dates=are_dates)


@pytest.mark.parametrize(
    ("table", "expected"),
    [
        (shaped(30, 3, are_dates=True), ChartType.LINE),
        (shaped(5, 1), ChartType.PIE),
        (shaped(21, 1), ChartType.BAR),
        (shaped(5, 3), ChartType.STACKED_BAR),
        (shaped(101, 3), None),
    ],
)
def test_suggest_picks_first_fitting_chart_type(table: ShapedTable, expected: ChartType | None) -> None:
    assert suggest_chart_type(table) == expected
