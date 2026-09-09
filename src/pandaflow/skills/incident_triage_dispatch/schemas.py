"""Bounded, non-identifying incident input."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


IncidentCategory = Literal["medical", "missing_person", "lost_property", "ticketing", "order", "facility"]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]


class IncidentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    description: str = Field(default="", max_length=2000)
    area: str = Field(default="", max_length=100)
    involved_groups: list[Literal["child", "elder", "adult", "mobility_impaired"]] = Field(default_factory=list, max_length=4)
    is_ongoing: bool | None = None
    measures_taken: list[ShortText] = Field(default_factory=list, max_length=10)
    category_hint: IncidentCategory | None = None
