"""Privacy-safe input schema for the visitor-policy Skill."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class VisitorPolicyRequest(BaseModel):
    """Only the minimum non-identifying details needed for a pre-visit check."""

    model_config = ConfigDict(extra="forbid")

    visit_date: date | None = None
    entry_slot: Literal["morning", "afternoon"] | None = None
    reservation_status: Literal["confirmed", "missing", "unknown"] | None = None
    document_type: str | None = None
    language: Literal["zh", "en"] = "zh"
    accessibility_needs: list[str] = Field(default_factory=list)
