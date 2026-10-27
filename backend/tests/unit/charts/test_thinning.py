import random

import pytest

from app.charts.chart_data import ChartData, Series
from app.charts.thinning import MAX_DISPLAY_POINTS, thin

SEED = 7
LARGE_COUNT = 20_000
SPIKE_INDEX = 12_345
SPIKE_VALUE = 10_000.0
SPIKE_SERIES = 2
TRAILING_GAP = 5_000
MANY_SERIES = 50
SMALL_MAX_POINTS = 100


def walk(count: int, rng: random.Random) -> list[float | None]:
    value = 0.0
    values: list[float | None] = []
    for _ in range(count):
        value += rng.uniform(-1, 1)
        values.append(value)
    return values


def build(series_count: int, count: int) -> ChartData:
    rng = random.Random(SEED)  # noqa: S311 - seeded for deterministic tests, not security
    return ChartData(
        categories=[f"c{index}" for index in range(count)],
        series=[Series(name=f"s{number}", values=walk(count, rng)) for number in range(series_count)],
    )


def test_thin_within_budget_returns_same_object() -> None:
    data = build(2, MAX_DISPLAY_POINTS)

    assert thin(data) is data


def test_thin_large_input_caps_categories() -> None:
    assert len(thin(build(5, LARGE_COUNT)).categories) <= MAX_DISPLAY_POINTS


def test_thin_fifty_series_never_exceeds_max_points() -> None:
    assert len(thin(build(MANY_SERIES, LARGE_COUNT)).categories) <= MAX_DISPLAY_POINTS


def test_thin_keeps_first_and_last_category() -> None:
    thinned = thin(build(3, LARGE_COUNT))

    assert thinned.categories[0] == "c0"
    assert thinned.categories[-1] == f"c{LARGE_COUNT - 1}"


def test_thin_keeps_spike_in_a_series() -> None:
    data = build(5, LARGE_COUNT)
    spiked = data.series[SPIKE_SERIES].values.copy()
    spiked[SPIKE_INDEX] = SPIKE_VALUE
    series = [*data.series]
    series[SPIKE_SERIES] = Series(name="spiked", values=spiked)

    thinned = thin(ChartData(categories=data.categories, series=series))

    position = thinned.categories.index(f"c{SPIKE_INDEX}")
    assert thinned.series[SPIKE_SERIES].values[position] == SPIKE_VALUE


def test_thin_keeps_series_aligned_with_categories() -> None:
    thinned = thin(build(5, LARGE_COUNT))

    assert all(len(series.values) == len(thinned.categories) for series in thinned.series)


def test_thin_series_with_trailing_gaps_keeps_its_real_points() -> None:
    data = build(2, LARGE_COUNT)
    gapped = [*data.series[0].values[:-TRAILING_GAP], *[None] * TRAILING_GAP]
    series = [Series(name="gapped", values=gapped), data.series[1]]

    thinned = thin(ChartData(categories=data.categories, series=series))

    last_real_label = f"c{LARGE_COUNT - TRAILING_GAP - 1}"
    position = thinned.categories.index(last_real_label)
    assert thinned.series[0].values[position] == data.series[0].values[LARGE_COUNT - TRAILING_GAP - 1]


def test_thin_preserves_values_at_kept_indices() -> None:
    data = build(2, LARGE_COUNT)

    thinned = thin(data)

    for kept, label in enumerate(thinned.categories):
        original = int(label.removeprefix("c"))
        assert thinned.series[0].values[kept] == data.series[0].values[original]


def test_thin_sparse_series_keeps_all_its_non_null_points() -> None:
    sparse_index = 777
    sparse: list[float | None] = [None] * LARGE_COUNT
    sparse[sparse_index] = 1.0
    data = ChartData(
        categories=[f"c{index}" for index in range(LARGE_COUNT)],
        series=[Series(name="sparse", values=sparse)],
    )

    thinned = thin(data)

    assert f"c{sparse_index}" in thinned.categories


def test_thin_all_null_series_stays_aligned_and_within_cap() -> None:
    data = build(1, LARGE_COUNT)
    dead = Series(name="dead", values=[None] * LARGE_COUNT)

    thinned = thin(ChartData(categories=data.categories, series=[data.series[0], dead]))

    assert len(thinned.categories) <= MAX_DISPLAY_POINTS
    assert all(len(series.values) == len(thinned.categories) for series in thinned.series)
    assert set(thinned.series[1].values) == {None}


def test_thin_one_over_max_points_is_thinned_within_cap() -> None:
    data = build(2, SMALL_MAX_POINTS + 1)

    thinned = thin(data, SMALL_MAX_POINTS)

    assert len(thinned.categories) < len(data.categories)
    assert len(thinned.categories) <= SMALL_MAX_POINTS


def test_thin_without_series_is_rejected() -> None:
    data = ChartData(categories=[f"c{index}" for index in range(MAX_DISPLAY_POINTS + 1)], series=[])

    with pytest.raises(ValueError, match="without series"):
        thin(data)
