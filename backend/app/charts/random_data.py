import random
from collections.abc import Callable, Mapping
from datetime import date, timedelta

from app.charts.chart_data import ChartData, Series
from app.core.enums import ChartType

CATEGORY_NAMES = (
    "Alpha",
    "Bravo",
    "Charlie",
    "Delta",
    "Echo",
    "Foxtrot",
    "Golf",
    "Hotel",
    "India",
    "Juliett",
)

# Matches the import row cap; weekly dates then reach back to roughly year 110, still a valid date.
MAX_GENERATED_POINTS = 100_000
LINE_MIN_POINTS = 12
LINE_MAX_POINTS = 52
LINE_MIN_SERIES = 2
LINE_MAX_SERIES = 4
LINE_WALK_MIN = 10.0
LINE_WALK_MAX = 100.0
LINE_WALK_STEP = 8.0
LINE_VALUE_DECIMALS = 1

BAR_MIN_CATEGORIES = 5
BAR_MAX_CATEGORIES = 8
BAR_SERIES_NAME = "Value"
BAR_VALUE_RANGE = (10, 1000)

STACKED_CATEGORY_COUNT = 5
STACKED_SERIES_NAMES = ("Positive", "Neutral", "Negative")
STACKED_VALUE_RANGE = (5, 500)

PIE_MIN_CATEGORIES = 4
PIE_MAX_CATEGORIES = 6
PIE_SERIES_NAME = "Share"
PIE_VALUE_RANGE = (1, 100)


def generate_chart_data(chart_type: ChartType, rng: random.Random, today: date) -> ChartData:
    return GENERATORS[chart_type](rng, today)


def _generate_line(rng: random.Random, today: date) -> ChartData:
    series_count = rng.randint(LINE_MIN_SERIES, LINE_MAX_SERIES)
    return generate_line_data(rng, today, series_count, rng.randint(LINE_MIN_POINTS, LINE_MAX_POINTS))


def _generate_bar(rng: random.Random, _today: date) -> ChartData:
    count = rng.randint(BAR_MIN_CATEGORIES, BAR_MAX_CATEGORIES)
    return _generate_categorical_data(rng, count, (BAR_SERIES_NAME,), BAR_VALUE_RANGE)


def _generate_stacked_bar(rng: random.Random, _today: date) -> ChartData:
    return _generate_categorical_data(rng, STACKED_CATEGORY_COUNT, STACKED_SERIES_NAMES, STACKED_VALUE_RANGE)


def _generate_pie(rng: random.Random, _today: date) -> ChartData:
    count = rng.randint(PIE_MIN_CATEGORIES, PIE_MAX_CATEGORIES)
    return _generate_categorical_data(rng, count, (PIE_SERIES_NAME,), PIE_VALUE_RANGE)


GENERATORS: Mapping[ChartType, Callable[[random.Random, date], ChartData]] = {
    ChartType.LINE: _generate_line,
    ChartType.BAR: _generate_bar,
    ChartType.STACKED_BAR: _generate_stacked_bar,
    ChartType.PIE: _generate_pie,
}


def generate_line_data(rng: random.Random, today: date, series_count: int, points: int) -> ChartData:
    """Weekly ISO dates ending at `today`, one bounded random walk per series.

    Raises ValueError unless 1 <= points <= MAX_GENERATED_POINTS and series_count >= 1.
    """
    if series_count < 1:
        raise ValueError(f"series_count must be at least 1, got {series_count}")
    if not 1 <= points <= MAX_GENERATED_POINTS:
        raise ValueError(f"points must be between 1 and {MAX_GENERATED_POINTS}, got {points}")
    first_day = today - timedelta(weeks=points - 1)
    return ChartData(
        categories=[(first_day + timedelta(weeks=week)).isoformat() for week in range(points)],
        series=[
            Series(name=f"Series {number}", values=_walk(rng, points))
            for number in range(1, series_count + 1)
        ],
    )


def _walk(rng: random.Random, points: int) -> list[float | None]:
    value = rng.uniform(LINE_WALK_MIN, LINE_WALK_MAX)
    values: list[float | None] = []
    for _ in range(points):
        value = min(LINE_WALK_MAX, max(LINE_WALK_MIN, value + rng.uniform(-LINE_WALK_STEP, LINE_WALK_STEP)))
        values.append(round(value, LINE_VALUE_DECIMALS))
    return values


def _generate_categorical_data(
    rng: random.Random, count: int, series_names: tuple[str, ...], value_range: tuple[int, int]
) -> ChartData:
    return ChartData(
        categories=list(CATEGORY_NAMES[:count]),
        series=[
            Series(name=name, values=[float(rng.randint(*value_range)) for _ in range(count)])
            for name in series_names
        ],
    )
