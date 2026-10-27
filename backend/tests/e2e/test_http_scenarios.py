"""Black-box HTTP scenarios: the real app and lifespan against the migrated test database.

The CLI runs `asyncio.run`, so it is invoked in a worker thread from these async tests.
"""

import asyncio
from collections.abc import AsyncIterator, Callable

import pytest
from httpx import ASGITransport, AsyncClient
from typer.testing import CliRunner

from app.cli.app import cli
from app.core.config import get_settings
from app.main import create_app
from tests.factories import SEED_DATA_DIR, SEED_TITLES

API = "/api/v1"
CSV_NAME = "stacked-bar.csv"
STACKED_SELECTION = '[{"chart_type": "stacked_bar"}]'
CONCURRENT_RESETS = 4
RACE_ROUNDS = 5


@pytest.fixture
async def api() -> AsyncIterator[AsyncClient]:
    app = create_app(get_settings())
    # The lifespan builds the engine from the pinned test database.
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http_client,
    ):
        yield http_client


async def titles(api: AsyncClient) -> list[str]:
    return [widget["title"] for widget in (await api.get(f"{API}/widgets")).json()]


async def test_scenario_seed_then_manage_widgets(runner: CliRunner, api: AsyncClient) -> None:
    seeded = await asyncio.to_thread(runner.invoke, cli, ["seed"])
    assert seeded.exit_code == 0
    assert await titles(api) == SEED_TITLES

    created = await api.post(f"{API}/widgets", json={"type": "bar"})
    assert created.status_code == 201
    bar = created.json()
    assert (await api.get(f"{API}/widgets/{bar['id']}/data")).json()["categories"]

    note_response = await api.post(f"{API}/widgets", json={"type": "text"})
    assert note_response.status_code == 201
    note = note_response.json()
    patched = await api.patch(f"{API}/widgets/{note['id']}", json={"text_content": "Edited"})
    assert patched.status_code == 200
    assert (await api.get(f"{API}/widgets")).json()[-1]["text_content"] == "Edited"

    assert (await api.delete(f"{API}/widgets/{bar['id']}")).status_code == 204
    assert (await api.get(f"{API}/widgets/{bar['id']}/data")).status_code == 404


async def test_scenario_upload_then_manage_datasets(api: AsyncClient) -> None:
    files = {"file": (CSV_NAME, (SEED_DATA_DIR / CSV_NAME).read_bytes())}
    assert (await api.post(f"{API}/imports/preview", files=files)).status_code == 200
    imported = await api.post(f"{API}/imports", files=files, data={"selections": STACKED_SELECTION})
    assert imported.status_code == 201

    [dataset] = (await api.get(f"{API}/datasets")).json()
    assert dataset["origin"] == "upload"
    assert (await api.post(f"{API}/datasets/{dataset['id']}/widgets")).status_code == 201
    assert len(await titles(api)) == 2

    assert (await api.delete(f"{API}/datasets/{dataset['id']}")).status_code == 204
    assert await titles(api) == []


async def test_scenario_reset_restores_seed_board(api: AsyncClient) -> None:
    await api.post(f"{API}/widgets", json={"type": "text"})

    assert (await api.post(f"{API}/dashboard/reset")).status_code == 200

    assert await titles(api) == SEED_TITLES


async def test_scenario_concurrent_resets_leave_one_seed_board(
    api: AsyncClient, board_size: Callable[[], tuple[int, int]]
) -> None:
    responses = await asyncio.gather(*(api.post(f"{API}/dashboard/reset") for _ in range(CONCURRENT_RESETS)))

    assert {response.status_code for response in responses} == {200}
    assert board_size() == (len(SEED_TITLES), len(SEED_TITLES))


async def test_scenario_concurrent_add_and_delete_never_fails_with_a_server_error(
    api: AsyncClient, board_size: Callable[[], tuple[int, int]]
) -> None:
    files = {"file": (CSV_NAME, (SEED_DATA_DIR / CSV_NAME).read_bytes())}
    for _ in range(RACE_ROUNDS):
        await api.post(f"{API}/imports", files=files, data={"selections": STACKED_SELECTION})
        [dataset] = (await api.get(f"{API}/datasets")).json()

        add, delete = await asyncio.gather(
            api.post(f"{API}/datasets/{dataset['id']}/widgets"),
            api.delete(f"{API}/datasets/{dataset['id']}"),
        )

        assert add.status_code in {201, 404}
        assert delete.status_code == 204
        assert board_size() == (0, 0)
