import pytest

from app.core.errors import InvalidFileError, LimitExceededError
from app.importing.limits import ImportLimits
from app.importing.reader import read_tables
from app.importing.source_file import SourceFile
from tests.factories import make_xlsx


def test_read_tables_empty_file_raises_invalid_file() -> None:
    with pytest.raises(InvalidFileError, match="File contains no data"):
        read_tables(SourceFile("a.csv", b""))


def test_read_tables_returns_parsed_tables() -> None:
    tables = read_tables(SourceFile("a.csv", b"A,B\n1,2\n"))

    assert tables[0].header == ("A", "B")


@pytest.mark.parametrize(
    ("limits", "limit_name", "message"),
    [
        (ImportLimits(max_sheets=1), "max_sheets", "File has more than 1 sheets, the maximum allowed"),
        (
            ImportLimits(max_columns=1),
            "max_columns",
            "Sheet 'one' has data in column B (row 1); at most 1 columns are allowed",
        ),
        (
            ImportLimits(max_rows=1),
            "max_rows",
            "Sheet 'one' has more than 1 data rows, the maximum allowed (reached at row 3)",
        ),
    ],
)
def test_read_tables_enforces_sheet_column_and_row_limits(
    limits: ImportLimits, limit_name: str, message: str
) -> None:
    content = make_xlsx({"one": [["A", "B"], [1, 2], [3, 4]], "two": [["A", "B"], [1, 2]]})

    with pytest.raises(LimitExceededError) as error:
        read_tables(SourceFile("a.xlsx", content), limits=limits)

    assert error.value.message == message
    assert error.value.details is not None
    assert error.value.details["limit"] == limit_name
    assert error.value.details["allowed"] == 1
    assert error.value.details["sheet"] == (None if limit_name == "max_sheets" else "one")
