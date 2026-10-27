from collections.abc import Callable
from pathlib import Path

import pytest
from typer.testing import CliRunner

from app.cli.app import cli
from tests.factories import SEED_DATA_DIR, make_xlsx

XLSX = str(SEED_DATA_DIR / "line-and-pie.xlsx")
CSV = str(SEED_DATA_DIR / "stacked-bar.csv")


def test_cli_inspect_prints_sheets_and_suggestions(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["inspect", XLSX])

    assert result.exit_code == 0
    assert "line chart data" in result.output
    assert "pie chart data" in result.output
    assert "Suggested chart: line" in result.output
    assert "Suggested chart: pie" in result.output
    assert "categories=Date, series=Campaign, values=Result" in result.output
    assert "Date (date)" in result.output


def test_cli_inspect_prints_issue_for_unshapeable_sheet(runner: CliRunner, tmp_path: Path) -> None:
    broken = tmp_path / "words.xlsx"
    broken.write_bytes(make_xlsx({"words": [["a", "b"], ["x", "y"]]}))

    result = runner.invoke(cli, ["inspect", str(broken)])

    assert result.exit_code == 0
    assert "Issue:" in result.output
    assert "Suggested chart" not in result.output


def test_cli_inspect_explains_why_no_chart_type_fits(runner: CliRunner, tmp_path: Path) -> None:
    rows: list[list[object]] = [["label", "a", "b"], *([f"row {index}", 1, 2] for index in range(101))]
    wide = tmp_path / "wide.xlsx"
    wide.write_bytes(make_xlsx({"wide": rows}))

    result = runner.invoke(cli, ["inspect", str(wide)])

    assert result.exit_code == 0
    assert "Rows: 101" in result.output
    assert "Mapping: categories=label" in result.output
    assert "Issue: A stacked bar chart supports at most 100 categories; this data has 101" in result.output
    assert "Suggested chart" not in result.output


def test_cli_import_without_options_imports_suggested_sheets(
    runner: CliRunner, board_titles: Callable[[], list[str]]
) -> None:
    result = runner.invoke(cli, ["import", XLSX])

    assert result.exit_code == 0
    assert board_titles() == ["line chart data", "pie chart data"]
    assert "Imported 2 widgets" in result.output


def test_cli_import_with_options_uses_chart_and_title(
    runner: CliRunner, board_titles: Callable[[], list[str]]
) -> None:
    arguments = ["import", XLSX, "--sheet", "pie chart data", "--chart", "bar", "--title", "Mine"]

    result = runner.invoke(cli, arguments)

    assert result.exit_code == 0
    assert board_titles() == ["Mine"]


def test_cli_import_without_chart_uses_the_sheet_suggestion(
    runner: CliRunner, board_titles: Callable[[], list[str]]
) -> None:
    result = runner.invoke(cli, ["import", XLSX, "--sheet", "pie chart data"])

    assert result.exit_code == 0
    assert board_titles() == ["pie chart data"]


def test_cli_import_csv_without_sheet_uses_the_suggestion(
    runner: CliRunner, board_titles: Callable[[], list[str]]
) -> None:
    result = runner.invoke(cli, ["import", CSV, "--title", "Brands"])

    assert result.exit_code == 0
    assert board_titles() == ["Brands"]


def test_cli_import_rejects_option_lists_of_different_length(
    runner: CliRunner, board_titles: Callable[[], list[str]]
) -> None:
    arguments = ["import", XLSX, "--sheet", "line chart data", "--sheet", "pie chart data", "--chart", "line"]

    result = runner.invoke(cli, arguments)

    assert result.exit_code == 1
    assert "same number" in result.output
    assert board_titles() == []


def test_cli_import_sheet_without_suggestion_exits_with_message(runner: CliRunner, tmp_path: Path) -> None:
    broken = tmp_path / "words.xlsx"
    broken.write_bytes(make_xlsx({"words": [["a", "b"], ["x", "y"]]}))

    result = runner.invoke(cli, ["import", str(broken), "--sheet", "words"])

    assert result.exit_code == 1
    assert "Error: No chart type suggested for Sheet 'words'" in result.output


def test_cli_import_unknown_sheet_without_chart_lists_available_sheets(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["import", XLSX, "--sheet", "nope"])

    assert result.exit_code == 1
    assert "Error: Sheet 'nope' not found" in result.output


def test_cli_import_sheet_on_csv_says_csv_files_have_no_sheets(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["import", CSV, "--sheet", "data"])

    assert result.exit_code == 1
    assert "CSV files have no sheets" in result.output


def test_cli_import_without_options_fails_when_no_sheet_is_chartable(
    runner: CliRunner, tmp_path: Path
) -> None:
    broken = tmp_path / "words.xlsx"
    broken.write_bytes(make_xlsx({"words": [["a", "b"], ["x", "y"]]}))

    result = runner.invoke(cli, ["import", str(broken)])

    assert result.exit_code == 1
    assert "Error: No sheet has a suggested chart type; pass --sheet and --chart" in result.output


@pytest.mark.parametrize("title", ["   ", "x" * 101], ids=["blank", "too_long"])
def test_cli_import_invalid_title_prints_error_without_traceback(runner: CliRunner, title: str) -> None:
    result = runner.invoke(cli, ["import", CSV, "--title", title])

    assert result.exit_code == 1
    assert "Error: Invalid --title:" in result.output
    assert "Traceback" not in result.output


def test_cli_import_unknown_sheet_prints_error(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["import", XLSX, "--sheet", "nope", "--chart", "line"])

    assert result.exit_code == 1
    assert "Error: Sheet 'nope' not found" in result.output


def test_cli_import_unsupported_file_prints_error_without_traceback(
    runner: CliRunner, tmp_path: Path
) -> None:
    notes = tmp_path / "notes.txt"
    notes.write_text("hello")

    result = runner.invoke(cli, ["import", str(notes)])

    assert result.exit_code == 1
    assert "Error: Unsupported file type '.txt'" in result.output
    assert "Traceback" not in result.output
