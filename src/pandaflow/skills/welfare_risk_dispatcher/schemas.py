"""Input schema for deterministic welfare risk dispatch."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RiskDispatchRequest(BaseModel):
    """Non-identifying route and demo-weather context."""

    model_config = ConfigDict(extra="forbid")

    temperature_celsius: float = Field(ge=-50, le=60)
    apparent_temperature_celsius: float | None = Field(default=None, ge=-80, le=80)
    precipitation_mm: float | None = Field(default=None, ge=0, le=2_000)
    weather_code: int | None = Field(default=None, ge=0, le=99)
    wind_speed_kmh: float | None = Field(default=None, ge=0, le=500)
    crowd_level: Literal["low", "medium", "high"]
    route_nodes: list[str] = Field(default_factory=list)
    closed_nodes: list[str] = Field(default_factory=list)
