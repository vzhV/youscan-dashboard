import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import WidgetType
from app.models import Dataset, Widget
from tests.factories import make_dataset


async def test_text_widget_with_dataset_violates_check(db_session: AsyncSession) -> None:
    dataset = make_dataset()
    db_session.add(dataset)
    await db_session.flush()
    db_session.add(Widget(type=WidgetType.TEXT, title="t", position=0, dataset_id=dataset.id))

    with pytest.raises(IntegrityError, match="ck_widgets_text_iff_no_dataset"):
        await db_session.flush()


async def test_chart_widget_without_dataset_violates_check(db_session: AsyncSession) -> None:
    db_session.add(Widget(type=WidgetType.LINE, title="c", position=0))

    with pytest.raises(IntegrityError, match="ck_widgets_text_iff_no_dataset"):
        await db_session.flush()


async def test_chart_widget_with_text_content_violates_check(db_session: AsyncSession) -> None:
    dataset = make_dataset()
    db_session.add(dataset)
    await db_session.flush()
    db_session.add(
        Widget(type=WidgetType.PIE, title="c", position=0, dataset_id=dataset.id, text_content="x")
    )

    with pytest.raises(IntegrityError, match="ck_widgets_text_content_only_for_text"):
        await db_session.flush()


async def test_deleting_dataset_cascades_to_widgets(db_session: AsyncSession) -> None:
    dataset = make_dataset()
    db_session.add(dataset)
    await db_session.flush()
    db_session.add(Widget(type=WidgetType.LINE, title="c", position=0, dataset_id=dataset.id))
    await db_session.flush()

    await db_session.delete(dataset)
    await db_session.flush()

    assert (await db_session.execute(select(Widget))).scalars().all() == []


async def test_dataset_data_columns_raise_when_not_explicitly_loaded(db_session: AsyncSession) -> None:
    db_session.add(make_dataset())
    await db_session.flush()
    db_session.expunge_all()
    dataset = (await db_session.execute(select(Dataset))).scalar_one()

    with pytest.raises(InvalidRequestError):
        _ = dataset.display_data
