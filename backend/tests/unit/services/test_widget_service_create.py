from app.core.enums import DatasetOrigin, WidgetType
from app.schemas.widget import WidgetCreate
from app.services.widget_service import TEXT_PLACEHOLDER, WidgetService
from tests.fakes import InMemoryStore


async def test_create_chart_widget_generates_hidden_dataset_and_appends(
    service: WidgetService, store: InMemoryStore
) -> None:
    created = await service.create_widget(WidgetCreate(type=WidgetType.LINE))

    assert created.position == 0
    assert created.title == "Line chart 1"
    assert created.source is not None
    assert created.source.origin == DatasetOrigin.GENERATED
    assert [dataset.name for dataset in store.datasets.values()] == ["Line chart 1"]


async def test_second_widget_of_same_type_is_numbered(service: WidgetService) -> None:
    await service.create_widget(WidgetCreate(type=WidgetType.LINE))

    second = await service.create_widget(WidgetCreate(type=WidgetType.LINE))

    assert second.title == "Line chart 2"
    assert second.position == 1


async def test_create_text_widget_uses_placeholder_without_dataset(
    service: WidgetService, store: InMemoryStore
) -> None:
    created = await service.create_widget(WidgetCreate(type=WidgetType.TEXT))

    assert created.title == "Text 1"
    assert created.text_content == TEXT_PLACEHOLDER
    assert created.source is None
    assert not store.datasets


async def test_create_uses_given_title(service: WidgetService) -> None:
    created = await service.create_widget(WidgetCreate(type=WidgetType.PIE, title="Share"))

    assert created.title == "Share"
