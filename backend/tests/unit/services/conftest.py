import random
from datetime import date

import pytest

from app.services.import_service import ImportService
from app.services.widget_service import WidgetService
from tests.fakes import InMemoryDatasetRepository, InMemoryStore, InMemoryWidgetRepository

TODAY = date(2026, 10, 27)


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def widget_repo(store: InMemoryStore) -> InMemoryWidgetRepository:
    return InMemoryWidgetRepository(store)


@pytest.fixture
def dataset_repo(store: InMemoryStore) -> InMemoryDatasetRepository:
    return InMemoryDatasetRepository(store)


@pytest.fixture
def service(widget_repo: InMemoryWidgetRepository, dataset_repo: InMemoryDatasetRepository) -> WidgetService:
    rng = random.Random(7)  # noqa: S311  # seeded for deterministic test data
    return WidgetService(widget_repo, dataset_repo, rng, lambda: TODAY)


@pytest.fixture
def importer(widget_repo: InMemoryWidgetRepository, dataset_repo: InMemoryDatasetRepository) -> ImportService:
    return ImportService(dataset_repo, widget_repo)
