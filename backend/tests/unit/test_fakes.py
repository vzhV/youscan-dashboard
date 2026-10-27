from uuid import uuid4

import pytest

from app.core.enums import WidgetType
from tests.factories import make_chart_widget, make_dataset, make_widget
from tests.fakes import InMemoryDatasetRepository, InMemoryStore, InMemoryWidgetRepository


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


async def test_widget_add_with_unknown_dataset_raises(store: InMemoryStore) -> None:
    with pytest.raises(ValueError, match="Foreign key"):
        await InMemoryWidgetRepository(store).add(make_chart_widget(uuid4()))


async def test_text_widget_add_with_dataset_raises(store: InMemoryStore) -> None:
    dataset = await InMemoryDatasetRepository(store).add(make_dataset())

    with pytest.raises(ValueError, match="Check"):
        await InMemoryWidgetRepository(store).add(make_widget(dataset_id=dataset.id))


async def test_chart_widget_add_without_dataset_raises(store: InMemoryStore) -> None:
    with pytest.raises(ValueError, match="Check"):
        await InMemoryWidgetRepository(store).add(make_widget(type=WidgetType.LINE))


async def test_chart_widget_add_with_text_content_raises(store: InMemoryStore) -> None:
    dataset = await InMemoryDatasetRepository(store).add(make_dataset())

    with pytest.raises(ValueError, match="text content"):
        await InMemoryWidgetRepository(store).add(make_chart_widget(dataset.id, text_content="x"))


async def test_widget_delete_of_unknown_widget_raises(store: InMemoryStore) -> None:
    with pytest.raises(KeyError):
        await InMemoryWidgetRepository(store).delete(make_widget(id=uuid4()))


async def test_dataset_delete_of_unknown_dataset_raises(store: InMemoryStore) -> None:
    with pytest.raises(KeyError):
        await InMemoryDatasetRepository(store).delete(make_dataset(id=uuid4()))


async def test_dataset_delete_keeps_store_dict_identity(store: InMemoryStore) -> None:
    datasets = InMemoryDatasetRepository(store)
    dataset = await datasets.add(make_dataset())
    await InMemoryWidgetRepository(store).add(make_chart_widget(dataset.id))
    widgets_before = store.widgets

    await datasets.delete(dataset)

    assert store.widgets is widgets_before
    assert widgets_before == {}
