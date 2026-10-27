from collections.abc import Mapping
from typing import ClassVar


class DomainError(Exception):
    """Base for every expected failure; api/errors.py maps each subclass to an HTTP status."""

    code: ClassVar[str]

    def __init__(self, message: str, details: Mapping[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(DomainError):
    code = "not_found"


class DomainValidationError(DomainError):
    code = "validation_error"


class WidgetHasNoDataError(DomainError):
    code = "widget_has_no_data"


class BoardNotEmptyError(DomainError):
    code = "board_not_empty"


class UnsupportedFileTypeError(DomainError):
    code = "unsupported_file_type"


class FileTooLargeError(DomainError):
    code = "file_too_large"


class InvalidFileError(DomainError):
    code = "invalid_file"


class SheetNotFoundError(DomainError):
    code = "sheet_not_found"


class NotShapeableError(DomainError):
    code = "not_shapeable"


class ChartTypeMismatchError(DomainError):
    code = "chart_type_mismatch"


class DuplicatePointError(DomainError):
    code = "duplicate_point"


class LimitExceededError(DomainError):
    code = "limit_exceeded"


class DatabaseUnavailableError(DomainError):
    code = "database_unavailable"


class SeedDataError(DomainError):
    code = "seed_data_invalid"
