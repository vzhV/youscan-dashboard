import json
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.dataset_repository import SqlDatasetRepository
from app.schemas.imports import ImportPreview, ImportResult
from tests.factories import SEED_DATA_DIR

PREVIEW_URL = "/api/v1/imports/preview"
IMPORTS_URL = "/api/v1/imports"
WIDGETS_URL = "/api/v1/widgets"
XLSX_NAME = "line-and-pie.xlsx"
LINE_SELECTION = {"sheet": "line chart data", "chart_type": "line"}


def seed_upload(filename: str = XLSX_NAME) -> dict[str, tuple[str, bytes]]:
    return {"file": (filename, (SEED_DATA_DIR / filename).read_bytes())}


def selections_form(*selections: dict[str, str]) -> dict[str, str]:
    return {"selections": json.dumps(list(selections))}


@pytest.fixture
def small_upload_limit(app: FastAPI) -> Iterator[None]:
    original = app.state.settings
    app.state.settings = original.model_copy(update={"max_upload_mb": 1})
    yield
    app.state.settings = original


async def test_import_operation_ids_are_stable(client: AsyncClient) -> None:
    schema = (await client.get("/api/v1/openapi.json")).json()

    operation_ids = {
        operation["operationId"]
        for path, item in schema["paths"].items()
        if path.startswith(IMPORTS_URL)
        for operation in item.values()
    }

    assert operation_ids == {"imports-preview", "imports-create"}


async def test_preview_seed_xlsx_returns_two_sheets(client: AsyncClient) -> None:
    response = await client.post(PREVIEW_URL, files=seed_upload())

    assert response.status_code == 200
    preview = ImportPreview.model_validate(response.json())
    assert [sheet.sheet for sheet in preview.sheets] == ["line chart data", "pie chart data"]


async def test_preview_unsupported_extension_returns_415(client: AsyncClient) -> None:
    response = await client.post(PREVIEW_URL, files={"file": ("notes.txt", b"hello")})

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_file_type"


async def test_preview_part_without_filename_returns_422(client: AsyncClient) -> None:
    response = await client.post(PREVIEW_URL, files={"file": ("", b"hello")})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_preview_empty_file_returns_422_invalid_file(client: AsyncClient) -> None:
    response = await client.post(PREVIEW_URL, files={"file": ("empty.csv", b"")})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_file"


@pytest.mark.usefixtures("small_upload_limit")
async def test_upload_exactly_at_limit_is_accepted_and_one_byte_over_returns_413(
    client: AsyncClient,
) -> None:
    limit = 1024 * 1024
    header = b"day,a\n"
    row = b"2024-01-01,1\n"
    padding = limit - len(header) - len(row)
    # Blank lines keep the CSV valid while pinning the size exactly.
    at_limit = header + row + b"\n" * padding

    accepted = await client.post(PREVIEW_URL, files={"file": ("big.csv", at_limit)})
    rejected = await client.post(PREVIEW_URL, files={"file": ("big.csv", at_limit + b"\n")})

    assert accepted.status_code == 200
    assert rejected.status_code == 413
    assert "1 MB" in rejected.json()["error"]["message"]


async def test_import_returns_201_with_datasets_and_widgets(client: AsyncClient) -> None:
    response = await client.post(IMPORTS_URL, files=seed_upload(), data=selections_form(LINE_SELECTION))

    assert response.status_code == 201
    result = ImportResult.model_validate(response.json())
    assert result.datasets[0].widget_count == 1
    assert result.widgets[0].title == "line chart data"
    listed = (await client.get(WIDGETS_URL)).json()
    assert [widget["id"] for widget in listed] == [str(result.widgets[0].id)]


async def test_import_with_a_failing_selection_is_rejected_before_any_write(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    missing = {"sheet": "nope", "chart_type": "line"}

    response = await client.post(
        IMPORTS_URL, files=seed_upload(), data=selections_form(LINE_SELECTION, missing)
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "sheet_not_found"
    assert (await client.get(WIDGETS_URL)).json() == []
    assert await SqlDatasetRepository(db_session).list_with_widget_counts() == []


@pytest.mark.parametrize(
    "raw", ["not json", "[]", '[{"chart_type": "donut"}]', '[{"chart_type": "line", "x": 1}]']
)
async def test_import_with_malformed_selections_returns_422(client: AsyncClient, raw: str) -> None:
    response = await client.post(IMPORTS_URL, files=seed_upload(), data={"selections": raw})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["message"] == "Invalid selections"
    assert error["details"]["fields"]


async def test_import_with_too_many_selections_returns_422(client: AsyncClient) -> None:
    selections = [LINE_SELECTION] * 21

    response = await client.post(IMPORTS_URL, files=seed_upload(), data=selections_form(*selections))

    assert response.status_code == 422
    assert response.json()["error"]["message"] == "Invalid selections"


async def test_import_without_selections_returns_validation_error(client: AsyncClient) -> None:
    response = await client.post(IMPORTS_URL, files=seed_upload())

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
