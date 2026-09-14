"""Thin orchestration for PandaFlow's fixed dynamic-demo story."""

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from pandaflow.shared.contracts import SkillResponse, SkillStatus
from pandaflow.skills.accessible_itinerary_planner.schemas import ItineraryRequest
from pandaflow.skills.accessible_itinerary_planner.service import plan_itinerary
from pandaflow.skills.visitor_policy_check.schemas import VisitorPolicyRequest
from pandaflow.skills.visitor_policy_check.service import evaluate_policy
from pandaflow.skills.welfare_risk_dispatcher.schemas import RiskDispatchRequest
from pandaflow.skills.welfare_risk_dispatcher.service import dispatch_risk
from pandaflow.skills.incident_triage_dispatch.schemas import IncidentRequest
from pandaflow.skills.incident_triage_dispatch.service import triage_incident
from pandaflow.skills.operations_review.schemas import ExecutionRecord, ReviewRequest
from pandaflow.skills.operations_review.service import review_operations
from pandaflow.skills.panda_knowledge_guard.schemas import KnowledgeRequest
from pandaflow.skills.panda_knowledge_guard.service import answer_question
from pandaflow.orchestrator.weather import WeatherFetcher, resolve_weather


class DemoRequest(BaseModel):
    """Non-identifying input for the fixed PandaFlow demonstration workflow."""

    model_config = ConfigDict(extra="forbid")

    visit_date: date
    temperature_celsius: float | None = Field(default=None, ge=-50, le=60)
    weather_mode: Literal["synthetic", "live_current"] = "synthetic"
    crowd_level: Literal["low", "medium", "high"]
    must_see: list[str] = Field(default_factory=lambda: ["panda_nursery", "science_hall"])
    incident: IncidentRequest | None = None
    knowledge: KnowledgeRequest | None = None


def _as_data(response: SkillResponse) -> dict[str, Any]:
    return response.model_dump(mode="json")


def _combined_refs(*responses: SkillResponse) -> tuple[list[str], list[str], list[str]]:
    sources = list(dict.fromkeys(ref for response in responses for ref in response.source_refs))
    rules = list(dict.fromkeys(ref for response in responses for ref in response.rule_refs))
    warnings = [warning for response in responses for warning in response.warnings]
    return sources, rules, warnings


