import pytest

from app.core.errors import InvalidFileError
from app.importing.limits import DEFAULT_LIMITS
from app.importing.parsers.csv_parser import CsvParser
from app.importing.table import Row, Table
from tests.factories import SEED_DATA_DIR


def parse_csv(content: bytes) -> list[Table]:
    return CsvParser().parse(content, DEFAULT_LIMITS)


def parse_single(content: bytes) -> Table:
    tables = parse_csv(content)
    assert len(tables) == 1
    return tables[0]


def test_csv_parses_seed_file() -> None:
    table = parse_single((SEED_DATA_DIR / "stacked-bar.csv").read_bytes())

    assert table.name is None
    assert table.header == ("Brand", "Positive", "Neutral", "Negative")
    assert len(table.rows) == 5
    assert table.rows[0] == Row(2, ("A", "1137", "531", "227"))


def test_csv_strips_utf8_bom() -> None:
    table = parse_single(b"\xef\xbb\xbfBrand,Value\nA,1\n")

    assert table.header == ("Brand", "Value")


def test_csv_sniffs_semicolon_delimiter() -> None:
    table = parse_single(b"Brand;Value\nA;1\nB;2\n")

    assert table.header == ("Brand", "Value")
    assert table.rows[1].cells == ("B", "2")


def test_csv_skips_blank_lines_and_drops_trailing_empty_columns() -> None:
    table = parse_single(b"Brand,Value,,\nA,1,,\n\n")

    assert table.header == ("Brand", "Value")
    assert len(table.rows) == 1


def test_csv_non_utf8_raises_invalid_file() -> None:
    with pytest.raises(InvalidFileError) as error:
        parse_csv("Brand\nCafé".encode("cp1252"))

    assert error.value.message == "File must be UTF-8 encoded. In Excel, save it as 'CSV UTF-8'."


def test_csv_header_only_returns_table_without_rows() -> None:
    table = parse_single(b"Brand,Value\n")

    assert table.rows == ()


def test_csv_data_under_empty_header_raises_invalid_file() -> None:
    with pytest.raises(InvalidFileError, match="File has data in column B but no header"):
        parse_csv(b"Brand,\nA,5\n")


def test_csv_empty_content_returns_no_tables() -> None:
    assert parse_csv(b"") == []


def test_csv_cr_only_line_endings_are_parsed() -> None:
    table = parse_single(b"Brand,Value\rA,1\r")

    assert table.rows == (Row(2, ("A", "1")),)


def test_csv_unterminated_quote_over_field_limit_raises_invalid_file() -> None:
    content = b'Brand,Value\nA,"' + b"x\n" * 100_000

    with pytest.raises(InvalidFileError, match="Could not read the CSV near line 2:"):
        parse_csv(content)


def test_csv_row_numbers_follow_lines_after_multiline_quoted_field() -> None:
    table = parse_single(b'A,B\n"l1\nl2",x\nB,y\n,oops')

    assert [row.number for row in table.rows] == [2, 4, 5]


def test_csv_duplicate_header_raises_invalid_file() -> None:
    with pytest.raises(InvalidFileError, match="File has a duplicate column 'A'"):
        parse_csv(b"A,A\n1,2\n")


def test_csv_integral_numeric_header_has_no_decimal_suffix() -> None:
    table = parse_single(b"2023,2024\n1,2\n")

    assert table.header == ("2023", "2024")
