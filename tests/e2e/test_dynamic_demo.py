from datetime import date

from pandaflow.integrations.open_meteo import OpenMeteoError, WeatherSnapshot
from pandaflow.shared.contracts import SkillStatus
from pandaflow.orchestrator.service import DemoRequest, run_demo
from pandaflow.skills.incident_triage_dispatch.schemas import IncidentRequest
from pandaflow.skills.panda_knowledge_guard.schemas import KnowledgeRequest


def _live_snapshot(*, temperature: float = 33) -> WeatherSnapshot:
    return WeatherSnapshot(
        temperature_celsius=temperature,
        apparent_temperature_celsius=36,
        precipitation_mm=0.2,
        weather_code=3,
        wind_speed_kmh=8.4,
        observed_at="2026-09-08T12:00",
        timezone="Asia/Shanghai",
        location_label="Chengdu Panda Base demo weather point",
        source="open_meteo",
        attribution="Weather data by Open-Meteo.com",
        attribution_url="https://open-meteo.com/",
        demo_data=False,
    )


def test_normal_weather_keeps_the_initial_itinerary():
    result = run_demo(
        DemoRequest(
            visit_date=date(2026, 7, 4),
            temperature_celsius=22,
            crowd_level="low",
            must_see=["panda_nursery", "science_hall"],
        )
    )

    assert result.status is SkillStatus.OK
    assert result.data["replanned"] is False
    assert result.data["risk"]["data"]["risk_level"] == "low"
    assert result.data["weather"]["source"] == "provided_synthetic"
    assert result.data["initial_itinerary"] == result.data["final_itinerary"]


def test_live_weather_drives_the_existing_high_heat_replan_without_becoming_a_skill():
    result = run_demo(
        DemoRequest(
            visit_date=date.today(),
            weather_mode="live_current",
            crowd_level="high",
            must_see=["panda_nursery", "bamboo_grove"],
        ),
        weather_fetcher=lambda: _live_snapshot(),
    )

    final_nodes = [step["node_id"] for step in result.data["final_itinerary"]["data"]["itinerary"]]
    assert result.status is SkillStatus.OK
    assert result.data["weather"]["source"] == "open_meteo"
    assert result.data["weather"]["apparent_temperature_celsius"] == 36
    assert result.data["replanned"] is True
    assert "bamboo_grove" not in final_nodes
    assert result.data["review"]["data"]["total_calls"] == 4


def test_live_weather_failure_completes_with_fixed_safe_fallback_and_degraded_status():
    def unavailable() -> WeatherSnapshot:
        raise OpenMeteoError("private dependency detail")

    result = run_demo(
        DemoRequest(
            visit_date=date.today(),
            weather_mode="live_current",
            crowd_level="high",
            must_see=["panda_nursery", "bamboo_grove"],
        ),
        weather_fetcher=unavailable,
    )

    final_nodes = [step["node_id"] for step in result.data["final_itinerary"]["data"]["itinerary"]]
    assert result.status is SkillStatus.DEGRADED
    assert result.data["weather"]["source"] == "fixed_fallback"
    assert result.data["weather"]["temperature_celsius"] == 33
    assert result.data["replanned"] is True
    assert "bamboo_grove" not in final_nodes
    assert "private dependency detail" not in " ".join(result.warnings)


def test_high_heat_replans_and_removes_the_outdoor_node():
    result = run_demo(
        DemoRequest(
            visit_date=date(2026, 7, 4),
            temperature_celsius=33,
            crowd_level="high",
            must_see=["panda_nursery", "bamboo_grove"],
        )
    )

    initial_nodes = [step["node_id"] for step in result.data["initial_itinerary"]["data"]["itinerary"]]
    final_nodes = [step["node_id"] for step in result.data["final_itinerary"]["data"]["itinerary"]]
    assert result.status is SkillStatus.OK
    assert "bamboo_grove" in initial_nodes
    assert result.data["replanned"] is True
    assert "bamboo_grove" not in final_nodes
    assert result.data["risk"]["data"]["replan_required"] is True


