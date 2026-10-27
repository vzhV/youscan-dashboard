from datetime import UTC, datetime
from uuid import uuid4

from app.charts.chart_data import ChartData, Series
from app.core.enums import DatasetOrigin
from app.repositories.protocols import DatasetRepository, WidgetRepository
from tests.factories import make_chart_widget, make_dataset, make_widget


async def test_list_with_widget_counts_hides_generated(
    dataset_repo: DatasetRepository, widget_repo: WidgetRepository
) -> None:
    seeded = await dataset_repo.add(make_dataset(name="seeded"))
    generated = await dataset_repo.add(make_dataset(name="random", origin=DatasetOrigin.GENERATED))
    await widget_repo.add(make_chart_widget(seeded.id))
    await widget_repo.add(make_chart_widget(seeded.id))
    await widget_repo.add(make_chart_widget(generated.id))

    listed = await dataset_repo.list_with_widget_counts()

    assert [(dataset.name, count) for dataset, count in listed] == [("seeded", 2)]


async def test_list_with_widget_counts_includes_datasets_without_widgets(
    dataset_repo: DatasetRepository,
) -> None:
    await dataset_repo.add(make_dataset(name="orphan"))

    listed = await dataset_repo.list_with_widget_counts()

    assert [(dataset.name, count) for dataset, count in listed] == [("orphan", 0)]


async def test_list_with_widget_counts_orders_by_creation_time(dataset_repo: DatasetRepository) -> None:
    await dataset_repo.add(make_dataset(name="newer", created_at=datetime(2026, 1, 2, tzinfo=UTC)))
    await dataset_repo.add(make_dataset(name="older", created_at=datetime(2026, 1, 1, tzinfo=UTC)))

    listed = await dataset_repo.list_with_widget_counts()

    assert [dataset.name for dataset, _ in listed] == ["older", "newer"]


async def test_get_unknown_dataset_returns_none(dataset_repo: DatasetRepository) -> None:
    assert await dataset_repo.get(uuid4()) is None


async def test_get_returns_added_dataset(dataset_repo: DatasetRepository) -> None:
    dataset = await dataset_repo.add(make_dataset(name="found"))

    found = await dataset_repo.get(dataset.id)

    assert found is not None
    assert found.name == "found"


async def test_get_display_data_returns_chart_data(dataset_repo: DatasetRepository) -> None:
    display_data = {"categories": ["a", "b"], "series": [{"name": "s", "values": [1.0, None]}]}
    dataset = await dataset_repo.add(make_dataset(display_data=display_data))

    chart_data = await dataset_repo.get_display_data(dataset.id)

    assert chart_data == ChartData(categories=["a", "b"], series=[Series(name="s", values=[1.0, None])])


async def test_get_display_data_for_unknown_dataset_returns_none(dataset_repo: DatasetRepository) -> None:
    assert await dataset_repo.get_display_data(uuid4()) is None


async def test_delete_dataset_removes_its_widgets(
    dataset_repo: DatasetRepository, widget_repo: WidgetRepository
) -> None:
    dataset = await dataset_repo.add(make_dataset())
    widget = await widget_repo.add(make_chart_widget(dataset.id))

    await dataset_repo.delete(dataset)

    assert await dataset_repo.get(dataset.id) is None
    assert await widget_repo.get(widget.id) is None
    assert await widget_repo.list_ordered() == []


async def test_delete_all_datasets(dataset_repo: DatasetRepository) -> None:
    datasets = [
        await dataset_repo.add(make_dataset()),
        await dataset_repo.add(make_dataset(origin=DatasetOrigin.GENERATED)),
    ]

    await dataset_repo.delete_all()

    assert await dataset_repo.list_with_widget_counts() == []
    for dataset in datasets:
        assert await dataset_repo.get(dataset.id) is None


async def test_delete_all_datasets_cascades_to_chart_widgets_and_keeps_text_widgets(
    dataset_repo: DatasetRepository, widget_repo: WidgetRepository
) -> None:
    dataset = await dataset_repo.add(make_dataset())
    chart_widget = await widget_repo.add(make_chart_widget(dataset.id))
    note = await widget_repo.add(make_widget(title="note", position=1))

    await dataset_repo.delete_all()

    assert await widget_repo.get(chart_widget.id) is None
    assert await widget_repo.get(note.id) is not None
    assert [widget.title for widget in await widget_repo.list_ordered()] == ["note"]
