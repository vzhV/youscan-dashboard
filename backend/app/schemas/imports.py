from pydantic import BaseModel, Field

from app.core.enums import ChartType
from app.importing.shaping.columns import ColumnKind
from app.schemas.common import ErrorBody, RequestModel, Title
from app.schemas.dataset import DatasetRead
from app.schemas.widget import WidgetRead

MAX_SELECTIONS = 20


class ColumnInfo(BaseModel):
    name: str = Field(description="Column header as written in the file.", examples=["Result"])
    kind: ColumnKind = Field(description="Kind of values the column holds.", examples=["number"])


class ColumnMappingRead(BaseModel):
    categories: str = Field(description="Column that becomes the chart categories.", examples=["Date"])
    series: str | None = Field(
        description="Column whose values become series (long format); null for wide format.",
        examples=["Campaign"],
    )
    values: list[str] = Field(description="Number columns that supply the values.", examples=[["Result"]])


class SheetPreview(BaseModel):
    sheet: str | None = Field(description="Sheet name; null for CSV files.", examples=["line chart data"])
    row_count: int = Field(description="Number of data rows.", examples=[212])
    columns: list[ColumnInfo] = Field(description="Every column with its detected kind.", examples=[[]])
    sample_rows: list[list[str | float | None]] = Field(
        description="The first data rows; dates are rendered as YYYY-MM-DD.",
        examples=[[[1.0, "A", "2024-10-28", 48.0]]],
    )
    suggested_chart_type: ChartType | None = Field(
        description="Best-fitting chart type; null when the sheet cannot be charted.", examples=["line"]
    )
    mapping: ColumnMappingRead | None = Field(
        description="How the columns map to the chart; null when the sheet cannot be charted.",
        examples=[{"categories": "Date", "series": "Campaign", "values": ["Result"]}],
    )
    issue: ErrorBody | None = Field(
        description="Why the sheet cannot be charted; null when it can.", examples=[None]
    )


class ImportPreview(BaseModel):
    filename: str = Field(description="Name of the uploaded file.", examples=["line-and-pie.xlsx"])
    sheets: list[SheetPreview] = Field(description="One entry per sheet; CSV files have one.", examples=[[]])


class ImportSelection(RequestModel):
    sheet: str | None = Field(
        default=None,
        description="Sheet to import; omit for CSV files or to take the first sheet.",
        examples=["line chart data"],
    )
    chart_type: ChartType = Field(description="Chart type to create from the sheet.", examples=["line"])
    title: Title | None = Field(
        default=None,
        description="Widget title; defaults to the sheet name (the file name for CSV).",
        examples=["Campaign results"],
    )


class ImportResult(BaseModel):
    datasets: list[DatasetRead] = Field(description="Datasets created by the import.", examples=[[]])
    widgets: list[WidgetRead] = Field(description="Widgets appended to the board.", examples=[[]])
