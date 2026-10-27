from typing import NamedTuple

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.dataset_repository import SqlDatasetRepository
from app.repositories.protocols import DatasetRepository, WidgetRepository
from app.repositories.widget_repository import SqlWidgetRepository
from tests.fakes import InMemoryDatasetRepository, InMemoryStore, InMemoryWidgetRepository


class Repositories(NamedTuple):
    widgets: WidgetRepository
    datasets: DatasetRepository


# Sync on purpose: pytest-asyncio cannot resolve the async db_session through getfixturevalue from an
# async fixture, and the memory variant needs no event loop at all.
# One parametrized fixture (not one per repository) so both repositories always share one backend.
@pytest.fixture(params=["sql", "memory"])
def repositories(request: pytest.FixtureRequest) -> Repositories:
    if request.param == "sql":
        session: AsyncSession = request.getfixturevalue("db_session")
        return Repositories(SqlWidgetRepository(session), SqlDatasetRepository(session))
    store = InMemoryStore()
    return Repositories(InMemoryWidgetRepository(store), InMemoryDatasetRepository(store))


@pytest.fixture
def widget_repo(repositories: Repositories) -> WidgetRepository:
    return repositories.widgets


@pytest.fixture
def dataset_repo(repositories: Repositories) -> DatasetRepository:
    return repositories.datasets
