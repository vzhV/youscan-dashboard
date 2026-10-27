import random
from datetime import date, timedelta
from itertools import pairwise

import pytest

from app.charts.chart_data import ChartData
from app.charts.random_data import (
    BAR_MAX_CATEGORIES,
    BAR_MIN_CATEGORIES,
    CATEGORY_NAMES,
    GENERATORS,
    LINE_MAX_POINTS,
    LINE_MAX_SERIES,
    LINE_MIN_POINTS,
    LINE_MIN_SERIES,
    LINE_WALK_MAX,
    LINE_WALK_MIN,
    MAX_GENERATED_POINTS,
    PIE_MAX_CATEGORIES,
    PIE_MIN_CATEGORIES,
    STACKED_CATEGORY_COUNT,
    STACKED_SERIES_NAMES,
    generate_chart_data,
    generate_line_data,
)
from app.core.enums import ChartType
from app.importing.shaping.chart_rules import validate_for

TODAY = date(2026, 10, 27)
SEED = 42
SEED_COUNT = 20


def seeded_rng(seed: int = SEED) -> random.Random:
    return random.Random(seed)  # noqa: S311 - seeded for deterministic tests, not security


def generate(chart_type: ChartType, seed: int = SEED) -> ChartData:
    return generate_chart_data(chart_type, seeded_rng(seed), TODAY)


def is_positive_integer(value: float | None) -> bool:
    return value is not None and value > 0 and value == int(value)


def test_generators_cover_every_chart_type() -> None:
    assert set(GENERATORS) == set(ChartType)


@pytest.mark.parametrize("chart_type", list(ChartType))
def test_generate_same_seed_is_deterministic(chart_type: ChartType) -> None:
    assert generate(chart_type) == generate(chart_type)


def test_category_names_has_enough_distinct_labels() -> None:
    assert len(set(CATEGORY_NAMES)) == len(CATEGORY_NAMES) >= BAR_MAX_CATEGORIES
    assert CATEGORY_NAMES[:2] == ("Alpha", "Bravo")


def test_line_dates_are_weekly_and_end_today() -> None:
    dates = [date.fromisoformat(label) for label in generate(ChartType.LINE).categories]

    assert dates[-1] == TODAY
    assert {later - earlier for earlier, later in pairwise(dates)} == {timedelta(weeks=1)}
    assert LINE_MIN_POINTS <= len(dates) <= LINE_MAX_POINTS


def test_line_has_bounded_series_count() -> None:
    assert LINE_MIN_SERIES <= len(generate(ChartType.LINE).series) <= LINE_MAX_SERIES


def test_line_values_stay_inside_walk_bounds() -> None:
    values = [value for series in generate(ChartType.LINE).series for value in series.values]

    assert all(value is not None and LINE_WALK_MIN <= value <= LINE_WALK_MAX for value in values)


def test_line_values_have_one_decimal() -> None:
    values = [value for series in generate(ChartType.LINE).series for value in series.values]

    assert all(value == round(value, 1) for value in values if value is not None)


def test_generate_line_data_uses_requested_series_and_points() -> None:
    data = generate_line_data(seeded_rng(), TODAY, series_count=3, points=20)

    assert [series.name for series in data.series] == ["Series 1", "Series 2", "Series 3"]
    assert len(data.categories) == 20


@pytest.mark.parametrize("points", [0, -1, MAX_GENERATED_POINTS + 1])
def test_generate_line_data_points_out_of_bounds_is_rejected(points: int) -> None:
    with pytest.raises(ValueError, match="points must be between"):
        generate_line_data(seeded_rng(), TODAY, series_count=1, points=points)


@pytest.mark.parametrize("series_count", [0, -1])
def test_generate_line_data_without_series_is_rejected(series_count: int) -> None:
    with pytest.raises(ValueError, match="series_count must be at least 1"):
        generate_line_data(seeded_rng(), TODAY, series_count=series_count, points=1)


def test_generate_line_data_at_max_points_spans_full_range_ending_today() -> None:
    data = generate_line_data(seeded_rng(), TODAY, series_count=1, points=MAX_GENERATED_POINTS)

    assert len(data.categories) == MAX_GENERATED_POINTS
    assert data.categories[-1] == TODAY.isoformat()


def test_bar_has_one_value_series_and_bounded_categories() -> None:
    data = generate(ChartType.BAR)

    assert [series.name for series in data.series] == ["Value"]
    assert BAR_MIN_CATEGORIES <= len(data.categories) <= BAR_MAX_CATEGORIES


def test_stacked_bar_has_three_named_series_over_five_categories() -> None:
    data = generate(ChartType.STACKED_BAR)

    assert tuple(series.name for series in data.series) == STACKED_SERIES_NAMES
    assert len(data.categories) == STACKED_CATEGORY_COUNT


def test_pie_has_bounded_categories() -> None:
    assert PIE_MIN_CATEGORIES <= len(generate(ChartType.PIE).categories) <= PIE_MAX_CATEGORIES


@pytest.mark.parametrize("chart_type", [ChartType.BAR, ChartType.STACKED_BAR, ChartType.PIE])
def test_categorical_values_are_positive_integers(chart_type: ChartType) -> None:
    values = [value for series in generate(chart_type).series for value in series.values]

    assert all(is_positive_integer(value) for value in values)


@pytest.mark.parametrize("seed", range(SEED_COUNT))
@pytest.mark.parametrize("chart_type", list(ChartType))
def test_generated_data_satisfies_its_chart_rule(chart_type: ChartType, seed: int) -> None:
    validate_for(chart_type, generate(chart_type, seed))
