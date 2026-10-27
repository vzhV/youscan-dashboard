import runpy
from collections.abc import Callable
from pathlib import Path

import pytest
from typer.testing import CliRunner

from app.cli.app import cli
from app.core.config import get_settings
from app.services.seed import SEED_ENTRIES
from tests.factories import SEED_DATA_DIR, SEED_TITLES

XLSX = str(SEED_DATA_DIR / "line-and-pie.xlsx")


def test_cli_seed_creates_the_three_seed_widgets(
    runner: CliRunner, board_titles: Callable[[], list[str]]
) -> None:
    result = runner.invoke(cli, ["seed"])

    assert result.exit_code == 0
    assert board_titles() == SEED_TITLES


def test_cli_seed_refuses_non_empty_board(runner: CliRunner) -> None:
    runner.invoke(cli, ["seed"])

    result = runner.invoke(cli, ["seed"])

    assert result.exit_code == 1
    assert "Error: Board is not empty. Use --reset to replace it." in result.output


def test_cli_seed_with_reset_restores_three_widgets(
    runner: CliRunner, board_titles: Callable[[], list[str]], dataset_count: Callable[[], int]
) -> None:
    runner.invoke(cli, ["import", XLSX])

    result = runner.invoke(cli, ["seed", "--reset"])

    assert result.exit_code == 0
    assert board_titles() == SEED_TITLES
    assert dataset_count() == len(SEED_TITLES)


def test_cli_reports_unreachable_database_without_traceback(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://nobody:nopass@127.0.0.1:1/none")
    get_settings.cache_clear()

    result = runner.invoke(cli, ["seed"])

    assert result.exit_code == 1
    assert "Error: Database is unreachable" in result.output
    assert "Traceback" not in result.output


def test_cli_migrate_reports_unreachable_database_without_traceback(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    unreachable = "postgresql+psycopg://nobody:nopass@127.0.0.1:1/none"
    monkeypatch.setenv("MIGRATIONS_DATABASE_URL", unreachable)
    get_settings.cache_clear()

    result = runner.invoke(cli, ["migrate"])

    assert result.exit_code == 1
    assert "Error: Database is unreachable" in result.output
    assert "Traceback" not in result.output


def test_cli_migrate_applies_migrations(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["migrate"])

    assert result.exit_code == 0


def test_cli_module_entrypoint_shows_help(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["app.cli", "--help"])

    with pytest.raises(SystemExit) as stopped:
        runpy.run_module("app.cli", run_name="__main__")

    assert stopped.value.code == 0


def test_cli_seed_with_corrupt_seed_file_reports_error_without_traceback(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for entry in SEED_ENTRIES:
        (tmp_path / entry.filename).write_bytes(b"not a spreadsheet")
    monkeypatch.setattr("app.services.import_service.SEED_DATA_DIR", tmp_path)

    result = runner.invoke(cli, ["seed"])

    assert result.exit_code == 1
    assert "Error: Seed file 'line-and-pie.xlsx' could not be imported" in result.output
    assert "Traceback" not in result.output
