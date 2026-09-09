from pandaflow.shared.contracts import SkillStatus
from pandaflow.skills.accessible_itinerary_planner.schemas import ItineraryRequest
from pandaflow.skills.accessible_itinerary_planner.service import plan_itinerary


def test_step_free_family_route_has_a_rest_stop_and_stays_within_time_budget():
    result = plan_itinerary(
        ItineraryRequest(
            entry_node="north_gate",
            available_minutes=120,
            must_see=["panda_nursery", "science_hall"],
            mobility_need="step_free",
        )
    )

    visited_nodes = [step["node_id"] for step in result.data["itinerary"]]
    assert result.status is SkillStatus.OK
    assert result.data["total_minutes"] <= 120
    assert "science_hall" in result.data["rest_stops"]
    assert "hillside_trail" not in visited_nodes
    assert result.demo_data is True


def test_closed_preferred_node_is_omitted_without_violating_accessibility():
    result = plan_itinerary(
        ItineraryRequest(
            entry_node="north_gate",
            available_minutes=120,
            must_see=["panda_nursery", "bamboo_grove"],
            mobility_need="step_free",
            closed_nodes=["bamboo_grove"],
        )
    )

    visited_nodes = [step["node_id"] for step in result.data["itinerary"]]
    assert result.status is SkillStatus.OK
    assert "bamboo_grove" not in visited_nodes
    assert result.data["omitted_preferences"] == ["bamboo_grove"]


def test_no_safe_path_is_rejected_instead_of_returning_a_fabricated_route():
    result = plan_itinerary(
        ItineraryRequest(
            entry_node="north_gate",
            available_minutes=120,
            must_see=["panda_nursery"],
            mobility_need="step_free",
            closed_nodes=["panda_nursery", "science_hall"],
        )
    )

    assert result.status is SkillStatus.REJECTED
    assert result.data["itinerary"] == []
