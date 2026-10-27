import pytest
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Dataset
from app.repositories.dataset_repository import SqlDatasetRepository
from app.repositories.widget_repository import SqlWidgetRepository
from tests.factories import make_chart_widget, make_dataset

# Pins the SQL-only invariant the in-memory fakes cannot mirror: metadata loads never carry the payload.


@pytest.fixture
async def stored_dataset(db_session: AsyncSession) -> Dataset:
    dataset = await SqlDatasetRepository(db_session).add(make_dataset())
    await SqlWidgetRepository(db_session).add(make_chart_widget(dataset.id))
    # Drop the identity map so the repositories load fresh instances, as a new request would.
    db_session.expunge_all()
    return dataset


def _assert_payload_raises(dataset: Dataset) -> None:
    with pytest.raises(InvalidRequestError):
        _ = dataset.display_data
    with pytest.raises(InvalidRequestError):
        _ = dataset.data


async def test_dataset_of_listed_widget_raises_on_payload_access(
    db_session: AsyncSession, stored_dataset: Dataset
) -> None:
    [widget] = await SqlWidgetRepository(db_session).list_ordered()

    assert widget.dataset is not None
    _assert_payload_raises(widget.dataset)


async def test_dataset_from_get_raises_on_payload_access(
    db_session: AsyncSession, stored_dataset: Dataset
) -> None:
    dataset = await SqlDatasetRepository(db_session).get(stored_dataset.id)

    assert dataset is not None
    _assert_payload_raises(dataset)


async def test_dataset_from_listing_raises_on_payload_access(
    db_session: AsyncSession, stored_dataset: Dataset
) -> None:
    [(dataset, _)] = await SqlDatasetRepository(db_session).list_with_widget_counts()

    _assert_payload_raises(dataset)
