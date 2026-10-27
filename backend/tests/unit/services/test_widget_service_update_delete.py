from uuid import uuid4

import pytest

from app.core.enums import DatasetOrigin, WidgetType
from app.core.errors import DomainValidationError, NotFoundError, WidgetHasNoDataError
from app.repositories.protocols import DatasetRepository, WidgetRepository
from app.schemas.widget import WidgetCreate, WidgetUpdate
from app.services.widget_service import WidgetService
from tests.factories import OLD_TIMESTAMP, make_chart_widget, make_dataset
from tests.fakes import InMemoryStore


async def test_update_renames_any_widget(service: WidgetService) -> None:
    created = await service.create_widget(WidgetCreate(type=WidgetType.BAR))

    updated = await service.update_widget(created.id, WidgetUpdate(title="Renamed"))

    assert updated.title == "Renamed"


async def test_update_returns_a_newer_updated_at(
    service: WidgetService, widget_repo: WidgetRepository
) -> None:
    created = await service.create_widget(WidgetCreate(type=WidgetType.TEXT))
    stored = await widget_repo.get(created.id)
    assert stored is not None
    stored.updated_at = OLD_TIMESTAMP

    updated = await service.update_widget(created.id, WidgetUpdate(title="Later"))

    assert updated.updated_at > OLD_TIMESTAMP


async def test_update_text_content_on_text_widget_replaces_it(service: WidgetService) -> None:
    created = await service.create_widget(WidgetCreate(type=WidgetType.TEXT))

    updated = await service.update_widget(created.id, WidgetUpdate(text_content="Hello"))

    assert updated.text_content == "Hello"


async def test_update_text_content_on_chart_raises_validation_error(service: WidgetService) -> None:
    created = await service.create_widget(WidgetCreate(type=WidgetType.LINE))

    with pytest.raises(DomainValidationError, match="text widgets"):
        await service.update_widget(created.id, WidgetUpdate(text_content="nope"))


async def test_update_unknown_widget_raises_not_found(service: WidgetService) -> None:
    with pytest.raises(NotFoundError, match="Widget not found"):
        await service.update_widget(uuid4(), WidgetUpdate(title="x"))


async def test_delete_chart_widget_removes_its_generated_dataset(
    service: WidgetService, store: InMemoryStore
) -> None:
    created = await service.create_widget(WidgetCreate(type=WidgetType.LINE))

    await service.delete_widget(created.id)

    assert not store.widgets
    assert not store.datasets


async def test_delete_widget_keeps_uploaded_dataset(
    service: WidgetService,
    store: InMemoryStore,
    widget_repo: WidgetRepository,
    dataset_repo: DatasetRepository,
) -> None:
    dataset = await dataset_repo.add(make_dataset(origin=DatasetOrigin.UPLOAD))
    widget = await widget_repo.add(make_chart_widget(dataset.id))

    await service.delete_widget(widget.id)

    assert not store.widgets
    assert dataset.id in store.datasets


async def test_delete_unknown_widget_raises_not_found(service: WidgetService) -> None:
    with pytest.raises(NotFoundError):
        await service.delete_widget(uuid4())


async def test_get_widget_data_returns_display_data(service: WidgetService) -> None:
    created = await service.create_widget(WidgetCreate(type=WidgetType.PIE))

    data = await service.get_widget_data(created.id)

    assert data.categories
    assert len(data.series) == 1


async def test_get_widget_data_for_text_widget_raises_widget_has_no_data(service: WidgetService) -> None:
    created = await service.create_widget(WidgetCreate(type=WidgetType.TEXT))

    with pytest.raises(WidgetHasNoDataError, match="no chart data"):
        await service.get_widget_data(created.id)


async def test_get_widget_data_for_unknown_widget_raises_not_found(service: WidgetService) -> None:
    with pytest.raises(NotFoundError):
        await service.get_widget_data(uuid4())


async def test_get_widget_data_when_dataset_is_missing_raises_not_found(
    service: WidgetService, store: InMemoryStore
) -> None:
    created = await service.create_widget(WidgetCreate(type=WidgetType.LINE))
    store.datasets.clear()

    with pytest.raises(NotFoundError, match="Dataset not found"):
        await service.get_widget_data(created.id)
