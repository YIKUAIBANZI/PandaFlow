from pandaflow.shared.contracts import SkillStatus
import pytest
from pydantic import ValidationError

from pandaflow.skills.welfare_risk_dispatcher.schemas import RiskDispatchRequest
from pandaflow.skills.welfare_risk_dispatcher.service import dispatch_risk


def test_high_heat_route_through_outdoor_node_requests_replanning():
    result = dispatch_risk(
        RiskDispatchRequest(
            temperature_celsius=33,
            crowd_level="high",
            route_nodes=["north_gate", "panda_nursery", "bamboo_grove"],
        )
    )

    assert result.status is SkillStatus.OK
    assert result.data["risk_level"] == "high"
    assert result.data["replan_required"] is True
    assert "bamboo_grove" in result.data["avoid_nodes"]
    assert result.demo_data is True


def test_closed_route_node_requests_replanning_at_normal_temperature():
    result = dispatch_risk(
        RiskDispatchRequest(
            temperature_celsius=22,
            crowd_level="low",
            route_nodes=["north_gate", "panda_nursery", "bamboo_grove"],
            closed_nodes=["bamboo_grove"],
        )
    )

    assert result.status is SkillStatus.OK
    assert result.data["risk_level"] == "high"
    assert result.data["replan_required"] is True
    assert result.data["avoid_nodes"] == ["bamboo_grove"]


def test_normal_conditions_keep_the_existing_route():
    result = dispatch_risk(
        RiskDispatchRequest(
            temperature_celsius=22,
            crowd_level="low",
            route_nodes=["north_gate", "panda_nursery", "science_hall"],
        )
    )

    assert result.status is SkillStatus.OK
    assert result.data["risk_level"] == "low"
    assert result.data["replan_required"] is False
    assert result.data["avoid_nodes"] == []


def test_complete_weather_snapshot_is_preserved_as_decision_evidence():
    result = dispatch_risk(
        RiskDispatchRequest(
            temperature_celsius=22,
            apparent_temperature_celsius=24,
            precipitation_mm=0.4,
            weather_code=3,
            wind_speed_kmh=8.4,
            crowd_level="low",
            route_nodes=["north_gate", "science_hall"],
        )
    )

    assert result.data["weather"] == {
        "temperature_celsius": 22.0,
        "apparent_temperature_celsius": 24.0,
        "precipitation_mm": 0.4,
        "weather_code": 3,
        "wind_speed_kmh": 8.4,
        "source": "caller_supplied",
    }


def test_independent_skill_rejects_a_claim_of_verified_open_meteo_provenance():
    with pytest.raises(ValidationError):
        RiskDispatchRequest(
            temperature_celsius=22,
            weather_source="open_meteo",
            crowd_level="low",
        )
