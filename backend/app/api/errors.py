import logging
from collections.abc import Mapping, Sequence
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import (
    BoardNotEmptyError,
    ChartTypeMismatchError,
    DatabaseUnavailableError,
    DomainError,
    DomainValidationError,
    DuplicatePointError,
    FileTooLargeError,
    InvalidFileError,
    LimitExceededError,
    NotFoundError,
    NotShapeableError,
    SeedDataError,
    SheetNotFoundError,
    UnsupportedFileTypeError,
    WidgetHasNoDataError,
)
from app.schemas.common import ErrorBody, ErrorResponse

logger = logging.getLogger(__name__)

INTERNAL_ERROR_CODE = "internal_error"
INTERNAL_ERROR_MESSAGE = "Internal server error"
VALIDATION_ERROR_CODE = "validation_error"
VALIDATION_ERROR_MESSAGE = "Request validation failed"

STATUS_BY_ERROR: Mapping[type[DomainError], int] = {
    NotFoundError: HTTPStatus.NOT_FOUND,
    DomainValidationError: HTTPStatus.UNPROCESSABLE_ENTITY,
    InvalidFileError: HTTPStatus.UNPROCESSABLE_ENTITY,
    SheetNotFoundError: HTTPStatus.UNPROCESSABLE_ENTITY,
    NotShapeableError: HTTPStatus.UNPROCESSABLE_ENTITY,
    ChartTypeMismatchError: HTTPStatus.UNPROCESSABLE_ENTITY,
    DuplicatePointError: HTTPStatus.UNPROCESSABLE_ENTITY,
    LimitExceededError: HTTPStatus.UNPROCESSABLE_ENTITY,
    WidgetHasNoDataError: HTTPStatus.CONFLICT,
    BoardNotEmptyError: HTTPStatus.CONFLICT,
    UnsupportedFileTypeError: HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
    FileTooLargeError: HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
    DatabaseUnavailableError: HTTPStatus.SERVICE_UNAVAILABLE,
    SeedDataError: HTTPStatus.INTERNAL_SERVER_ERROR,
}


ERROR_EXAMPLES: Mapping[int, ErrorBody] = {
    HTTPStatus.NOT_FOUND: ErrorBody(
        code="not_found",
        message="Widget not found",
        details={"widget_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"},
    ),
    HTTPStatus.CONFLICT: ErrorBody(
        code="widget_has_no_data", message="Text widgets have no chart data", details=None
    ),
    HTTPStatus.REQUEST_ENTITY_TOO_LARGE: ErrorBody(
        code="file_too_large", message="File is larger than 4 MB", details={"max_bytes": 4_194_304}
    ),
    HTTPStatus.UNSUPPORTED_MEDIA_TYPE: ErrorBody(
        code="unsupported_file_type",
        message="Unsupported file type '.txt'. Supported: .csv, .xlsx",
        details={"supported": [".csv", ".xlsx"]},
    ),
    HTTPStatus.UNPROCESSABLE_ENTITY: ErrorBody(
        code=VALIDATION_ERROR_CODE,
        message=VALIDATION_ERROR_MESSAGE,
        details={"fields": [{"loc": ["body", "title"], "message": "Field required"}]},
    ),
    HTTPStatus.INTERNAL_SERVER_ERROR: ErrorBody(
        code=INTERNAL_ERROR_CODE, message=INTERNAL_ERROR_MESSAGE, details=None
    ),
    HTTPStatus.SERVICE_UNAVAILABLE: ErrorBody(
        code="database_unavailable", message="Database is unreachable", details=None
    ),
}


def invalid_path_parameter_example(param: str) -> ErrorBody:
    """The 422 a malformed UUID path parameter produces."""
    field = {
        "loc": ["path", param],
        "message": "Input should be a valid UUID, invalid character: found `n` at 0",
    }
    return ErrorBody(
        code=VALIDATION_ERROR_CODE, message=VALIDATION_ERROR_MESSAGE, details={"fields": [field]}
    )


def error_responses(
    *statuses: int, examples: Mapping[int, ErrorBody] | None = None
) -> dict[int | str, dict[str, Any]]:
    """Build a route's `responses=` mapping; 500 is always documented.

    `examples` replaces the shared example of a status for routes whose error reads differently.
    Any comes from FastAPI's own `responses` parameter type.
    """
    documented = sorted({*statuses, HTTPStatus.INTERNAL_SERVER_ERROR})
    shown = {**ERROR_EXAMPLES, **(examples or {})}
    return {status: _documented(status, shown[status]) for status in documented}


def _documented(status: int, error: ErrorBody) -> dict[str, Any]:
    example = ErrorResponse(error=error).model_dump(mode="json")
    return {
        "model": ErrorResponse,
        "description": HTTPStatus(status).phrase,
        "content": {"application/json": {"example": example}},
    }


def build_error_response(
    status_code: int, body: ErrorBody, headers: Mapping[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(error=body).model_dump(mode="json"),
        headers=dict(headers) if headers else None,
    )


def status_for(error: DomainError) -> int:
    for error_class in type(error).__mro__:
        if error_class in STATUS_BY_ERROR:
            return STATUS_BY_ERROR[error_class]
    # An unmapped error is a programming mistake; raising lets the generic handler answer 500 internal_error.
    raise LookupError(f"No HTTP status registered for {type(error).__name__}")


async def handle_domain_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)  # noqa: S101  # narrows the handler's Exception parameter
    details = dict(exc.details) if exc.details is not None else None
    body = ErrorBody(code=exc.code, message=exc.message, details=details)
    status = status_for(exc)
    if status >= HTTPStatus.INTERNAL_SERVER_ERROR:
        logger.error("%s on %s %s", exc.code, request.method, request.url.path, exc_info=exc)
    return build_error_response(status, body)


def field_errors(errors: Sequence[Mapping[str, Any]]) -> list[dict[str, object]]:
    """Reduce pydantic error dicts to the `{loc, message}` shape every validation error uses."""
    return [{"loc": list(item["loc"]), "message": item["msg"]} for item in errors]


async def handle_validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101  # narrows the handler's Exception parameter
    details = {"fields": field_errors(exc.errors())}
    body = ErrorBody(code=VALIDATION_ERROR_CODE, message=VALIDATION_ERROR_MESSAGE, details=details)
    return build_error_response(HTTPStatus.UNPROCESSABLE_ENTITY, body)


async def handle_http_exception(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)  # noqa: S101  # narrows the handler's Exception parameter
    code = HTTPStatus(exc.status_code).phrase.lower().replace(" ", "_")
    body = ErrorBody(code=code, message=str(exc.detail), details=None)
    # Headers carry protocol data such as Allow on 405, so they must survive the rewrite.
    return build_error_response(exc.status_code, body, exc.headers)


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception on %s %s", request.method, request.url.path, exc_info=exc)
    body = ErrorBody(code=INTERNAL_ERROR_CODE, message=INTERNAL_ERROR_MESSAGE, details=None)
    return build_error_response(HTTPStatus.INTERNAL_SERVER_ERROR, body)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, handle_domain_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(Exception, handle_unexpected_error)
