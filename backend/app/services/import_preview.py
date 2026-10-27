from collections.abc import Sequence

import anyio.to_thread

from app.core.enums import ChartType
from app.core.errors import ChartTypeMismatchError, DomainError
from app.importing.parsers.registry import DEFAULT_REGISTRY, ParserRegistry
from app.importing.reader import read_tables
from app.importing.shaping.columns import ColumnKind, ColumnProfile, profile_columns, to_date, to_number
from app.importing.shaping.shaper import ShapedTable, shape_table
from app.importing.shaping.suggest import explain_no_suggestion, suggest_chart_type
from app.importing.source_file import SourceFile
from app.importing.table import Cell, Row, Table, cell_text
from app.schemas.common import ErrorBody
from app.schemas.imports import ColumnInfo, ColumnMappingRead, ImportPreview, SheetPreview

SAMPLE_ROW_COUNT = 5


async def preview_file(source: SourceFile, registry: ParserRegistry = DEFAULT_REGISTRY) -> ImportPreview:
    # Parsing and shaping are CPU-bound, so they run off the event loop.
    return await anyio.to_thread.run_sync(_read_preview, source, registry)


def _read_preview(source: SourceFile, registry: ParserRegistry) -> ImportPreview:
    return build_preview(source, read_tables(source, registry))


def build_preview(source: SourceFile, tables: Sequence[Table]) -> ImportPreview:
    """Describe every table of a file.

    Sheets with no data are omitted by the parsers, so they never appear: there is nothing to chart.
    """
    return ImportPreview(filename=source.filename, sheets=[_sheet_preview(table) for table in tables])


def _sheet_preview(table: Table) -> SheetPreview:
    profiles = profile_columns(table)
    suggestion, mapping, issue = _assess(table)
    return SheetPreview(
        sheet=table.name,
        row_count=len(table.rows),
        columns=[ColumnInfo(name=profile.name, kind=profile.kind) for profile in profiles],
        sample_rows=[_sample_row(row, profiles) for row in table.rows[:SAMPLE_ROW_COUNT]],
        suggested_chart_type=suggestion,
        mapping=mapping,
        issue=issue,
    )


def _assess(table: Table) -> tuple[ChartType | None, ColumnMappingRead | None, ErrorBody | None]:
    try:
        shaped = shape_table(table)
    except DomainError as error:
        # One bad sheet must not hide the others; the issue tells the user why it cannot be charted.
        return None, None, ErrorBody(code=error.code, message=error.message, details=_details(error))
    mapping = _mapping(shaped)
    suggestion = suggest_chart_type(shaped)
    if suggestion is None:
        reason = explain_no_suggestion(shaped)
        return None, mapping, ErrorBody(code=ChartTypeMismatchError.code, message=reason, details=None)
    return suggestion, mapping, None


def _mapping(shaped: ShapedTable) -> ColumnMappingRead:
    return ColumnMappingRead(
        categories=shaped.mapping.categories,
        series=shaped.mapping.series,
        values=list(shaped.mapping.values),
    )


def _details(error: DomainError) -> dict[str, object] | None:
    return None if error.details is None else dict(error.details)


def _sample_row(row: Row, profiles: Sequence[ColumnProfile]) -> list[str | float | None]:
    return [_sample_cell(cell, profile.kind) for cell, profile in zip(row.cells, profiles, strict=True)]


def _sample_cell(cell: Cell, kind: ColumnKind) -> str | float | None:
    """Render by detected kind, so a CSV "1137" and an XLSX 1137 preview the same way."""
    if cell is None:
        return None
    if kind is ColumnKind.NUMBER:
        return to_number(cell)
    day = to_date(cell) if kind is ColumnKind.DATE else None
    return cell_text(cell) if day is None else day.isoformat()
