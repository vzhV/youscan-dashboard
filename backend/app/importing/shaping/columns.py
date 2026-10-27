import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from app.importing.table import Cell, Table, cell_text

ID_COLUMN_NAME = "id"
PLAIN_NUMBER = re.compile(r"-?\d+(\.\d+)?")
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
# Thousands separators seen in practice: comma, dot, space, no-break/narrow/thin spaces, apostrophe.
_SEPARATORS = r",. \u00a0\u202f\u2009'"
# "1,137" or "1 137" look numeric but would silently become text, so they are reported, not guessed.
# Only real grouping (groups of exactly three digits) or a decimal comma counts, so "28.10.2024" and
# "555 1234" are not mistaken for numbers.
# A trailing % ("12%") is the same kind of typo: it reads as text and would silently drop the column.
GROUPED_NUMBER = re.compile(rf"-?((\d{{1,3}}([{_SEPARATORS}]\d{{3}})+([.,]\d+)?|\d+,\d+)%?|\d+([.,]\d+)?%)")


class ColumnKind(StrEnum):
    DATE = "date"
    NUMBER = "number"
    TEXT = "text"
    EMPTY = "empty"


@dataclass(frozen=True)
class CellIssue:
    column: str
    row: int
    value: str
    expected: ColumnKind


@dataclass(frozen=True)
class ColumnProfile:
    name: str
    index: int
    kind: ColumnKind
    is_ignored: bool
    first_invalid: CellIssue | None


@dataclass(frozen=True)
class _Entry:
    row: int
    cell: Cell


def to_number(cell: Cell) -> float | None:
    number = cell if isinstance(cell, float) else None
    if isinstance(cell, str) and PLAIN_NUMBER.fullmatch(cell):
        number = float(cell)
    # float("9" * 400) is inf, which JSON and charts cannot carry.
    return number if number is not None and math.isfinite(number) else None


def to_date(cell: Cell) -> date | None:
    """Categories are daily, so the time of day is dropped; two times on one day then count as a duplicate."""
    if isinstance(cell, datetime):
        return cell.date()
    if isinstance(cell, str) and ISO_DATE.fullmatch(cell):
        try:
            return date.fromisoformat(cell)
        except ValueError:
            return None
    return None


def profile_columns(table: Table) -> list[ColumnProfile]:
    return [_profile(table, index, name) for index, name in enumerate(table.header)]


def _profile(table: Table, index: int, name: str) -> ColumnProfile:
    entries = [_Entry(row.number, cell) for row in table.rows if (cell := row.cells[index]) is not None]
    kind = _kind_of(entries)
    is_ignored = kind is ColumnKind.EMPTY or name.lower() == ID_COLUMN_NAME
    first_invalid = None if is_ignored or kind is not ColumnKind.TEXT else _first_invalid(name, entries)
    return ColumnProfile(name, index, kind, is_ignored, first_invalid)


def _kind_of(entries: Sequence[_Entry]) -> ColumnKind:
    if not entries:
        return ColumnKind.EMPTY
    if all(to_number(entry.cell) is not None for entry in entries):
        return ColumnKind.NUMBER
    if all(to_date(entry.cell) is not None for entry in entries):
        return ColumnKind.DATE
    return ColumnKind.TEXT


def _first_invalid(name: str, entries: Sequence[_Entry]) -> CellIssue | None:
    expected = _expected_kind(entries)
    if expected is None:
        return None
    parse = to_number if expected is ColumnKind.NUMBER else to_date
    offenders = (entry for entry in entries if parse(entry.cell) is None)
    return next((CellIssue(name, entry.row, cell_text(entry.cell), expected) for entry in offenders), None)


def _expected_kind(entries: Sequence[_Entry]) -> ColumnKind | None:
    """The kind most cells aim for, if more than half do; a lone stray word is then the likely culprit."""
    number_like = sum(_is_number_like(entry.cell) for entry in entries)
    if number_like * 2 > len(entries):
        return ColumnKind.NUMBER
    date_like = sum(to_date(entry.cell) is not None for entry in entries)
    if date_like * 2 > len(entries):
        return ColumnKind.DATE
    return None


def _is_number_like(cell: Cell) -> bool:
    return to_number(cell) is not None or (
        isinstance(cell, str) and GROUPED_NUMBER.fullmatch(cell) is not None
    )
