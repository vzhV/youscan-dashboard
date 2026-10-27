from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from openpyxl.utils import get_column_letter

from app.core.errors import LimitExceededError
from app.importing.location import describe_source

LimitName = Literal["max_sheets", "max_columns", "max_rows", "max_series"]


@dataclass(frozen=True)
class ImportLimits:
    max_sheets: int = 20
    max_columns: int = 50
    max_rows: int = 100_000
    max_series: int = 50


DEFAULT_LIMITS = ImportLimits()

# Rows and columns are checked while streaming, so `actual` below is what was seen when reading
# stopped (a lower bound), and the messages point at where the data is rather than at a total.


def too_many_sheets(allowed: int, actual: int) -> LimitExceededError:
    message = f"File has more than {allowed:,} sheets, the maximum allowed"
    return _exceeded("max_sheets", message, {"allowed": allowed, "actual": actual, "sheet": None})


def too_many_rows(sheet: str | None, allowed: int, actual: int, row: int) -> LimitExceededError:
    where = f"{describe_source(sheet)} has more than {allowed:,} data rows"
    message = f"{where}, the maximum allowed (reached at row {row})"
    return _exceeded("max_rows", message, {"allowed": allowed, "actual": actual, "sheet": sheet, "row": row})


def too_many_columns(sheet: str | None, allowed: int, width: int, row: int) -> LimitExceededError:
    letter = get_column_letter(width)
    where = f"{describe_source(sheet)} has data in column {letter} (row {row})"
    message = f"{where}; at most {allowed:,} columns are allowed"
    details = {"allowed": allowed, "actual": width, "sheet": sheet, "column": letter, "row": row}
    return _exceeded("max_columns", message, details)


def too_many_series(sheet: str | None, allowed: int, column: str, row: int) -> LimitExceededError:
    # The pivot allocates dates x series values, so the series count is capped before it is built.
    where = f"{describe_source(sheet)} has more than {allowed:,} distinct values in column '{column}'"
    message = f"{where} (one series each), the maximum allowed (reached at row {row})"
    details = {"allowed": allowed, "sheet": sheet, "column": column, "row": row}
    return _exceeded("max_series", message, details)


def _exceeded(limit: LimitName, message: str, details: Mapping[str, object]) -> LimitExceededError:
    return LimitExceededError(message, details={"limit": limit, **details})
