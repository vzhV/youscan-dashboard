from collections.abc import Iterator
from datetime import date, datetime

import pytest

from app.core.errors import LimitExceededError
from app.importing.limits import ImportLimits
from app.importing.table import Cell, build_table, cell_text, normalize_cell


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("   ", None),
        ("  x ", "x"),
        (True, "True"),
        (3, 3.0),
        (2.5, 2.5),
        (datetime(2024, 1, 2, 3), datetime(2024, 1, 2, 3)),
        (date(2024, 1, 2), datetime(2024, 1, 2)),
        (b"x", "b'x'"),
    ],
)
def test_normalize_cell_converts_value(value: object, expected: Cell) -> None:
    assert normalize_cell(value) == expected


def test_build_table_row_limit_stops_reading_before_all_rows_are_loaded() -> None:
    pulled: list[int] = []

    def rows() -> Iterator[tuple[int, list[object]]]:
        for number in range(1, 1001):
            pulled.append(number)
            yield number, [number]

    with pytest.raises(LimitExceededError):
        build_table("S", rows(), ImportLimits(max_rows=2))

    assert len(pulled) == 4


@pytest.mark.parametrize(
    ("cell", "expected"),
    [
        (2023.0, "2023"),
        (2.5, "2.5"),
        ("Q1", "Q1"),
        (datetime(2024, 10, 28), "2024-10-28"),
        (datetime(2024, 10, 28, 13, 30), "2024-10-28T13:30:00"),
    ],
)
def test_cell_text_renders_cell_as_label(cell: Cell, expected: str) -> None:
    assert cell_text(cell) == expected
