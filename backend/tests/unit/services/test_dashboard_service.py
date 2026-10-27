from pathlib import Path

import pytest

from app.core.enums import ChartType, DatasetOrigin, WidgetType
from app.core.errors import BoardNotEmptyError, SeedDataError
from app.importing.source_file import SourceFile
from app.models import Widget
from app.schemas.imports import ImportSelection
from app.services.dashboard_service import DashboardService
from app.services.import_service import ImportService
from app.services.seed import SEED_ENTRIES
from tests.factories import make_chart_widget, make_dataset, make_widget
from tests.fakes import InMemoryDatasetRepository, InMemoryStore, InMemoryWidgetRepository


@pytest.fixture
def dashboard(
    widget_repo: InMemoryWidgetRepository, dataset_repo: InMemoryDatasetRepository, importer: ImportService
) -> DashboardService:
    return DashboardService(widget_repo, dataset_repo, importer)


async def test_seed_on_empty_board_returns_seed_widgets(dashboard: DashboardService) -> None:
    widgets = await dashboard.seed()

    assert [widget.position for widget in widgets] == [0, 1, 2]


async def test_seed_refuses_non_empty_board(
    dashboard: DashboardService, widget_repo: InMemoryWidgetRepository
) -> None:
    await widget_repo.add(make_widget())

    with pytest.raises(BoardNotEmptyError, match="^Board is not empty$"):
        await dashboard.seed()


async def test_reset_replaces_board_with_seed_widgets(
    dashboard: DashboardService,
    importer: ImportService,
    widget_repo: InMemoryWidgetRepository,
    store: InMemoryStore,
) -> None:
    await widget_repo.add(make_widget())
    upload = SourceFile("u.csv", b"day,a,b\n2024-01-01,1,2\n")
    await importer.import_file(upload, [ImportSelection(chart_type=ChartType.LINE)])

    widgets = await dashboard.reset()

    assert [widget.type for widget in widgets] == [WidgetType.LINE, WidgetType.PIE, WidgetType.STACKED_BAR]
    assert [widget.position for widget in widgets] == [0, 1, 2]
    assert len(store.widgets) == 3
    assert {dataset.origin for dataset in store.datasets.values()} == {DatasetOrigin.SEED}
    assert len(store.datasets) == 3


class LockFailureError(Exception):
    """Sentinel raised by the lock so a test can see what ran before it."""


class ReadBeforeLockError(Exception):
    """Sentinel raised by a read, so a test can tell that the board was read before it was locked."""


class FailingLockWidgetRepository(InMemoryWidgetRepository):
    async def list_ordered(self) -> list[Widget]:
        raise ReadBeforeLockError

    async def lock_board(self) -> None:
        raise LockFailureError


@pytest.fixture
def lock_failing_dashboard(store: InMemoryStore, dataset_repo: InMemoryDatasetRepository) -> DashboardService:
    widgets = FailingLockWidgetRepository(store)
    return DashboardService(widgets, dataset_repo, ImportService(dataset_repo, widgets))


async def test_seed_takes_the_lock_before_any_read_or_write(
    lock_failing_dashboard: DashboardService, store: InMemoryStore
) -> None:
    with pytest.raises(LockFailureError):
        await lock_failing_dashboard.seed()

    assert store.widgets == {}
    assert store.datasets == {}


async def test_reset_takes_the_lock_before_deleting_anything(
    lock_failing_dashboard: DashboardService,
    widget_repo: InMemoryWidgetRepository,
    dataset_repo: InMemoryDatasetRepository,
    store: InMemoryStore,
) -> None:
    dataset = await dataset_repo.add(make_dataset())
    await widget_repo.add(make_chart_widget(dataset.id))

    with pytest.raises(LockFailureError):
        await lock_failing_dashboard.reset()

    assert len(store.widgets) == 1
    assert list(store.datasets) == [dataset.id]


async def test_reset_with_corrupt_seed_file_raises_seed_data_error(
    dashboard: DashboardService, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for entry in SEED_ENTRIES:
        (tmp_path / entry.filename).write_bytes(b"not a spreadsheet")
    monkeypatch.setattr("app.services.import_service.SEED_DATA_DIR", tmp_path)

    with pytest.raises(SeedDataError, match="^Seed file 'line-and-pie.xlsx' could not be imported: "):
        await dashboard.reset()
