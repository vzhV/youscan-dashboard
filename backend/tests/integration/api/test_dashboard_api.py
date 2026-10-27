from pathlib import Path

import pytest
from httpx import AsyncClient

from app.schemas.widget import WidgetRead
from app.services.seed import SEED_ENTRIES
from tests.factories import SEED_TITLES

RESET_URL = "/api/v1/dashboard/reset"
WIDGETS_URL = "/api/v1/widgets"


async def test_reset_returns_seed_widgets(client: AsyncClient) -> None:
    response = await client.post(RESET_URL)

    widgets = [WidgetRead.model_validate(item) for item in response.json()]
    assert response.status_code == 200
    assert [widget.title for widget in widgets] == SEED_TITLES


async def test_reset_replaces_user_widgets(client: AsyncClient) -> None:
    await client.post(WIDGETS_URL, json={"type": "text"})
    await client.post(RESET_URL)

    titles = [item["title"] for item in (await client.get(WIDGETS_URL)).json()]

    assert titles == SEED_TITLES


async def test_reset_with_corrupt_seed_file_returns_500_and_keeps_the_board(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    await client.post(RESET_URL)
    for entry in SEED_ENTRIES:
        (tmp_path / entry.filename).write_bytes(b"not a spreadsheet")
    monkeypatch.setattr("app.services.import_service.SEED_DATA_DIR", tmp_path)

    response = await client.post(RESET_URL)

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "seed_data_invalid"
    assert [item["title"] for item in (await client.get(WIDGETS_URL)).json()] == SEED_TITLES
