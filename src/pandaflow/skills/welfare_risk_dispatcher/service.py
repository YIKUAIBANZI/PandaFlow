"""Deterministic risk dispatch without animal-health inference or real-world actions."""

from pandaflow.shared.contracts import SkillResponse, SkillStatus
from pandaflow.shared.rules import load_json_resource
from pandaflow.skills.welfare_risk_dispatcher.schemas import RiskDispatchRequest


SKILL_NAME = "welfare-risk-dispatcher"


def _weather_evidence(request: RiskDispatchRequest) -> dict[str, object]:
    return {
        "temperature_celsius": request.temperature_celsius,
        "apparent_temperature_celsius": request.apparent_temperature_celsius,
        "precipitation_mm": request.precipitation_mm,
        "weather_code": request.weather_code,
        "wind_speed_kmh": request.wind_speed_kmh,
        "source": "caller_supplied",
    }


def dispatch_risk(request: RiskDispatchRequest) -> SkillResponse:
    """Request a route replan when demo high heat affects outdoor route nodes."""

    rules = load_json_resource("welfare_rules.json")
    route_nodes = set(request.route_nodes)
    active_avoid_nodes = set(request.closed_nodes)
    reasons: list[str] = []
    rule_refs: list[str] = []
    warnings: list[str] = []

    if request.closed_nodes:
        reasons.append("A demo route area is marked closed.")
        rule_refs.append("rule_demo_area_closure")
        warnings.append("Demo closure state: do not claim that a real venue has been notified.")

    if request.temperature_celsius >= rules["high_heat_celsius"]:
        active_avoid_nodes.update(rules["outdoor_nodes"])
        reasons.append(
            "Temperature meets the demo high-heat threshold for outdoor route areas."
        )
        rule_refs.append("rule_demo_high_heat_outdoor")
        warnings.append(
            "Demo welfare rule: do not infer an individual animal's health or location."
        )

    active_avoid_nodes_list = sorted(active_avoid_nodes)
    avoid_nodes = sorted(route_nodes & active_avoid_nodes)
    if avoid_nodes:
        return SkillResponse.create(
            skill=SKILL_NAME,
            status=SkillStatus.OK,
            data={
                "risk_level": "high",
                "replan_required": True,
                "avoid_nodes": avoid_nodes,
                "active_avoid_nodes": active_avoid_nodes_list,
                "reasons": reasons,
                "weather": _weather_evidence(request),
            },
            source_refs=rules["source_refs"],
            rule_refs=rule_refs,
            warnings=warnings,
            next_actions=["Replan with all active forbidden nodes excluded."],
            demo_data=True,
        )
    return SkillResponse.create(
        skill=SKILL_NAME,
        status=SkillStatus.OK,
        data={
            "risk_level": "low",
            "replan_required": False,
            "avoid_nodes": [],
            "active_avoid_nodes": active_avoid_nodes_list,
            "reasons": ["No demo high-risk route condition was detected."],
            "weather": _weather_evidence(request),
        },
        source_refs=rules["source_refs"],
        rule_refs=rule_refs or ["rule_demo_normal_conditions"],
        warnings=warnings or [
            "Demo welfare rule: do not infer an individual animal's health or location."
        ],
        next_actions=[],
        demo_data=True,
    )
