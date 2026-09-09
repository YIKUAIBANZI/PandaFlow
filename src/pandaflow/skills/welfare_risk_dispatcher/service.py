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
    outdoor_route_nodes = [node for node in request.route_nodes if node in rules["outdoor_nodes"]]
    closed_route_nodes = [node for node in request.route_nodes if node in request.closed_nodes]
    if closed_route_nodes:
        return SkillResponse.create(
            skill=SKILL_NAME,
            status=SkillStatus.OK,
            data={
                "risk_level": "high",
                "replan_required": True,
                "avoid_nodes": closed_route_nodes,
                "reasons": ["A demo route area is marked closed."],
                "weather": _weather_evidence(request),
            },
            source_refs=rules["source_refs"],
            rule_refs=["rule_demo_area_closure"],
            warnings=["Demo closure state: do not claim that a real venue has been notified."],
            next_actions=["Replan with the listed nodes excluded."],
            demo_data=True,
        )
    if request.temperature_celsius >= rules["high_heat_celsius"] and outdoor_route_nodes:
        return SkillResponse.create(
            skill=SKILL_NAME,
            status=SkillStatus.OK,
            data={
                "risk_level": "high",
                "replan_required": True,
                "avoid_nodes": outdoor_route_nodes,
                "reasons": ["Temperature meets the demo high-heat threshold for outdoor route areas."],
                "weather": _weather_evidence(request),
            },
            source_refs=rules["source_refs"],
            rule_refs=["rule_demo_high_heat_outdoor"],
            warnings=["Demo welfare rule: do not infer an individual animal's health or location."],
            next_actions=["Replan with the listed nodes excluded."],
            demo_data=True,
        )
    return SkillResponse.create(
        skill=SKILL_NAME,
        status=SkillStatus.OK,
        data={
            "risk_level": "low",
            "replan_required": False,
            "avoid_nodes": [],
            "reasons": ["No demo high-risk route condition was detected."],
            "weather": _weather_evidence(request),
        },
        source_refs=rules["source_refs"],
        rule_refs=["rule_demo_normal_conditions"],
        warnings=["Demo welfare rule: do not infer an individual animal's health or location."],
        next_actions=[],
        demo_data=True,
    )
