from datetime import UTC, datetime
from uuid import uuid4

from app.core.enums import WidgetType
from app.repositories.protocols import DatasetRepository, WidgetRepository
from tests.factories import make_chart_widget, make_dataset, make_widget

EARLIER = datetime(2026, 1, 1, tzinfo=UTC)
LATER = datetime(2026, 1, 2, tzinfo=UTC)


async def test_list_ordered_sorts_by_position(widget_repo: WidgetRepository) -> None:
    for position, title in [(2, "c"), (0, "a"), (1, "b")]:
        await widget_repo.add(make_widget(title=title, position=position))

    widgets = await widget_repo.list_ordered()

    assert [widget.title for widget in widgets] == ["a", "b", "c"]


async def test_list_ordered_breaks_position_ties_by_creation_time(widget_repo: WidgetRepository) -> None:
    await widget_repo.add(make_widget(title="newer", position=0, created_at=LATER))
    await widget_repo.add(make_widget(title="older", position=0, created_at=EARLIER))

    widgets = await widget_repo.list_ordered()

    assert [widget.title for widget in widgets] == ["older", "newer"]


async def test_get_unknown_widget_returns_none(widget_repo: WidgetRepository) -> None:
    assert await widget_repo.get(uuid4()) is None


async def test_add_assigns_id_and_timestamps(widget_repo: WidgetRepository) -> None:
    widget = await widget_repo.add(make_widget())

    assert widget.id is not None
    assert widget.created_at is not None
    assert widget.updated_at is not None
    assert await widget_repo.get(widget.id) is widget


async def test_next_position_is_zero_on_an_empty_board(widget_repo: WidgetRepository) -> None:
    assert await widget_repo.next_position() == 0


async def test_next_position_is_max_plus_one(widget_repo: WidgetRepository) -> None:
    await widget_repo.add(make_widget(position=0))
    await widget_repo.add(make_widget(position=5))

    assert await widget_repo.next_position() == 6


async def test_count_by_type_counts_only_that_type(
    widget_repo: WidgetRepository, dataset_repo: DatasetRepository
) -> None:
    dataset = await dataset_repo.add(make_dataset())
    await widget_repo.add(make_chart_widget(dataset.id))
    await widget_repo.add(make_widget())
    await widget_repo.add(make_widget())

    assert await widget_repo.count_by_type(WidgetType.TEXT) == 2
    assert await widget_repo.count_by_type(WidgetType.LINE) == 1
    assert await widget_repo.count_by_type(WidgetType.PIE) == 0


async def test_listed_chart_widget_exposes_dataset_metadata(
    widget_repo: WidgetRepository, dataset_repo: DatasetRepository
) -> None:
    dataset = await dataset_repo.add(make_dataset(source_filename="x.csv"))
    await widget_repo.add(make_chart_widget(dataset.id))

    [widget] = await widget_repo.list_ordered()

    assert widget.dataset is not None
    assert widget.dataset.source_filename == "x.csv"


async def test_add_returns_chart_widget_with_dataset_loaded(
    widget_repo: WidgetRepository, dataset_repo: DatasetRepository
) -> None:
    dataset = await dataset_repo.add(make_dataset(source_filename="x.csv"))

    widget = await widget_repo.add(make_chart_widget(dataset.id, type=WidgetType.BAR))

    assert widget.dataset is not None
    assert widget.dataset.source_filename == "x.csv"


async def test_add_returns_text_widget_without_dataset(widget_repo: WidgetRepository) -> None:
    widget = await widget_repo.add(make_widget())

    assert widget.dataset is None


async def test_delete_widget_removes_only_that_widget(widget_repo: WidgetRepository) -> None:
    doomed = await widget_repo.add(make_widget(title="doomed", position=0))
    await widget_repo.add(make_widget(title="kept", position=1))

    await widget_repo.delete(doomed)

    assert await widget_repo.get(doomed.id) is None
    assert [widget.title for widget in await widget_repo.list_ordered()] == ["kept"]


async def test_delete_all_widgets(widget_repo: WidgetRepository) -> None:
    widgets = [await widget_repo.add(make_widget()), await widget_repo.add(make_widget())]

    await widget_repo.delete_all()

    assert await widget_repo.list_ordered() == []
    for widget in widgets:
        assert await widget_repo.get(widget.id) is None
