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
}


def error_responses(*statuses: int) -> dict[int | str, dict[str, Any]]:
    """Build a route's `responses=` mapping; 500 is always documented.

    Any comes from FastAPI's own `responses` parameter type.
    """
    documented = sorted({*statuses, HTTPStatus.INTERNAL_SERVER_ERROR})
    return {
        status: {"model": ErrorResponse, "description": HTTPStatus(status).phrase} for status in documented
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


async def handle_domain_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)  # noqa: S101  # narrows the handler's Exception parameter
    details = dict(exc.details) if exc.details is not None else None
    body = ErrorBody(code=exc.code, message=exc.message, details=details)
    return build_error_response(status_for(exc), body)


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
