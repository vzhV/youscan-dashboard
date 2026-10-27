from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

TITLE_MAX_LENGTH = 100
TEXT_MAX_LENGTH = 10_000

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=TITLE_MAX_LENGTH)]
TextContent = Annotated[str, StringConstraints(max_length=TEXT_MAX_LENGTH)]


class RequestModel(BaseModel):
    """Base for request bodies: unknown fields are a 422 instead of being silently ignored."""

    model_config = ConfigDict(extra="forbid")


class ErrorBody(BaseModel):
    code: str = Field(description="Stable machine-readable error code in snake_case.", examples=["not_found"])
    message: str = Field(description="Human-readable explanation.", examples=["Widget not found"])
    details: dict[str, object] | None = Field(
        default=None,
        description="Optional structured context, such as the offending fields; null when there is none.",
        examples=[{"fields": [{"loc": ["body", "title"], "message": "Field required"}]}],
    )


class ErrorResponse(BaseModel):
    error: ErrorBody = Field(
        description="The error that occurred.",
        examples=[{"code": "not_found", "message": "Widget not found", "details": None}],
    )
