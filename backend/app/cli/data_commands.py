import asyncio
from pathlib import Path
from typing import Annotated

import typer

from app.cli.runtime import fail_with_message, open_session
from app.cli.selections import SelectionOptions, build_selections
from app.core.enums import ChartType
from app.core.errors import BoardNotEmptyError
from app.importing.source_file import SourceFile
from app.schemas.imports import ImportPreview, SheetPreview
from app.services.factories import build_dashboard_service, build_import_service
from app.services.import_preview import preview_file

commands = typer.Typer()

FileArgument = Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="An .xlsx or .csv file.")]


def _load(path: Path) -> SourceFile:
    return SourceFile(path.name, path.read_bytes())


def _format_sheet(sheet: SheetPreview) -> str:
    columns = ", ".join(f"{column.name} ({column.kind.value})" for column in sheet.columns)
    lines = [f"Sheet: {sheet.sheet or '(CSV)'}", f"  Rows: {sheet.row_count}", f"  Columns: {columns}"]
    if sheet.suggested_chart_type is not None:
        lines.append(f"  Suggested chart: {sheet.suggested_chart_type.value}")
    if sheet.mapping is not None:
        mapping = sheet.mapping
        values = ", ".join(mapping.values)
        lines.append(f"  Mapping: categories={mapping.categories}, series={mapping.series}, values={values}")
    if sheet.issue is not None:
        lines.append(f"  Issue: {sheet.issue.message}")
    return "\n".join(lines)


def _format_preview(preview: ImportPreview) -> str:
    return "\n\n".join([preview.filename, *(_format_sheet(sheet) for sheet in preview.sheets)])


@commands.command("inspect")
@fail_with_message
def inspect_file(file: FileArgument) -> None:
    """Show each sheet's columns, suggested chart type and column mapping. Stores nothing."""
    preview = asyncio.run(preview_file(_load(file)))
    typer.echo(_format_preview(preview))


async def _import(source: SourceFile, options: SelectionOptions) -> int:
    async with open_session() as session:
        selections = build_selections(await preview_file(source), options)
        return len((await build_import_service(session).import_file(source, selections)).widgets)


@commands.command("import")
@fail_with_message
def import_file(
    file: FileArgument,
    sheet: Annotated[list[str] | None, typer.Option(help="Sheet to import; repeat for several.")] = None,
    chart: Annotated[
        list[ChartType] | None,
        typer.Option(help="Chart type per sheet; targets the first sheet when --sheet is omitted."),
    ] = None,
    title: Annotated[
        list[str] | None,
        typer.Option(help="Widget title per sheet; targets the first sheet when --sheet is omitted."),
    ] = None,
) -> None:
    """Import sheets as widgets. Options are matched by position; with none, every chartable sheet is used."""
    options = SelectionOptions(sheet or [], chart or [], title or [])
    count = asyncio.run(_import(_load(file), options))
    typer.echo(f"Imported {count} widgets")


async def _seed(is_reset: bool) -> int:
    async with open_session() as session:
        dashboard = build_dashboard_service(session)
        try:
            widgets = await (dashboard.reset() if is_reset else dashboard.seed())
        except BoardNotEmptyError as error:
            # The hint names a CLI flag, so it belongs here rather than in the service.
            raise BoardNotEmptyError(f"{error.message}. Use --reset to replace it.") from error
        return len(widgets)


@commands.command("seed")
@fail_with_message
def seed(
    reset: Annotated[
        bool, typer.Option("--reset", help="Replace the whole board with the seed data.")
    ] = False,
) -> None:
    """Import the sample files. Refuses a non-empty board unless --reset is given."""
    count = asyncio.run(_seed(reset))
    typer.echo(f"Seeded {count} widgets")
