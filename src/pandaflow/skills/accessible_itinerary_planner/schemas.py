"""Input model for the deterministic itinerary planner."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


NodeId = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,99}$"),
]


class ItineraryRequest(BaseModel):
    """A non-identifying request for a short park itinerary."""

    model_config = ConfigDict(extra="forbid")

    entry_node: NodeId
    available_minutes: int = Field(ge=1, le=480)
    must_see: list[NodeId] = Field(default_factory=list, max_length=20)
    mobility_need: Literal["standard", "step_free"] = "standard"
    closed_nodes: list[NodeId] = Field(default_factory=list, max_length=20)
