"""Input model for the deterministic itinerary planner."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ItineraryRequest(BaseModel):
    """A non-identifying request for a short park itinerary."""

    model_config = ConfigDict(extra="forbid")

    entry_node: str
    available_minutes: int = Field(ge=1, le=480)
    must_see: list[str] = Field(default_factory=list)
    mobility_need: Literal["standard", "step_free"] = "standard"
    closed_nodes: list[str] = Field(default_factory=list)
