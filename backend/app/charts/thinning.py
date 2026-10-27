from collections.abc import Sequence

from app.charts.chart_data import ChartData, Series

MAX_DISPLAY_POINTS = 1000
# Room kept for the shared first and last categories.
RESERVED_ENDPOINTS = 2
MIN_SERIES_BUDGET = 3
# LTTB always keeps the first and last point of a series and buckets the rest.
LTTB_FIXED_POINTS = 2

type Point = tuple[int, float]


def thin(data: ChartData, max_points: int = MAX_DISPLAY_POINTS) -> ChartData:
    """Downsample categories while keeping each series' visual shape.

    The result has at most `max_points` categories whenever
    `len(series) <= (max_points - 2) // MIN_SERIES_BUDGET`; beyond that the minimum budget may exceed it.
    Raises ValueError when thinning is needed but there are no series to pick points from.
    """
    category_count = len(data.categories)
    if category_count <= max_points:
        return data
    if not data.series:
        raise ValueError("Cannot thin data without series")
    budget = max(MIN_SERIES_BUDGET, (max_points - RESERVED_ENDPOINTS) // len(data.series))
    kept = {0, category_count - 1}
    for series in data.series:
        kept.update(_lttb_indices(_non_null_points(series), budget))
    indices = sorted(kept)
    return ChartData(
        categories=[data.categories[index] for index in indices],
        series=[
            Series(name=series.name, values=[series.values[index] for index in indices])
            for series in data.series
        ],
    )


def _non_null_points(series: Series) -> list[Point]:
    return [(index, value) for index, value in enumerate(series.values) if value is not None]


def _triangle_area(previous: Point, candidate: Point, following_average: tuple[float, float]) -> float:
    """Twice the triangle area; the factor does not change which candidate wins."""
    return abs(
        (previous[0] - following_average[0]) * (candidate[1] - previous[1])
        - (previous[0] - candidate[0]) * (following_average[1] - previous[1])
    )


def _average(points: Sequence[Point]) -> tuple[float, float]:
    return (sum(x for x, _ in points) / len(points), sum(y for _, y in points) / len(points))


def _lttb_indices(points: Sequence[Point], budget: int) -> list[int]:
    """Largest-Triangle-Three-Buckets: indices of the points that best preserve the line's visual shape."""
    if len(points) <= budget:
        return [index for index, _ in points]
    selected = [points[0][0]]
    bucket_size = (len(points) - LTTB_FIXED_POINTS) / (budget - LTTB_FIXED_POINTS)
    previous = points[0]
    for bucket in range(budget - LTTB_FIXED_POINTS):
        start, end = int(bucket * bucket_size) + 1, int((bucket + 1) * bucket_size) + 1
        following = points[end : min(int((bucket + 2) * bucket_size) + 1, len(points))] or [points[-1]]
        following_average = _average(following)
        previous = max(
            points[start:end], key=lambda candidate: _triangle_area(previous, candidate, following_average)
        )
        selected.append(previous[0])
    selected.append(points[-1][0])
    return selected
