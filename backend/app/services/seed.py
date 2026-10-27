from dataclasses import dataclass
from pathlib import Path

from app.core.enums import ChartType

SEED_DATA_DIR = Path(__file__).resolve().parents[2] / "seed_data"


@dataclass(frozen=True)
class SeedEntry:
    filename: str
    sheet: str | None
    chart_type: ChartType
    title: str


SEED_ENTRIES = (
    SeedEntry("line-and-pie.xlsx", "line chart data", ChartType.LINE, "Campaign results over time"),
    SeedEntry("line-and-pie.xlsx", "pie chart data", ChartType.PIE, "Results by campaign"),
    SeedEntry("stacked-bar.csv", None, ChartType.STACKED_BAR, "Sentiment by brand"),
)