def run_demo(
    request: DemoRequest, *, weather_fetcher: WeatherFetcher | None = None
) -> SkillResponse:
    """Prioritize reported incidents and review every completed or stopped flow."""

    responses: list[SkillResponse] = []
    extra_data: dict[str, Any] = {}
    # A reported ongoing incident must not wait behind ordinary trip planning.
    if request.incident is not None:
        incident = triage_incident(request.incident)
        responses.append(incident)
        extra_data["incident"] = _as_data(incident)
        if incident.status is not SkillStatus.OK:
            return _stopped(incident, "Incident requires human assistance or more information.", responses)

    policy = evaluate_policy(
        VisitorPolicyRequest(
            visit_date=request.visit_date,
            entry_slot="morning",
            reservation_status="confirmed",
            document_type="passport",
            accessibility_needs=["elder_companion"],
        )
    )
    responses.append(policy)
    if policy.status is not SkillStatus.OK:
        return _stopped(policy, "Policy validation did not permit itinerary planning.", responses)

    itinerary_request = ItineraryRequest(
        entry_node="north_gate",
        available_minutes=120,
        must_see=request.must_see,
        mobility_need="step_free",
    )
    initial_itinerary = plan_itinerary(itinerary_request)
    responses.append(initial_itinerary)
    if initial_itinerary.status is not SkillStatus.OK:
        return _stopped(initial_itinerary, "No safe initial itinerary was available.", responses)

    route_nodes = [step["node_id"] for step in initial_itinerary.data["itinerary"]]
    weather = resolve_weather(
        mode=request.weather_mode,
        temperature_celsius=request.temperature_celsius,
        visit_date=request.visit_date,
        fetcher=weather_fetcher,
    )
    snapshot = weather.snapshot
    risk = dispatch_risk(
        RiskDispatchRequest(
            temperature_celsius=snapshot.temperature_celsius,
            apparent_temperature_celsius=snapshot.apparent_temperature_celsius,
            precipitation_mm=snapshot.precipitation_mm,
            weather_code=snapshot.weather_code,
            wind_speed_kmh=snapshot.wind_speed_kmh,
            crowd_level=request.crowd_level,
            route_nodes=route_nodes,
        )
    )
    responses.append(risk)
    if risk.status is not SkillStatus.OK:
        return _stopped(risk, "Risk dispatch did not produce an actionable result.", responses)

    final_itinerary = initial_itinerary
    replanned = bool(risk.data["replan_required"])
    active_avoid_nodes = risk.data.get("active_avoid_nodes", risk.data["avoid_nodes"])
    if replanned:
        final_itinerary = plan_itinerary(
            itinerary_request.model_copy(update={"closed_nodes": active_avoid_nodes})
        )
        responses.append(final_itinerary)
        if final_itinerary.status is not SkillStatus.OK:
            return _stopped(
                final_itinerary,
                "Risk-aware replan did not produce a safe itinerary.",
                responses,
                context_data={"weather": snapshot.model_dump(mode="json")},
                extra_source_refs=weather.source_refs,
                extra_warnings=weather.warnings,
            )

    final_route_nodes = {
        step["node_id"] for step in final_itinerary.data["itinerary"]
    }
    violating_nodes = sorted(final_route_nodes & set(active_avoid_nodes))
    if violating_nodes:
        return _finish(
            responses,
            status=SkillStatus.REJECTED,
            data={
                **extra_data,
                "weather": snapshot.model_dump(mode="json"),
                "policy": _as_data(policy),
                "initial_itinerary": _as_data(initial_itinerary),
                "risk": _as_data(risk),
                "replanned": replanned,
                "stopped_after": "final-route-constraint-check",
                "violating_nodes": violating_nodes,
            },
            warnings=[
                "Final route failed an active hard-constraint check.",
                *weather.warnings,
            ],
            next_actions=["Ask staff for a safe alternative route."],
            extra_source_refs=weather.source_refs,
        )

    if request.knowledge is not None:
        knowledge = answer_question(request.knowledge)
        responses.append(knowledge)
        extra_data["knowledge"] = _as_data(knowledge)
        if knowledge.status not in {SkillStatus.OK, SkillStatus.NEEDS_INPUT}:
            return _stopped(
                knowledge,
                "Knowledge request did not produce a supported answer.",
                responses,
                context_data={"weather": snapshot.model_dump(mode="json")},
                extra_source_refs=weather.source_refs,
                extra_warnings=weather.warnings,
            )

    completion_status = weather.status
    if request.knowledge is not None and knowledge.status is SkillStatus.NEEDS_INPUT:
        completion_status = SkillStatus.NEEDS_INPUT

    return _finish(
        responses, status=completion_status,
        data={
            **extra_data,
            "weather": snapshot.model_dump(mode="json"),
            "policy": _as_data(policy),
            "initial_itinerary": _as_data(initial_itinerary),
            "risk": _as_data(risk),
            "final_itinerary": _as_data(final_itinerary),
            "replanned": replanned,
        },
        next_actions=["Continue with the final itinerary shown above.", *[action for response in responses if response.skill == "incident-triage-dispatch" for action in response.next_actions]],
        warnings=weather.warnings,
        extra_source_refs=weather.source_refs,
    )


def _stopped(
    response: SkillResponse,
    reason: str,
    responses: list[SkillResponse],
    *,
    context_data: dict[str, Any] | None = None,
    extra_source_refs: list[str] | None = None,
    extra_warnings: list[str] | None = None,
) -> SkillResponse:
    return _finish(
        responses,
        status=response.status,
        data={**(context_data or {}), "stopped_after": response.skill, "response": _as_data(response)},
        warnings=[reason, *(extra_warnings or [])],
        next_actions=response.next_actions,
        extra_source_refs=extra_source_refs,
    )


def _finish(
    responses: list[SkillResponse],
    *,
    status: SkillStatus,
    data: dict[str, Any],
    next_actions: list[str],
    warnings: list[str] | None = None,
    extra_source_refs: list[str] | None = None,
) -> SkillResponse:
    records = []
    for response in responses:
        record = ExecutionRecord(
            record_id=response.request_id, skill=response.skill, status=response.status,
            source_refs=response.source_refs, rule_refs=response.rule_refs, demo_data=response.demo_data,
            incident_category=response.data.get("category") if response.skill == "incident-triage-dispatch" else None,
            priority=response.data.get("priority") if response.skill == "incident-triage-dispatch" else None,
        )
        records.append(record.model_dump(mode="json", exclude_none=True))
    # The review's own invocation is excluded to avoid counting it recursively.
    review = review_operations(ReviewRequest(records=records))
    sources, rules, all_warnings = _combined_refs(*responses, review)
    sources = list(dict.fromkeys([*sources, *(extra_source_refs or [])]))
    if status is SkillStatus.OK and review.status is not SkillStatus.OK:
        status = review.status
    return SkillResponse.create(
        skill="pandaflow-demo-orchestrator", status=status,
        data={**data, "execution_records": records, "review": _as_data(review)},
        source_refs=sources, rule_refs=rules,
        warnings=[*(warnings or []), *all_warnings],
        next_actions=list(dict.fromkeys([*next_actions, *review.next_actions])), demo_data=True,
    )
