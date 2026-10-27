from datetime import date, datetime
from io import BytesIO
from zipfile import BadZipFile, ZipFile

import pytest
from openpyxl.utils.exceptions import InvalidFileException

from app.core.errors import InvalidFileError, LimitExceededError
from app.importing.limits import DEFAULT_LIMITS, ImportLimits
from app.importing.parsers.xlsx_parser import XlsxParser
from app.importing.table import Row, Table
from tests.factories import SEED_DATA_DIR, make_xlsx, make_xlsx_with_cells, make_zip, replace_zip_member

SEED_XLSX = SEED_DATA_DIR / "line-and-pie.xlsx"


def parse_xlsx(content: bytes, limits: ImportLimits = DEFAULT_LIMITS) -> list[Table]:
    return XlsxParser().parse(content, limits)


def test_xlsx_parses_seed_sheet_names() -> None:
    tables = parse_xlsx(SEED_XLSX.read_bytes())

    assert [table.name for table in tables] == ["line chart data", "pie chart data"]


def test_xlsx_line_sheet_skips_blank_formatted_rows() -> None:
    line = parse_xlsx(SEED_XLSX.read_bytes())[0]

    assert line.header == ("id", "Campaign", "Date", "Result")
    assert len(line.rows) == 212
    assert line.rows[0] == Row(2, (1.0, "A", datetime(2024, 10, 28), 48.0))
    assert line.rows[-1].number == 213


def test_xlsx_pie_sheet_drops_empty_header_columns() -> None:
    pie = parse_xlsx(SEED_XLSX.read_bytes())[1]

    assert pie.header == ("Campaign", "Result")
    assert pie.rows[0].cells == ("A", 1895.0)


def test_xlsx_skips_empty_sheets() -> None:
    content = make_xlsx({"empty": [], "data": [["Name"], ["A"]]})

    assert [table.name for table in parse_xlsx(content)] == ["data"]


def test_xlsx_bool_and_date_cells_become_text_and_datetime() -> None:
    content = make_xlsx({"s": [["Flag", "Day"], [True, date(2024, 1, 2)]]})

    row = parse_xlsx(content)[0].rows[0]

    assert row.cells == ("True", datetime(2024, 1, 2))


def test_xlsx_corrupt_bytes_raise_invalid_file() -> None:
    with pytest.raises(InvalidFileError, match="not a valid .xlsx"):
        parse_xlsx(b"definitely not a workbook")


def test_xlsx_header_gap_error_names_sheet_and_column() -> None:
    content = make_xlsx_with_cells("Notes", [["A", "B"], ["x", "y"]], {"C5": "stray"})

    with pytest.raises(InvalidFileError) as error:
        parse_xlsx(content)

    assert error.value.message == "Sheet 'Notes' has data in column C but no header"
    assert error.value.details == {"sheet": "Notes", "column": "C"}


def test_xlsx_stray_far_right_cell_is_rejected_naming_its_column_and_row() -> None:
    content = make_xlsx_with_cells("S", [["A", "B"], [1, 2]], {"XFD4": "x"})

    with pytest.raises(LimitExceededError) as error:
        parse_xlsx(content, ImportLimits(max_columns=50))

    assert error.value.message == "Sheet 'S' has data in column XFD (row 4); at most 50 columns are allowed"
    assert error.value.details == {
        "limit": "max_columns",
        "allowed": 50,
        "actual": 16384,
        "sheet": "S",
        "column": "XFD",
        "row": 4,
    }


def test_xlsx_year_and_date_headers_render_as_text() -> None:
    content = make_xlsx({"S": [[2023, datetime(2024, 1, 1), datetime(2024, 1, 1, 8, 30)], [1, 2, 3]]})

    header = parse_xlsx(content)[0].header

    assert header == ("2023", "2024-01-01", "2024-01-01T08:30:00")


def test_xlsx_duplicate_header_names_sheet() -> None:
    content = make_xlsx({"Dupes": [["A", "A"], [1, 2]]})

    with pytest.raises(InvalidFileError, match="Sheet 'Dupes' has a duplicate column 'A'"):
        parse_xlsx(content)


def test_xlsx_truncated_sheet_xml_raises_invalid_file() -> None:
    valid = make_xlsx({"S": [["A"], [1], [2]]})
    broken = replace_zip_member(valid, "xl/worksheets/sheet1.xml", b"<worksheet><sheetData><row")

    with pytest.raises(InvalidFileError, match="not a valid .xlsx"):
        parse_xlsx(broken)


def test_xlsx_zip_without_workbook_part_raises_invalid_file() -> None:
    content = make_zip({"[Content_Types].xml": b"<Types/>"})

    with pytest.raises(InvalidFileError, match="not a valid .xlsx"):
        parse_xlsx(content)


@pytest.mark.parametrize("error", [KeyError("part"), InvalidFileException("bad"), BadZipFile("bad")])
def test_xlsx_loader_errors_raise_invalid_file(error: Exception, monkeypatch: pytest.MonkeyPatch) -> None:
    def failing_loader(*_args: object, **_kwargs: object) -> None:
        raise error

    # openpyxl is the boundary: these exceptions are only reachable with specific corrupt packages.
    monkeypatch.setattr("app.importing.parsers.xlsx_parser.load_workbook", failing_loader)

    with pytest.raises(InvalidFileError, match="not a valid .xlsx"):
        parse_xlsx(b"ignored")


def test_xlsx_bug_in_our_code_is_not_reported_as_invalid_file(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken_build_table(*_args: object, **_kwargs: object) -> None:
        raise KeyError("our bug")

    monkeypatch.setattr("app.importing.parsers.xlsx_parser.build_table", broken_build_table)

    with pytest.raises(KeyError):
        parse_xlsx(make_xlsx({"S": [["A"], [1]]}))


def test_xlsx_too_many_sheets_is_rejected_before_any_sheet_is_read() -> None:
    content = make_xlsx({"one": [["A"], [1]], "two": []})

    with pytest.raises(LimitExceededError, match="more than 1 sheets"):
        parse_xlsx(content, ImportLimits(max_sheets=1))


def test_xlsx_sheet_xml_cut_off_mid_stream_raises_invalid_file() -> None:
    # A normal (not write-only) workbook declares its <dimension> up front, so the cut surfaces
    # lazily while rows are streamed rather than when the workbook is opened.
    valid = make_xlsx_with_cells("S", [["A"]] + [[number] for number in range(200)], {})
    with ZipFile(BytesIO(valid)) as archive:
        sheet_xml = archive.read("xl/worksheets/sheet1.xml")
    broken = replace_zip_member(valid, "xl/worksheets/sheet1.xml", sheet_xml[: len(sheet_xml) // 2])

    with pytest.raises(InvalidFileError, match="not a valid .xlsx"):
        parse_xlsx(broken)


@pytest.mark.parametrize(
    ("original", "corrupted"),
    [
        (b"<v>1</v>", b"<v>abc</v>"),
        (b'r="A2"', b'r="??"'),
        (b'<row r="2"', b'<row r="x"'),
    ],
)
def test_xlsx_corrupt_cell_values_raise_invalid_file(original: bytes, corrupted: bytes) -> None:
    valid = make_xlsx_with_cells("S", [["A"], [1]], {})
    with ZipFile(BytesIO(valid)) as archive:
        sheet_xml = archive.read("xl/worksheets/sheet1.xml")
    assert original in sheet_xml
    broken = replace_zip_member(valid, "xl/worksheets/sheet1.xml", sheet_xml.replace(original, corrupted))

    with pytest.raises(InvalidFileError, match="not a valid .xlsx"):
        parse_xlsx(broken)
