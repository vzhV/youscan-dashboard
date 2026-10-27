import pytest
from pydantic import ValidationError

from app.charts.chart_data import ChartData, Series, point_count


def test_chart_data_equal_lengths_is_valid() -> None:
    data = ChartData(categories=["A", "B"], series=[Series(name="S", values=[1, None])])

    assert data.series[0].values == [1, None]


def test_chart_data_series_length_mismatch_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Series 'S' has 1 values but there are 2 categories"):
        ChartData(categories=["A", "B"], series=[Series(name="S", values=[1])])


def test_point_count_multiplies_categories_by_series() -> None:
    data = ChartData(categories=["A", "B", "C"], series=[Series(name="S", values=[1, 2, 3])] * 2)

    assert point_count(data) == 6
