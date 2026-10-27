from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from pydantic import ValidationError

from app.core.enums import ChartType
from app.core.errors import DomainValidationError
from app.importing.location import describe_source
from app.importing.sheets import sheet_not_found
from app.schemas.imports import ImportPreview, ImportSelection, SheetPreview

OPTION_BY_FIELD: Mapping[str, str] = {"sheet": "--sheet", "chart_type": "--chart", "title": "--title"}


@dataclass(frozen=True)
class SelectionOptions:
    """The repeated `--sheet`, `--chart` and `--title` options; each is empty or one entry per selection."""

    sheets: Sequence[str]
    charts: Sequence[ChartType]
    titles: Sequence[str]


def build_selections(preview: ImportPreview, options: SelectionOptions) -> list[ImportSelection]:
    lengths = {len(values) for values in (options.sheets, options.charts, options.titles) if values}
    if not lengths:
        return _suggested_selections(preview)
    if len(lengths) > 1:
        raise DomainValidationError("--sheet, --chart and --title must be given the same number of times")
    count = lengths.pop()
    return [_selection_at(preview, options, index) for index in range(count)]


def _suggested_selections(preview: ImportPreview) -> list[ImportSelection]:
    selections = [
        ImportSelection(sheet=sheet.sheet, chart_type=sheet.suggested_chart_type)
        for sheet in preview.sheets
        if sheet.suggested_chart_type is not None
    ]
    if not selections:
        raise DomainValidationError("No sheet has a suggested chart type; pass --sheet and --chart")
    return selections


def _selection_at(preview: ImportPreview, options: SelectionOptions, index: int) -> ImportSelection:
    sheet = options.sheets[index] if options.sheets else None
    chart_type = options.charts[index] if options.charts else _suggestion_for(preview, sheet)
    title = options.titles[index] if options.titles else None
    try:
        return ImportSelection(sheet=sheet, chart_type=chart_type, title=title)
    except ValidationError as error:
        first = error.errors()[0]
        option = OPTION_BY_FIELD[str(first["loc"][0])]
        raise DomainValidationError(f"Invalid {option}: {first['msg']}") from error


def _suggestion_for(preview: ImportPreview, sheet: str | None) -> ChartType:
    suggestion = _sheet_preview(preview, sheet).suggested_chart_type
    if suggestion is None:
        raise DomainValidationError(f"No chart type suggested for {describe_source(sheet)}; pass --chart")
    return suggestion


def _sheet_preview(preview: ImportPreview, sheet: str | None) -> SheetPreview:
    if sheet is None:
        return preview.sheets[0]
    for candidate in preview.sheets:
        if candidate.sheet == sheet:
            return candidate
    raise sheet_not_found(sheet, [candidate.sheet for candidate in preview.sheets])
