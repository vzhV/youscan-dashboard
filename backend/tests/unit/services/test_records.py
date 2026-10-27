import random
from datetime import date

from app.charts.random_data import generate_line_data
from app.charts.thinning import MAX_DISPLAY_POINTS
from app.core.enums import ChartType, DatasetOrigin
from app.services.records import DatasetSpec, new_dataset

LARGE_POINT_COUNT = 1_500


def test_new_dataset_thins_display_data_but_keeps_full_data() -> None:
    rng = random.Random(7)  # noqa: S311  # seeded test data, not cryptography
    data = generate_line_data(rng, date(2026, 10, 27), series_count=1, points=LARGE_POINT_COUNT)
    spec = DatasetSpec(
        name="big",
        origin=DatasetOrigin.GENERATED,
        chart_type=ChartType.LINE,
        data=data,
        row_count=LARGE_POINT_COUNT,
    )

    dataset = new_dataset(spec)

    assert len(dataset.data["categories"]) == LARGE_POINT_COUNT
    assert len(dataset.display_data["categories"]) <= MAX_DISPLAY_POINTS
