import json
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, File, Form, Request, UploadFile

from app.api.deps import ImportServiceDep
from app.api.errors import error_responses
from app.api.uploads import parse_selections, read_upload
from app.schemas.imports import ImportPreview, ImportResult
from app.services.import_preview import preview_file

router = APIRouter(prefix="/imports", tags=["imports"])

FILE_DESCRIPTION = "The .xlsx or .csv file to import."
FILE_EXAMPLE = "line-and-pie.xlsx"
SELECTIONS_DESCRIPTION = (
    "JSON array with one entry per sheet to import: `sheet` (omit for CSV), `chart_type` and an optional "
    "`title`. Between 1 and 20 entries."
)
SELECTIONS_EXAMPLE = json.dumps([{"sheet": "line chart data", "chart_type": "line", "title": "Results"}])

FileUpload = Annotated[UploadFile, File(description=FILE_DESCRIPTION, examples=[FILE_EXAMPLE])]
SelectionsForm = Annotated[str, Form(description=SELECTIONS_DESCRIPTION, examples=[SELECTIONS_EXAMPLE])]


@router.post(
    "/preview",
    name="preview",
    summary="Preview a file before importing it",
    status_code=HTTPStatus.OK,
    response_model=ImportPreview,
    responses=error_responses(
        HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
        HTTPStatus.UNPROCESSABLE_ENTITY,
    ),
)
async def preview_import(request: Request, file: FileUpload) -> ImportPreview:
    """Read a file and report each sheet's columns, sample rows, suggested chart type and column mapping.

    Nothing is stored. A sheet that cannot be charted carries an `issue` instead of failing the preview.
    """
    source = await read_upload(file, request.app.state.settings.max_upload_bytes)
    return await preview_file(source)


@router.post(
    "",
    name="create",
    summary="Import selected sheets as widgets",
    status_code=HTTPStatus.CREATED,
    response_model=ImportResult,
    responses=error_responses(
        HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
        HTTPStatus.UNPROCESSABLE_ENTITY,
        HTTPStatus.SERVICE_UNAVAILABLE,
    ),
)
async def create_import(
    request: Request, file: FileUpload, selections: SelectionsForm, service: ImportServiceDep
) -> ImportResult:
    """Create a dataset and a widget for every selected sheet and append the widgets to the board.

    The import is all or nothing: if any selection is invalid, nothing is stored.
    """
    source = await read_upload(file, request.app.state.settings.max_upload_bytes)
    return await service.import_file(source, parse_selections(selections))
