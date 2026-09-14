"""Public, normalized catalog for the fixed PandaFlow demo scenarios."""

from copy import deepcopy
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from pandaflow.shared.rules import load_json_resource


SHANGHAI = ZoneInfo("Asia/Shanghai")
ALLOWED_IDS = {
    "normal_all_skills",
    "heat_replan",
    "human_escalation",
    "live_current_weather",
}


def load_demo_scenarios(*, current_date: date | None = None) -> dict[str, Any]:
    """Load the allowlisted catalog and resolve the live scenario's visit date."""

    resource = deepcopy(load_json_resource("demo_scenarios.json"))
    scenarios = resource.get("scenarios")
    if resource.get("classification") != "demo" or not isinstance(scenarios, list):
        raise ValueError("Demo scenario resource has an invalid structure.")

    scenario_ids = {
        row.get("id") for row in scenarios if isinstance(row, dict)
    }
    if scenario_ids != ALLOWED_IDS or len(scenarios) != len(ALLOWED_IDS):
        raise ValueError("Demo scenario resource has an invalid catalog.")

    resolved_date = current_date or datetime.now(SHANGHAI).date()
    for scenario in scenarios:
        title = scenario.get("title")
        request = scenario.get("request")
        if not isinstance(title, str) or not isinstance(request, dict):
            raise ValueError("Demo scenario resource has an invalid entry.")
        if scenario.get("requires_current_visit_date") is True:
            request["visit_date"] = resolved_date.isoformat()

    return {
        "classification": "demo",
        "demo_data": True,
        "generated_at": datetime.now(SHANGHAI).isoformat(),
        "scenarios": scenarios,
    }
