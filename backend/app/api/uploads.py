from typing import Annotated

from fastapi import UploadFile
from pydantic import Field, TypeAdapter, ValidationError

from app.api.errors import field_errors
from app.core.config import BYTES_PER_MEGABYTE
from app.core.errors import DomainValidationError, FileTooLargeError
from app.importing.source_file import SourceFile
from app.schemas.imports import MAX_SELECTIONS, ImportSelection

SELECTIONS_ADAPTER = TypeAdapter(
    Annotated[list[ImportSelection], Field(min_length=1, max_length=MAX_SELECTIONS)]
)


async def read_upload(file: UploadFile, max_bytes: int) -> SourceFile:
    # One byte past the limit is enough to know the file is too large without buffering all of it.
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        megabytes = max_bytes // BYTES_PER_MEGABYTE
        raise FileTooLargeError(f"File is larger than {megabytes} MB", details={"max_bytes": max_bytes})
    return SourceFile(file.filename or "", content)


def parse_selections(raw: str) -> list[ImportSelection]:
    try:
        return SELECTIONS_ADAPTER.validate_json(raw)
    except ValidationError as error:
        details = {"fields": field_errors(error.errors())}
        raise DomainValidationError("Invalid selections", details=details) from error
