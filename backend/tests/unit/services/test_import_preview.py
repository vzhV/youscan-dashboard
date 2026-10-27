import threading
from datetime import datetime

from app.core.enums import ChartType
from app.importing.parsers.registry import ParserRegistry
from app.importing.reader import read_tables
from app.importing.shaping.columns import ColumnKind
from app.importing.source_file import SourceFile
from app.schemas.imports import ColumnInfo, ColumnMappingRead, ImportPreview
from app.services.import_preview import SAMPLE_ROW_COUNT, build_preview, preview_file
from tests.factories import SEED_DATA_DIR, make_xlsx
from tests.fakes import ThreadRecordingParser


def preview_of(source: SourceFile) -> ImportPreview:
    return build_preview(source, read_tables(source))


def seed_preview(filename: str) -> ImportPreview:
    return preview_of(SourceFile(filename, (SEED_DATA_DIR / filename).read_bytes()))


def test_preview_seed_workbook_suggests_line_and_pie() -> None:
    preview = seed_preview("line-and-pie.xlsx")

    line, pie = preview.sheets
    assert preview.filename == "line-and-pie.xlsx"
    assert line.suggested_chart_type is ChartType.LINE
    assert line.mapping == ColumnMappingRead(categories="Date", series="Campaign", values=["Result"])
    assert pie.suggested_chart_type is ChartType.PIE


def test_preview_lists_every_column_with_its_kind() -> None:
    line = seed_preview("line-and-pie.xlsx").sheets[0]

    assert ColumnInfo(name="Date", kind=ColumnKind.DATE) in line.columns
    assert ColumnInfo(name="Result", kind=ColumnKind.NUMBER) in line.columns
    assert line.row_count == 212


def test_preview_sample_rows_render_dates_as_iso() -> None:
    line = seed_preview("line-and-pie.xlsx").sheets[0]

    assert line.sample_rows[0] == [1.0, "A", "2024-10-28", 48.0]
    assert len(line.sample_rows) == SAMPLE_ROW_COUNT


def test_preview_csv_sheet_has_no_name() -> None:
    preview = seed_preview("stacked-bar.csv")

    assert preview.sheets[0].sheet is None
    assert preview.sheets[0].suggested_chart_type is ChartType.STACKED_BAR


def test_preview_reports_issue_for_unshapeable_sheet() -> None:
    content = make_xlsx({"words": [["a", "b"], ["x", "y"]]})

    sheet = preview_of(SourceFile("words.xlsx", content)).sheets[0]

    assert sheet.issue is not None
    assert sheet.issue.code == "not_shapeable"
    assert sheet.suggested_chart_type is None
    assert sheet.mapping is None


def test_preview_keeps_good_sheets_when_another_sheet_has_an_issue() -> None:
    content = make_xlsx({"words": [["a", "b"], ["x", "y"]], "ok": [["day", "n"], ["a", 1], ["b", 2]]})

    words, ok = preview_of(SourceFile("mixed.xlsx", content)).sheets

    assert words.issue is not None
    assert ok.issue is None
    assert ok.suggested_chart_type is ChartType.PIE


def test_preview_csv_numbers_in_a_number_column_become_floats() -> None:
    sheet = preview_of(SourceFile("n.csv", b"label,count\nA,1137\nB,2\n")).sheets[0]

    assert sheet.sample_rows == [["A", 1137.0], ["B", 2.0]]


def test_preview_sample_rows_keep_empty_cells_as_none() -> None:
    sheet = preview_of(SourceFile("n.csv", b"label,count\nA,1\nB,\n")).sheets[0]

    assert sheet.sample_rows == [["A", 1.0], ["B", None]]


def test_preview_flags_sheet_when_no_chart_type_fits() -> None:
    rows: list[list[object]] = [["label", "a", "b"], *([f"row {index}", 1, 2] for index in range(101))]

    sheet = preview_of(SourceFile("wide.xlsx", make_xlsx({"wide": rows}))).sheets[0]

    assert sheet.suggested_chart_type is None
    assert sheet.mapping is not None
    assert sheet.issue is not None
    assert sheet.issue.code == "chart_type_mismatch"
    assert sheet.issue.message == "A stacked bar chart supports at most 100 categories; this data has 101"


def test_preview_names_the_first_percent_cell() -> None:
    sheet = preview_of(SourceFile("p.csv", b"Brand,Share\nA,12%\nB,30%\n")).sheets[0]

    assert sheet.issue is not None
    assert "Column 'Share', row 2: '12%' is not a number" in sheet.issue.message


def test_preview_sample_rows_keep_numbers_and_render_midnight_datetimes() -> None:
    content = make_xlsx({"s": [["day", "n"], [datetime(2024, 1, 2), 1.5]]})

    sheet = preview_of(SourceFile("s.xlsx", content)).sheets[0]

    assert sheet.sample_rows == [["2024-01-02", 1.5]]


async def test_preview_file_reads_the_file_off_the_event_loop() -> None:
    parser = ThreadRecordingParser()
    source = SourceFile("n.csv", b"label,count\nA,1\n")

    preview = await preview_file(source, ParserRegistry([parser]))

    assert preview.sheets[0].row_count == 1
    assert threading.get_ident() not in parser.thread_ids