def test_urgent_incident_stops_before_any_ordinary_planning_and_is_reviewed():
    def unexpected_weather() -> WeatherSnapshot:
        raise AssertionError("urgent incidents must stop before weather resolution")

    result = run_demo(
        DemoRequest(
            visit_date=date.today(), weather_mode="live_current", crowd_level="low",
            incident=IncidentRequest(description="儿童走失"),
        ),
        weather_fetcher=unexpected_weather,
    )
    assert result.status is SkillStatus.ESCALATED
    assert result.data["stopped_after"] == "incident-triage-dispatch"
    assert "final_itinerary" not in result.data
    assert result.data["review"]["data"]["total_calls"] == 1
    assert result.data["review"]["data"]["event_counts"] == {"missing_person": 1}
    assert len(result.data["execution_records"]) == 1
    assert "Continue with the final itinerary" not in str(result.next_actions)


def test_six_skills_are_represented_with_a_review_of_actual_calls():
    result = run_demo(DemoRequest(
        visit_date=date(2026, 7, 4), temperature_celsius=26, crowd_level="low",
        incident=IncidentRequest(description="手机遗失", area="north_gate", is_ongoing=False),
        knowledge=KnowledgeRequest(question="大熊猫主要吃什么？", language="zh"),
    ))
    assert result.status is SkillStatus.OK
    review = result.data["review"]
    assert review["skill"] == "operations-review"
    assert review["data"]["total_calls"] == 5
    assert set(review["data"]["skill_counts"]) == {
        "visitor-policy-check", "accessible-itinerary-planner", "welfare-risk-dispatcher",
        "incident-triage-dispatch", "panda-knowledge-guard",
    }
    assert "竹" in result.data["knowledge"]["data"]["answer"]
    assert review["data"]["skill_counts"]["accessible-itinerary-planner"] == 1
    assert all("description" not in row and "data" not in row for row in result.data["execution_records"])


def test_replanning_counts_two_executions_with_distinct_ids():
    result = run_demo(DemoRequest(
        visit_date=date(2026, 7, 4), temperature_celsius=33, crowd_level="high",
        must_see=["panda_nursery", "bamboo_grove"],
    ))
    data = result.data["review"]["data"]
    assert data["total_calls"] == 4
    assert data["skill_counts"]["accessible-itinerary-planner"] == 2
    assert len(set(data["record_ids"])) == 4


def test_failed_route_preserves_policy_evidence_and_stop_status():
    result = run_demo(DemoRequest(
        visit_date=date(2026, 7, 4), temperature_celsius=26, crowd_level="low",
        must_see=["unknown_node"],
    ))
    assert result.status is SkillStatus.REJECTED
    assert result.data["review"]["data"]["total_calls"] == 2
    assert result.data["review"]["data"]["status_counts"] == {"ok": 1, "rejected": 1}


def test_unsupported_knowledge_stops_and_is_not_reported_as_success():
    result = run_demo(DemoRequest(
        visit_date=date(2026, 7, 4), temperature_celsius=26, crowd_level="low",
        knowledge=KnowledgeRequest(question="某只熊猫现在在哪里？", language="zh"),
    ))
    assert result.status is SkillStatus.NEEDS_INPUT
    assert result.data["stopped_after"] == "panda-knowledge-guard"
    assert result.data["review"]["data"]["total_calls"] == 4


def test_danger_in_measures_blocks_itinerary_and_survives_review_failure(monkeypatch):
    from pandaflow.skills.operations_review import service
    def unavailable(_):
        raise OSError("offline")
    monkeypatch.setattr(service, "load_json_resource", unavailable)
    result = run_demo(DemoRequest(
        visit_date=date(2026, 7, 4), temperature_celsius=26, crowd_level="low",
        incident=IncidentRequest(description="手机遗失", measures_taken=["老人昏迷，已找工作人员"]),
    ))
    assert result.status is SkillStatus.ESCALATED
    assert "final_itinerary" not in result.data
    assert result.data["response"]["data"]["priority"] == "P0"
    assert result.data["review"]["status"] == "degraded"
    assert len(result.data["execution_records"]) == 1
