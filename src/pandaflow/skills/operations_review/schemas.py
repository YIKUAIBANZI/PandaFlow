"""Metadata-only records; no incident text or visitor identifiers."""

from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from pandaflow.shared.contracts import SkillStatus
from pandaflow.skills.incident_triage_dispatch.schemas import IncidentCategory


SkillName = Literal[
    "visitor-policy-check", "accessible-itinerary-planner", "panda-knowledge-guard",
    "welfare-risk-dispatcher", "incident-triage-dispatch", "operations-review",
]
Reference = Annotated[str, StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,99}$")]


class ExecutionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: Annotated[str, StringConstraints(pattern=r"^req_[A-Za-z0-9_-]{1,80}$")]
    skill: SkillName
    status: SkillStatus
    rule_refs: list[Reference] = Field(default_factory=list, max_length=100)
    source_refs: list[Reference] = Field(default_factory=list, max_length=100)
    demo_data: bool = True
    incident_category: IncidentCategory | Literal["unknown"] | None = None
    priority: Literal["P0", "P1", "P2", "P3"] | None = None

    @model_validator(mode="after")
    def incident_fields_belong_to_incident_skill(self) -> Self:
        if self.skill != "incident-triage-dispatch" and (self.incident_category is not None or self.priority is not None):
            raise ValueError("Only incident executions may carry incident metadata.")
        return self


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Validate records inside the service so private fields produce a business
    # rejection without FastAPI echoing their values in a validation response.
    records: list[dict[str, Any]] = Field(default_factory=list, max_length=1000)
