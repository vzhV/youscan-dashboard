from typing import Literal

from pydantic import BaseModel, Field


class HealthRead(BaseModel):
    status: Literal["ok"] = Field(description="Always `ok` when the service is up.", examples=["ok"])
