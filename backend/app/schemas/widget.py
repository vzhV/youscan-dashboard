from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.core.enums import DatasetOrigin, WidgetType
from app.schemas.common import RequestModel, TextContent, Title

EXAMPLE_ID = "0b1f6a0e-5d3c-4c1e-9d55-2f0a6b7c8d9e"
EXAMPLE_TIMESTAMP = "2026-10-27T09:30:00Z"


class WidgetSource(BaseModel):
    dataset_id: UUID = Field(description="Dataset that backs the chart.", examples=[EXAMPLE_ID])
    origin: DatasetOrigin = Field(
        description="Where the dataset came from: a seed file, an upload or random generation.",
        examples=["seed"],
    )
    filename: str | None = Field(
        description="Source file name; null for generated data.", examples=["line-and-pie.xlsx"]
    )
    sheet: str | None = Field(
        description="Source sheet name; null for CSV files and generated data.", examples=["line chart data"]
    )


class WidgetRead(BaseModel):
    id: UUID = Field(description="Widget identifier.", examples=[EXAMPLE_ID])
    type: WidgetType = Field(description="Kind of widget.", examples=["line"])
    title: str = Field(description="Widget title shown on the card.", examples=["Line chart 1"])
    position: int = Field(description="Zero-based order on the board.", examples=[0])
    text_content: str | None = Field(description="Body of a text widget; null for charts.", examples=[None])
    source: WidgetSource | None = Field(
        description="Dataset metadata for chart widgets; null for text widgets.",
        examples=[
            {
                "dataset_id": EXAMPLE_ID,
                "origin": "seed",
                "filename": "line-and-pie.xlsx",
                "sheet": "line chart data",
            }
        ],
    )
    created_at: datetime = Field(description="When the widget was created.", examples=[EXAMPLE_TIMESTAMP])
    updated_at: datetime = Field(
        description="When the widget was last changed.", examples=[EXAMPLE_TIMESTAMP]
    )


class WidgetCreate(RequestModel):
    type: WidgetType = Field(description="Kind of widget to create.", examples=["bar"])
    title: Title | None = Field(
        default=None,
        description="Widget title; defaults to a numbered name such as 'Bar chart 2'.",
        examples=["Revenue by region"],
    )


class WidgetUpdate(RequestModel):
    title: Title | None = Field(default=None, description="New widget title.", examples=["Renamed"])
    text_content: TextContent | None = Field(
        default=None, description="New body; only text widgets accept it.", examples=["Updated notes"]
    )

    @model_validator(mode="after")
    def _require_a_change(self) -> Self:
        if self.title is None and self.text_content is None:
            raise ValueError("Provide title or text_content")
        return self
