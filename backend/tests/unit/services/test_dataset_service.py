from uuid import uuid4

import pytest

from app.core.enums import ChartType, DatasetOrigin, WidgetType
from app.core.errors import NotFoundError
from app.services.dataset_service import DatasetService
from tests.factories import make_chart_widget, make_dataset
from tests.fakes import InMemoryDatasetRepository, InMemoryStore, InMemoryWidgetRepository


@pytest.fixture
def datasets_service(
    dataset_repo: InMemoryDatasetRepository, widget_repo: InMemoryWidgetRepository
) -> DatasetService:
    return DatasetService(dataset_repo, widget_repo)


async def test_list_datasets_hides_generated_and_counts_widgets(
    datasets_service: DatasetService,
    dataset_repo: InMemoryDatasetRepository,
    widget_repo: InMemoryWidgetRepository,
) -> None:
    seeded = await dataset_repo.add(make_dataset(name="seeded"))
    generated = await dataset_repo.add(make_dataset(name="random", origin=DatasetOrigin.GENERATED))
    await widget_repo.add(make_chart_widget(seeded.id))
    await widget_repo.add(make_chart_widget(generated.id))

    listed = await datasets_service.list_datasets()

    assert [(item.name, item.widget_count) for item in listed] == [("seeded", 1)]


async def test_add_to_dashboard_appends_widget_with_dataset_type_and_name(
    datasets_service: DatasetService, dataset_repo: InMemoryDatasetRepository
) -> None:
    dataset = await dataset_repo.add(make_dataset(name="Sales", chart_type=ChartType.PIE))

    widget = await datasets_service.add_to_dashboard(dataset.id)

    assert (widget.type, widget.title, widget.position) == (WidgetType.PIE, "Sales", 0)
    assert widget.source is not None
    assert widget.source.dataset_id == dataset.id


async def test_add_to_dashboard_unknown_dataset_raises_not_found(datasets_service: DatasetService) -> None:
    missing = uuid4()

    with pytest.raises(NotFoundError, match="^Dataset not found$") as raised:
        await datasets_service.add_to_dashboard(missing)

    assert raised.value.details == {"dataset_id": str(missing)}


async def test_add_to_dashboard_generated_dataset_raises_not_found(
    datasets_service: DatasetService, dataset_repo: InMemoryDatasetRepository, store: InMemoryStore
) -> None:
    generated = await dataset_repo.add(make_dataset(origin=DatasetOrigin.GENERATED))

    with pytest.raises(NotFoundError):
        await datasets_service.add_to_dashboard(generated.id)

    assert store.widgets == {}


async def test_delete_dataset_removes_its_widgets(
    datasets_service: DatasetService,
    dataset_repo: InMemoryDatasetRepository,
    widget_repo: InMemoryWidgetRepository,
    store: InMemoryStore,
) -> None:
    dataset = await dataset_repo.add(make_dataset())
    await widget_repo.add(make_chart_widget(dataset.id))

    await datasets_service.delete_dataset(dataset.id)

    assert store.datasets == {}
    assert store.widgets == {}


async def test_delete_dataset_unknown_raises_not_found(datasets_service: DatasetService) -> None:
    with pytest.raises(NotFoundError, match="^Dataset not found$"):
        await datasets_service.delete_dataset(uuid4())


async def test_delete_dataset_generated_raises_not_found_and_keeps_it(
    datasets_service: DatasetService, dataset_repo: InMemoryDatasetRepository, store: InMemoryStore
) -> None:
    generated = await dataset_repo.add(make_dataset(origin=DatasetOrigin.GENERATED))

    with pytest.raises(NotFoundError):
        await datasets_service.delete_dataset(generated.id)

    assert generated.id in store.datasets
