import pytest

from app.core.enums import ChartType, WidgetType, chart_type_of


@pytest.mark.parametrize("chart_type", list(ChartType))
def test_chart_type_of_maps_chart_widgets_to_the_same_named_chart_type(chart_type: ChartType) -> None:
    assert chart_type_of(WidgetType(chart_type.value)) is chart_type


def test_chart_type_of_text_widget_is_none() -> None:
    assert chart_type_of(WidgetType.TEXT) is None
