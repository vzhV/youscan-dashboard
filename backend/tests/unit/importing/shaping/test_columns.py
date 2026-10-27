from datetime import date, datetime

import pytest

from app.importing.shaping.columns import (
    GROUPED_NUMBER,
    CellIssue,
    ColumnKind,
    profile_columns,
    to_date,
    to_number,
)
from app.importing.table import Cell
from tests.factories import make_table


@pytest.mark.parametrize(
    ("cell", "expected"),
    [
        (3.0, 3.0),
        ("9" * 400, None),
        (float("inf"), None),
        ("1137", 1137.0),
        ("-2.5", -2.5),
        ("1,137", None),
        ("n/a", None),
        ("", None),
        (None, None),
    ],
)
def test_to_number_accepts_only_plain_numbers(cell: Cell, expected: float | None) -> None:
    assert to_number(cell) == expected


@pytest.mark.parametrize(
    ("cell", "expected"),
    [
        (datetime(2024, 10, 28, 5), date(2024, 10, 28)),
        ("2024-10-28", date(2024, 10, 28)),
        ("2024-13-45", None),
        ("28/10/2024", None),
        (3.0, None),
        (None, None),
    ],
)
def test_to_date_accepts_datetimes_and_iso_strings(cell: Cell, expected: date | None) -> None:
    assert to_date(cell) == expected


def kinds(header: list[str], rows: list[list[Cell]]) -> list[ColumnKind]:
    return [profile.kind for profile in profile_columns(make_table(header, rows))]


def test_profile_number_cells_make_number_column() -> None:
    assert kinds(["n"], [[1.0], ["2"], [None]]) == [ColumnKind.NUMBER]


def test_profile_datetime_cells_make_date_column() -> None:
    assert kinds(["d"], [[datetime(2024, 1, 1)], [datetime(2024, 1, 2)]]) == [ColumnKind.DATE]


def test_iso_date_strings_count_as_dates() -> None:
    assert kinds(["d"], [["2024-01-01"], ["2024-01-02"]]) == [ColumnKind.DATE]


def test_profile_mixed_cells_make_text_column() -> None:
    assert kinds(["t"], [["A"], [1.0]]) == [ColumnKind.TEXT]


def test_profile_ignores_id_and_empty_columns() -> None:
    table = make_table(["ID", "Empty", "Value"], [[1.0, None, 5.0], [2.0, None, 6.0]])

    profiles = profile_columns(table)

    assert [(p.name, p.is_ignored) for p in profiles] == [("ID", True), ("Empty", True), ("Value", False)]
    assert profiles[1].kind is ColumnKind.EMPTY


def test_profile_mostly_numbers_with_one_word_reports_first_non_number() -> None:
    table = make_table(["Positive"], [["1"], ["2"], ["n/a"], ["4"]])

    (profile,) = profile_columns(table)

    assert profile.kind is ColumnKind.TEXT
    assert profile.first_invalid == CellIssue("Positive", 4, "n/a", ColumnKind.NUMBER)


def test_profile_column_of_separator_numbers_points_at_first_cell() -> None:
    table = make_table(["Positive"], [["1,137"], ["2,500"]])

    (profile,) = profile_columns(table)

    assert profile.first_invalid == CellIssue("Positive", 2, "1,137", ColumnKind.NUMBER)


def test_profile_mostly_dates_with_one_word_reports_first_non_date() -> None:
    table = make_table(["When"], [["2024-01-01"], ["soon"], [datetime(2024, 1, 3)]])

    (profile,) = profile_columns(table)

    assert profile.first_invalid == CellIssue("When", 3, "soon", ColumnKind.DATE)


def test_profile_mostly_text_column_has_no_first_invalid() -> None:
    table = make_table(["Name"], [["A"], ["B"], ["3"]])

    (profile,) = profile_columns(table)

    assert profile.first_invalid is None


def test_profile_valid_number_column_has_no_first_invalid() -> None:
    (profile,) = profile_columns(make_table(["n"], [[1.0], [2.0]]))

    assert profile.first_invalid is None


@pytest.mark.parametrize(
    "text",
    [
        "1,137",
        "1\u00a0137",
        "1\u202f137",
        "1\u2009137",
        "1 137",
        "1'137",
        "1.234.567",
        "12,5",
        "-2,500",
        "1,234.56",
        "12%",
        "12.5%",
        "1,137%",
    ],
)
def test_grouped_number_matches_real_thousands_grouping(text: str) -> None:
    assert GROUPED_NUMBER.fullmatch(text)


@pytest.mark.parametrize("text", ["28.10.2024", "1.2.3", "555 1234", "2024-10-28", "n/a"])
def test_grouped_number_rejects_non_numbers(text: str) -> None:
    assert GROUPED_NUMBER.fullmatch(text) is None
