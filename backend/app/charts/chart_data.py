from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Series(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Series label shown in the legend.", examples=["Positive"])
    values: list[float | None] = Field(
        description="One value per category; null marks a gap.", examples=[[1137, 764, None]]
    )


class ChartData(BaseModel):
    model_config = ConfigDict(frozen=True)

    categories: list[str] = Field(
        description="Category labels (x axis, bar groups or pie slices).", examples=[["A", "B", "C"]]
    )
    series: list[Series] = Field(
        description="Data series; each has one value per category.",
        examples=[[{"name": "Positive", "values": [1137, 764, None]}]],
    )

    @model_validator(mode="after")
    def _series_match_categories(self) -> Self:
        for series in self.series:
            if len(series.values) != len(self.categories):
                raise ValueError(
                    f"Series '{series.name}' has {len(series.values)} values "
                    f"but there are {len(self.categories)} categories"
                )
        return self


def point_count(data: ChartData) -> int:
    return len(data.categories) * len(data.series)
