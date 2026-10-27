from datetime import datetime

import pytest

from app.core.errors import DuplicatePointError, NotShapeableError
from app.importing.shaping.shaper import ColumnMapping, shape_table
from tests.factories import make_table, seed_table


def test_wide_format_seed_csv() -> None:
    shaped = shape_table(seed_table("stacked-bar.csv"))

    assert shaped.mapping == ColumnMapping("Brand", None, ("Positive", "Neutral", "Negative"))
    assert shaped.data.categories == ["A", "B", "C", "D", "E"]
    assert [s.name for s in shaped.data.series] == ["Positive", "Neutral", "Negative"]
    assert shaped.data.series[0].values == [1137, 764, 927, 800, 672]
    assert shaped.row_count == 5
    assert not shaped.categories_are_dates


def test_wide_format_seed_pie_sheet() -> None:
    shaped = shape_table(seed_table("line-and-pie.xlsx", "pie chart data"))

    assert [(s.name, s.values) for s in shaped.data.series] == [("Result", [1895, 1699, 1782, 2105, 988])]


def test_wide_format_date_categories_are_sorted() -> None:
    table = make_table(["Day", "Sales"], [[datetime(2024, 3, 1), 3.0], [datetime(2024, 1, 1), 1.0]])

    shaped = shape_table(table)

    assert shaped.data.categories == ["2024-01-01", "2024-03-01"]
    assert shaped.data.series[0].values == [1.0, 3.0]
    assert shaped.categories_are_dates


def test_wide_format_text_categories_keep_row_order() -> None:
    shaped = shape_table(make_table(["Name", "N"], [["B", 1.0], ["A", 2.0]]))

    assert shaped.data.categories == ["B", "A"]


def test_empty_number_cell_becomes_none() -> None:
    table = make_table(["Name", "N", "M"], [["A", 1.0, 5.0], ["B", None, 6.0], ["C"]])

    shaped = shape_table(table)

    assert [s.values for s in shaped.data.series] == [[1.0, None, None], [5.0, 6.0, None]]


def test_thousands_separator_cell_makes_sheet_not_shapeable_and_names_cell() -> None:
    table = make_table(
        ["Brand", "Positive", "Neutral"], [["A", "1,137", "5"], ["B", "764", "6"], ["C", "900", "7"]]
    )

    with pytest.raises(NotShapeableError) as raised:
        shape_table(table)

    assert raised.value.details is not None
    assert raised.value.details["issues"] == [
        {"column": "Positive", "row": 2, "value": "1,137", "expected": "number"}
    ]
    assert "Column 'Positive', row 2: '1,137' is not a number" in raised.value.message


def test_unused_text_column_raises_not_shapeable_with_columns() -> None:
    table = make_table(["Brand", "Region", "N"], [["A", "x", 1.0]], name="Data")

    with pytest.raises(NotShapeableError) as raised:
        shape_table(table)

    assert raised.value.message.startswith("Sheet 'Data'")
    assert "'Region' (text)" in raised.value.message
    assert raised.value.details == {
        "columns": [
            {"name": "Brand", "kind": "text"},
            {"name": "Region", "kind": "text"},
            {"name": "N", "kind": "number"},
        ],
        "issues": [],
    }


def test_second_date_column_is_not_silently_dropped() -> None:
    table = make_table(["From", "To", "N"], [[datetime(2024, 1, 1), datetime(2024, 2, 1), 1.0]])

    with pytest.raises(NotShapeableError, match="'To' \\(date\\)"):
        shape_table(table)


def test_duplicate_wide_category_raises_duplicate_point() -> None:
    table = make_table(["Name", "N"], [["A", 1.0], ["B", 2.0], ["A", 3.0]])

    with pytest.raises(DuplicatePointError) as raised:
        shape_table(table)

    assert raised.value.details == {"category": "A", "series": None, "row": 4}


def test_empty_category_cell_raises_not_shapeable_with_row() -> None:
    table = make_table(["Name", "N"], [["A", 1.0], [None, 2.0]])

    with pytest.raises(NotShapeableError) as raised:
        shape_table(table)

    assert raised.value.details == {"row": 3}


def test_table_without_number_columns_raises_not_shapeable() -> None:
    with pytest.raises(NotShapeableError, match="File needs a number column"):
        shape_table(make_table(["A", "B"], [["x", "y"]]))


def test_table_without_category_column_raises_not_shapeable() -> None:
    with pytest.raises(NotShapeableError, match="needs a date or text column for the categories"):
        shape_table(make_table(["A", "B"], [[1.0, 2.0]]))


def test_nbsp_thousands_separator_makes_sheet_not_shapeable_and_names_row() -> None:
    table = make_table(["Brand", "Positive"], [["A", "1\u00a0137"], ["B", "764"]])

    with pytest.raises(NotShapeableError, match="Column 'Positive', row 2: '1\u00a0137' is not a number"):
        shape_table(table)


def test_percent_cells_make_sheet_not_shapeable_and_name_the_first_cell() -> None:
    table = make_table(["Brand", "Share"], [["A", "12%"], ["B", "30%"]])

    with pytest.raises(NotShapeableError, match="Column 'Share', row 2: '12%' is not a number"):
        shape_table(table)


def test_two_flagged_columns_list_both_issues_in_column_order() -> None:
    table = make_table(
        ["Brand", "Positive", "Neutral"],
        [["A", "1,137", "2,500"], ["B", "764", "3,100"], ["C", "900", "800"]],
        name="Data",
    )

    with pytest.raises(NotShapeableError) as raised:
        shape_table(table)

    assert raised.value.message == (
        "Sheet 'Data' cannot be shaped: Column 'Positive', row 2: '1,137' is not a number; "
        "Column 'Neutral', row 2: '2,500' is not a number"
    )


def test_flagged_column_is_not_used_as_category_labels() -> None:
    table = make_table(["Positive", "Neutral"], [["1,137", 1.0], ["764", 2.0]])

    with pytest.raises(NotShapeableError, match="Column 'Positive', row 2: '1,137'"):
        shape_table(table)


def test_flagged_date_column_is_not_shaped_as_text_categories() -> None:
    table = make_table(
        ["Date", "Sales"], [[datetime(2024, 1, 1), 1.0], ["soon", 2.0], [datetime(2024, 1, 3), 3.0]]
    )

    with pytest.raises(NotShapeableError, match="Column 'Date', row 3: 'soon' is not a date"):
        shape_table(table)


def test_header_only_sheet_raises_not_shapeable_with_no_data_rows() -> None:
    with pytest.raises(NotShapeableError, match="Sheet 'S' has no data rows"):
        shape_table(make_table(["Name", "N"], [], name="S"))
