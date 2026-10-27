from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums import ChartType, DatasetOrigin
from app.schemas.widget import EXAMPLE_ID, EXAMPLE_TIMESTAMP


class DatasetRead(BaseModel):
    id: UUID = Field(description="Dataset identifier.", examples=[EXAMPLE_ID])
    name: str = Field(
        description="Dataset name: the sheet name, or the file name for CSV.", examples=["line chart data"]
    )
    origin: DatasetOrigin = Field(
        description="Where the dataset came from: a seed file, an upload or random generation.",
        examples=["upload"],
    )
    chart_type: ChartType = Field(description="Chart type the data was validated for.", examples=["line"])
    source_filename: str | None = Field(
        description="Source file name; null for generated data.", examples=["line-and-pie.xlsx"]
    )
    source_sheet: str | None = Field(
        description="Source sheet name; null for CSV files and generated data.", examples=["line chart data"]
    )
    row_count: int = Field(description="Number of data rows in the source table.", examples=[212])
    widget_count: int = Field(description="Number of widgets that show this dataset.", examples=[1])
    created_at: datetime = Field(description="When the dataset was created.", examples=[EXAMPLE_TIMESTAMP])
