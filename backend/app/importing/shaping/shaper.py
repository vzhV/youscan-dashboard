from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from app.charts.chart_data import ChartData, Series
from app.importing.limits import DEFAULT_LIMITS, ImportLimits, too_many_series
from app.importing.shaping.columns import ColumnKind, ColumnProfile, profile_columns, to_date, to_number
from app.importing.shaping.errors import (
    HAS_NO_DATA_ROWS,
    NEEDS_CATEGORY_COLUMN,
    NEEDS_NUMBER_COLUMN,
    cells_do_not_match,
    duplicate_point,
    empty_cell,
    not_shapeable,
    unused_columns_reason,
)
from app.importing.table import Table, cell_text

LONG_FORMAT_KINDS = frozenset({ColumnKind.DATE, ColumnKind.TEXT, ColumnKind.NUMBER})


@dataclass(frozen=True)
class ColumnMapping:
    categories: str
    series: str | None
    values: tuple[str, ...]


@dataclass(frozen=True)
class ShapedTable:
    mapping: ColumnMapping
    data: ChartData
    row_count: int
    categories_are_dates: bool


@dataclass(frozen=True)
class _WideRow:
    label: str
    values: list[float | None]


@dataclass(frozen=True)
class _LongColumns:
    day: ColumnProfile
    series: ColumnProfile
    value: ColumnProfile


def shape_table(table: Table, limits: ImportLimits = DEFAULT_LIMITS) -> ShapedTable:
    profiles = profile_columns(table)
    active = [profile for profile in profiles if not profile.is_ignored]
    if not table.rows:
        raise not_shapeable(table, profiles, HAS_NO_DATA_ROWS)
    # A flagged column is a typo in numbers or dates; shaping around it would silently mis-chart the sheet.
    if any(profile.first_invalid is not None for profile in active):
        raise cells_do_not_match(table, profiles)
    numbers = [profile for profile in active if profile.kind is ColumnKind.NUMBER]
    if not numbers:
        raise not_shapeable(table, profiles, NEEDS_NUMBER_COLUMN)
    if len(active) == len(LONG_FORMAT_KINDS) and {profile.kind for profile in active} == LONG_FORMAT_KINDS:
        by_kind = {profile.kind: profile for profile in active}
        columns = _LongColumns(by_kind[ColumnKind.DATE], by_kind[ColumnKind.TEXT], by_kind[ColumnKind.NUMBER])
        return _shape_long(table, columns, limits)
    return _shape_wide(table, profiles, active, numbers)


def _shape_long(table: Table, columns: _LongColumns, limits: ImportLimits) -> ShapedTable:
    points = _collect_points(table, columns, limits)
    days = sorted({day for by_day in points.values() for day in by_day})
    series = [Series(name=name, values=[by_day.get(day) for day in days]) for name, by_day in points.items()]
    data = ChartData(categories=[day.isoformat() for day in days], series=series)
    mapping = ColumnMapping(columns.day.name, columns.series.name, (columns.value.name,))
    return ShapedTable(mapping, data, len(table.rows), categories_are_dates=True)


def _collect_points(
    table: Table, columns: _LongColumns, limits: ImportLimits
) -> dict[str, dict[date, float | None]]:
    points: dict[str, dict[date, float | None]] = {}
    for row in table.rows:
        day = to_date(row.cells[columns.day.index])
        if day is None:
            raise empty_cell(table, row.number, columns.day.name)
        name_cell = row.cells[columns.series.index]
        if name_cell is None:
            raise empty_cell(table, row.number, columns.series.name)
        series_name = cell_text(name_cell)
        # Checked on first sight, before the pivot densifies dates x series into a matrix.
        if series_name not in points and len(points) >= limits.max_series:
            raise too_many_series(table.name, limits.max_series, columns.series.name, row.number)
        by_day = points.setdefault(series_name, {})
        if day in by_day:
            raise duplicate_point(table, day.isoformat(), series_name, row.number)
        by_day[day] = to_number(row.cells[columns.value.index])
    return points


def _shape_wide(
    table: Table,
    profiles: Sequence[ColumnProfile],
    active: Sequence[ColumnProfile],
    numbers: Sequence[ColumnProfile],
) -> ShapedTable:
    category_column = _category_column(active)
    if category_column is None:
        raise not_shapeable(table, profiles, NEEDS_CATEGORY_COLUMN)
    unused = [
        profile
        for profile in active
        if profile is not category_column and profile.kind is not ColumnKind.NUMBER
    ]
    if unused:
        raise not_shapeable(table, profiles, unused_columns_reason(unused))
    is_dates = category_column.kind is ColumnKind.DATE
    rows = _wide_rows(table, category_column, numbers)
    if is_dates:
        # ISO labels sort chronologically as plain strings.
        rows.sort(key=lambda wide_row: wide_row.label)
    series = [
        Series(name=column.name, values=[row.values[position] for row in rows])
        for position, column in enumerate(numbers)
    ]
    data = ChartData(categories=[row.label for row in rows], series=series)
    mapping = ColumnMapping(category_column.name, None, tuple(column.name for column in numbers))
    return ShapedTable(mapping, data, len(table.rows), categories_are_dates=is_dates)


def _category_column(active: Sequence[ColumnProfile]) -> ColumnProfile | None:
    for kind in (ColumnKind.DATE, ColumnKind.TEXT):
        match = next((profile for profile in active if profile.kind is kind), None)
        if match is not None:
            return match
    return None


def _wide_rows(
    table: Table, category_column: ColumnProfile, numbers: Sequence[ColumnProfile]
) -> list[_WideRow]:
    seen: set[str] = set()
    rows: list[_WideRow] = []
    for row in table.rows:
        cell = row.cells[category_column.index]
        if cell is None:
            raise empty_cell(table, row.number, category_column.name)
        day = to_date(cell) if category_column.kind is ColumnKind.DATE else None
        label = cell_text(cell) if day is None else day.isoformat()
        if label in seen:
            raise duplicate_point(table, label, None, row.number)
        seen.add(label)
        rows.append(_WideRow(label, [to_number(row.cells[column.index]) for column in numbers]))
    return rows
