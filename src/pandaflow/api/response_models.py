"""Precise HTTP response models layered over the stable SkillResponse wire format."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from pandaflow.integrations.open_meteo import WeatherSnapshot
from pandaflow.shared.contracts import SkillResponse
from pandaflow.skills.incident_triage_dispatch.schemas import IncidentCategory
from pandaflow.skills.operations_review.schemas import ExecutionRecord


class StrictData(BaseModel):
    """Reject undocumented response fields during HTTP serialization."""

    model_config = ConfigDict(extra="forbid")


class VisitorPolicyData(StrictData):
    eligible: bool | None
    missing_fields: list[str] | None = None
    reason: str | None = None
    visit_date: date | None = None
    entry_slot: Literal["morning", "afternoon"] | None = None


class VisitorPolicyResponse(SkillResponse):
    skill: Literal["visitor-policy-check"]
    data: VisitorPolicyData


class ItineraryStep(StrictData):
    node_id: str
    arrival_after_minutes: int = Field(ge=0)
    dwell_minutes: int = Field(ge=0)


class ItineraryData(StrictData):
    itinerary: list[ItineraryStep]
    total_minutes: int = Field(ge=0)
    rest_stops: list[str]
    omitted_preferences: list[str]
    fulfilled_preferences: list[str]


class ItineraryResponse(SkillResponse):
    skill: Literal["accessible-itinerary-planner"]
    data: ItineraryData


class KnowledgeData(StrictData):
    answer: str | None


class KnowledgeResponse(SkillResponse):
    skill: Literal["panda-knowledge-guard"]
    data: KnowledgeData


class RiskWeatherEvidence(StrictData):
    temperature_celsius: float = Field(ge=-50, le=60)
    apparent_temperature_celsius: float | None = Field(default=None, ge=-80, le=80)
    precipitation_mm: float | None = Field(default=None, ge=0, le=2_000)
    weather_code: int | None = Field(default=None, ge=0, le=99)
    wind_speed_kmh: float | None = Field(default=None, ge=0, le=500)
    source: Literal["caller_supplied"]


class RiskDispatchData(StrictData):
    risk_level: Literal["low", "high"]
    replan_required: bool
    avoid_nodes: list[str]
    active_avoid_nodes: list[str]
    reasons: list[str]
    weather: RiskWeatherEvidence


class RiskDispatchResponse(SkillResponse):
    skill: Literal["welfare-risk-dispatcher"]
    data: RiskDispatchData


class IncidentData(StrictData):
    category: IncidentCategory | Literal["unknown"]
    priority: Literal["P0", "P1", "P2", "P3"] | None
    responsible_role: str
    immediate_actions: list[str]
    prohibited_actions: list[str]
    reply_template: str
    dispatch_status: Literal["draft"]
    sent: Literal[False]
    missing_fields: list[str]
    rule_version: str | None
    safety_signals: list[str]


class IncidentResponse(SkillResponse):
    skill: Literal["incident-triage-dispatch"]
    data: IncidentData


class ReviewObservation(StrictData):
    kind: str
    count: int = Field(ge=1)
    recommendation: str
    record_ids: list[str]


class RuleUpdateCandidate(StrictData):
    rule_ref: str
    trigger_status: str
    record_ids: list[str]
    recommendation: str


class OperationsReviewData(StrictData):
    total_calls: int = Field(ge=0)
    sample_size: int = Field(ge=0)
    status_counts: dict[str, int] | None = None
    skill_counts: dict[str, int] | None = None
    degraded_count: int | None = Field(default=None, ge=0)
    rule_hit_counts: dict[str, int] | None = None
    event_counts: dict[str, int] | None = None
    observations: list[ReviewObservation]
    rule_update_candidates: list[RuleUpdateCandidate]
    record_ids: list[str] | None = None
    causal_claims: Literal[False]
    rule_version: str | None = None


class OperationsReviewResponse(SkillResponse):
    skill: Literal["operations-review"]
    data: OperationsReviewData


StoppedResponse = (
    VisitorPolicyResponse
    | ItineraryResponse
    | KnowledgeResponse
    | RiskDispatchResponse
    | IncidentResponse
)


class DemoData(StrictData):
    weather: WeatherSnapshot | None = None
    policy: VisitorPolicyResponse | None = None
    initial_itinerary: ItineraryResponse | None = None
    risk: RiskDispatchResponse | None = None
    final_itinerary: ItineraryResponse | None = None
    incident: IncidentResponse | None = None
    knowledge: KnowledgeResponse | None = None
    replanned: bool | None = None
    stopped_after: str | None = None
    response: StoppedResponse | None = None
    violating_nodes: list[str] | None = None
    execution_records: list[ExecutionRecord]
    review: OperationsReviewResponse


class DemoResponse(SkillResponse):
    skill: Literal["pandaflow-demo-orchestrator"]
    data: DemoData
