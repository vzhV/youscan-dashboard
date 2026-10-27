import pytest

from app.core.enums import ChartType, DatasetOrigin, WidgetType
from app.core.errors import BoardNotEmptyError
from app.importing.source_file import SourceFile
from app.schemas.imports import ImportSelection
from app.services.dashboard_service import DashboardService
from app.services.import_service import ImportService
from tests.factories import make_widget
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
