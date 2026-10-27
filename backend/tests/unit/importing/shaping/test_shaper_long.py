from datetime import datetime

import pytest

from app.core.errors import DuplicatePointError, LimitExceededError, NotShapeableError
from app.importing.limits import ImportLimits
from app.importing.shaping.shaper import ColumnMapping, shape_table
from app.importing.table import Cell, Table
from tests.factories import make_table, seed_table

HEADER = ["Date", "Campaign", "Result"]


def day(number: int) -> datetime:
    return datetime(2024, 10, number)


def long_table(rows: list[list[Cell]]) -> Table:
    return make_table(HEADER, rows, name="S")


def test_long_format_pivots_seed_line_sheet() -> None:
    shaped = shape_table(seed_table("line-and-pie.xlsx", "line chart data"))

    assert shaped.mapping == ColumnMapping(categories="Date", series="Campaign", values=("Result",))
    assert len(shaped.data.categories) == 54
    assert (shaped.data.categories[0], shaped.data.categories[-1]) == ("2024-10-28", "2025-11-03")
    assert [s.name for s in shaped.data.series] == ["A", "B", "C", "D", "E"]
    series = {s.name: s.values for s in shaped.data.series}
    assert series["A"][:5] == [48, 50, 51, 52, 48]
    assert series["A"][48:] == [None] * 6
    assert series["E"].count(None) == 28
    assert None not in series["D"]
    assert shaped.row_count == 212
    assert shaped.categories_are_dates


def test_long_format_sorts_dates_and_keeps_series_in_first_appearance_order() -> None:
    shaped = shape_table(long_table([[day(2), "B", 1.0], [day(1), "A", 2.0]]))

    assert shaped.data.categories == ["2024-10-01", "2024-10-02"]
    assert [(s.name, s.values) for s in shaped.data.series] == [("B", [None, 1.0]), ("A", [2.0, None])]


def test_long_format_empty_value_cell_becomes_none() -> None:
    shaped = shape_table(long_table([[day(1), "A", None], [day(2), "A", 3.0]]))

    assert shaped.data.series[0].values == [None, 3.0]


def test_long_format_ignores_id_column() -> None:
    table = make_table(["id", *HEADER], [[1.0, day(1), "A", 2.0]])

    assert shape_table(table).data.series[0].values == [2.0]


def test_duplicate_date_series_pair_raises_duplicate_point() -> None:
    table = long_table([[day(28), "A", 1.0], [day(29), "A", 2.0], [day(28), "A", 3.0]])

    with pytest.raises(DuplicatePointError) as raised:
        shape_table(table)

    assert raised.value.details == {"category": "2024-10-28", "series": "A", "row": 4}


def test_long_format_empty_date_cell_raises_not_shapeable_with_row() -> None:
    with pytest.raises(NotShapeableError) as raised:
        shape_table(long_table([[day(1), "A", 1.0], [None, "A", 2.0]]))

    assert raised.value.details == {"row": 3}


def test_long_format_empty_series_name_raises_not_shapeable_with_row() -> None:
    with pytest.raises(NotShapeableError) as raised:
        shape_table(long_table([[day(1), "A", 1.0], [day(2), None, 2.0]]))

    assert raised.value.details == {"row": 3}


def series_rows(count: int) -> list[list[Cell]]:
    return [[day(1), f"S{number}", 1.0] for number in range(count)]


def test_long_format_accepts_series_up_to_the_cap() -> None:
    shaped = shape_table(long_table(series_rows(3)), ImportLimits(max_series=3))

    assert len(shaped.data.series) == 3


def test_long_format_too_many_series_raises_limit_exceeded() -> None:
    with pytest.raises(LimitExceededError) as raised:
        shape_table(long_table(series_rows(4)), ImportLimits(max_series=3))

    assert raised.value.message == (
        "Sheet 'S' has more than 3 distinct values in column 'Campaign' (one series each), "
        "the maximum allowed (reached at row 5)"
    )
    assert raised.value.details == {
        "limit": "max_series",
        "allowed": 3,
        "sheet": "S",
        "column": "Campaign",
        "row": 5,
    }


def test_long_format_default_cap_allows_fifty_series() -> None:
    assert len(shape_table(long_table(series_rows(50))).data.series) == 50


def test_long_format_default_cap_rejects_fifty_one_series() -> None:
    with pytest.raises(LimitExceededError):
        shape_table(long_table(series_rows(51)))


def test_long_format_same_day_different_times_are_duplicates() -> None:
    table = long_table([[datetime(2024, 10, 1, 8), "A", 1.0], [datetime(2024, 10, 1, 9), "A", 2.0]])

    with pytest.raises(DuplicatePointError):
        shape_table(table)


def test_flagged_column_in_long_looking_sheet_is_not_shaped_as_long() -> None:
    table = make_table(
        ["Date", "Positive", "Negative"],
        [
            [datetime(2024, 1, 1), "1,137", 1.0],
            [datetime(2024, 1, 2), "2,500", 2.0],
            [datetime(2024, 1, 3), "764", 3.0],
        ],
    )

    with pytest.raises(NotShapeableError, match="Column 'Positive', row 2: '1,137'"):
        shape_table(table)
