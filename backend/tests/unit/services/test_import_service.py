import threading
from pathlib import Path

import pytest

from app.core.enums import ChartType, DatasetOrigin, WidgetType
from app.core.errors import ChartTypeMismatchError, SeedDataError, SheetNotFoundError
from app.importing.parsers.registry import ParserRegistry
from app.importing.source_file import SourceFile
from app.schemas.imports import ImportSelection
from app.services.import_service import ImportService
from tests.factories import SEED_DATA_DIR, SEED_TITLES
from tests.fakes import (
    InMemoryDatasetRepository,
    InMemoryStore,
    InMemoryWidgetRepository,
    ThreadRecordingParser,
)

LINE_SHEET = "line chart data"


def seed_file(filename: str) -> SourceFile:
    return SourceFile(filename, (SEED_DATA_DIR / filename).read_bytes())


async def test_import_creates_dataset_and_widget_per_selection(importer: ImportService) -> None:
    selection = ImportSelection(sheet=LINE_SHEET, chart_type=ChartType.LINE)

    result = await importer.import_file(seed_file("line-and-pie.xlsx"), [selection])

    dataset, widget = result.datasets[0], result.widgets[0]
    assert dataset.row_count == 212
    assert dataset.source_sheet == LINE_SHEET
    assert dataset.origin is DatasetOrigin.UPLOAD
    assert dataset.widget_count == 1
    assert widget.title == LINE_SHEET
    assert widget.type is WidgetType.LINE


async def test_import_uses_selection_title_when_given(importer: ImportService) -> None:
    selection = ImportSelection(sheet=LINE_SHEET, chart_type=ChartType.LINE, title="  Mine ")

    result = await importer.import_file(seed_file("line-and-pie.xlsx"), [selection])

    assert result.widgets[0].title == "Mine"


async def test_import_without_sheet_uses_first_table(importer: ImportService) -> None:
    selection = ImportSelection(chart_type=ChartType.LINE)

    result = await importer.import_file(seed_file("line-and-pie.xlsx"), [selection])

    assert result.datasets[0].source_sheet == LINE_SHEET


async def test_import_csv_defaults_title_to_file_stem(importer: ImportService) -> None:
    selection = ImportSelection(chart_type=ChartType.STACKED_BAR)

    result = await importer.import_file(seed_file("stacked-bar.csv"), [selection])

    assert result.widgets[0].title == "stacked-bar"
    assert result.datasets[0].name == "stacked-bar"


async def test_import_truncates_long_default_title(importer: ImportService) -> None:
    source = SourceFile(f"{'x' * 300}.csv", seed_file("stacked-bar.csv").content)

    result = await importer.import_file(source, [ImportSelection(chart_type=ChartType.STACKED_BAR)])

    assert len(result.widgets[0].title) == 100


async def test_import_unknown_sheet_raises_with_available_sheets(importer: ImportService) -> None:
    selection = ImportSelection(sheet="nope", chart_type=ChartType.LINE)

    with pytest.raises(SheetNotFoundError) as caught:
        await importer.import_file(seed_file("line-and-pie.xlsx"), [selection])

    assert caught.value.message == "Sheet 'nope' not found"
    assert caught.value.details == {"available": [LINE_SHEET, "pie chart data"]}


async def test_import_rejects_mismatching_chart_type(importer: ImportService) -> None:
    selection = ImportSelection(chart_type=ChartType.PIE)

    with pytest.raises(ChartTypeMismatchError):
        await importer.import_file(seed_file("stacked-bar.csv"), [selection])


async def test_import_sheet_on_csv_says_csv_files_have_no_sheets(importer: ImportService) -> None:
    selection = ImportSelection(sheet="data", chart_type=ChartType.STACKED_BAR)

    with pytest.raises(SheetNotFoundError) as caught:
        await importer.import_file(seed_file("stacked-bar.csv"), [selection])

    assert caught.value.message == "Sheet 'data' not found: CSV files have no sheets"
    assert caught.value.details == {"available": []}


async def test_import_with_a_bad_selection_writes_nothing(
    importer: ImportService, store: InMemoryStore
) -> None:
    selections = [
        ImportSelection(sheet=LINE_SHEET, chart_type=ChartType.LINE),
        ImportSelection(sheet="nope", chart_type=ChartType.LINE),
    ]

    with pytest.raises(SheetNotFoundError):
        await importer.import_file(seed_file("line-and-pie.xlsx"), selections)

    assert not store.datasets
    assert not store.widgets


async def test_import_seed_creates_manifest_widgets_in_order(
    importer: ImportService, store: InMemoryStore
) -> None:
    result = await importer.import_seed()

    assert [widget.title for widget in result.widgets] == SEED_TITLES
    assert [widget.type for widget in result.widgets] == [
        WidgetType.LINE,
        WidgetType.PIE,
        WidgetType.STACKED_BAR,
    ]
    assert [widget.position for widget in result.widgets] == [0, 1, 2]
    assert {dataset.origin for dataset in store.datasets.values()} == {DatasetOrigin.SEED}


async def test_import_parses_and_plans_off_the_event_loop(
    widget_repo: InMemoryWidgetRepository, dataset_repo: InMemoryDatasetRepository
) -> None:
    parser = ThreadRecordingParser()
    importer = ImportService(dataset_repo, widget_repo, ParserRegistry([parser]))

    await importer.import_file(
        seed_file("stacked-bar.csv"), [ImportSelection(chart_type=ChartType.STACKED_BAR)]
    )

    assert parser.thread_ids
    assert threading.get_ident() not in parser.thread_ids


async def test_import_seed_with_missing_seed_file_raises_seed_data_error_naming_only_the_file(
    importer: ImportService, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("app.services.import_service.SEED_DATA_DIR", tmp_path)

    with pytest.raises(SeedDataError) as raised:
        await importer.import_seed()

    assert (
        str(raised.value) == "Seed file 'line-and-pie.xlsx' could not be imported: the file could not be read"
    )
    assert raised.value.details == {"file": "line-and-pie.xlsx"}
