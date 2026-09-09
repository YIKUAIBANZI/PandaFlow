"""Stable, auditable response types shared by PandaFlow Skills."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SkillStatus(str, Enum):
    """Business outcome statuses allowed by the PandaFlow contract."""

    OK = "ok"
    NEEDS_INPUT = "needs_input"
    DEGRADED = "degraded"
    ESCALATED = "escalated"
    REJECTED = "rejected"


class SkillResponse(BaseModel):
    """The response envelope returned by every independent Skill."""

    status: SkillStatus
    request_id: str
    skill: str
    data: dict[str, Any]
    source_refs: list[str] = Field(default_factory=list)
    rule_refs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    demo_data: bool = False
    generated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        skill: str,
        status: SkillStatus,
        data: dict[str, Any],
        source_refs: list[str] | None = None,
        rule_refs: list[str] | None = None,
        warnings: list[str] | None = None,
        next_actions: list[str] | None = None,
        demo_data: bool = False,
    ) -> "SkillResponse":
        """Create a response with a traceable ID and an aware UTC timestamp."""

        return cls(
            status=status,
            request_id=f"req_{uuid4().hex}",
            skill=skill,
            data=data,
            source_refs=source_refs or [],
            rule_refs=rule_refs or [],
            warnings=warnings or [],
            next_actions=next_actions or [],
            demo_data=demo_data,
            generated_at=datetime.now(UTC),
        )
