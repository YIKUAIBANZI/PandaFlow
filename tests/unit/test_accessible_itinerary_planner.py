from pandaflow.shared.contracts import SkillStatus
import pytest
from pydantic import ValidationError

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


def test_duplicate_preference_has_one_dwell_and_no_hidden_time():
    result = plan_itinerary(
        ItineraryRequest(
            entry_node="north_gate",
            available_minutes=120,
            must_see=["panda_nursery", "panda_nursery"],
            mobility_need="step_free",
        )
    )

    nursery_steps = [
        step for step in result.data["itinerary"]
        if step["node_id"] == "panda_nursery"
    ]
    assert result.status is SkillStatus.OK
    assert nursery_steps == [
        {
            "node_id": "panda_nursery",
            "arrival_after_minutes": 12,
            "dwell_minutes": 35,
        }
    ]
    assert result.data["total_minutes"] == 47
    assert result.data["fulfilled_preferences"] == ["panda_nursery"]


def test_entry_target_is_explicitly_counted_as_fulfilled():
    result = plan_itinerary(
        ItineraryRequest(
            entry_node="north_gate",
            available_minutes=120,
            must_see=["north_gate"],
            mobility_need="step_free",
        )
    )

    assert result.status is SkillStatus.OK
    assert result.data["itinerary"] == [
        {"node_id": "north_gate", "arrival_after_minutes": 0, "dwell_minutes": 0}
    ]
    assert result.data["total_minutes"] == 0
    assert result.data["fulfilled_preferences"] == ["north_gate"]


def test_transit_node_later_requested_gets_one_explicit_dwell():
    result = plan_itinerary(
        ItineraryRequest(
            entry_node="north_gate",
            available_minutes=120,
            must_see=["south_gate", "lake_pavilion"],
            mobility_need="step_free",
        )
    )

    lake_steps = [
        step for step in result.data["itinerary"]
        if step["node_id"] == "lake_pavilion"
    ]
    assert result.status is SkillStatus.OK
    assert sum(step["dwell_minutes"] > 0 for step in lake_steps) == 1
    assert result.data["fulfilled_preferences"] == ["south_gate", "lake_pavilion"]
    last_step = result.data["itinerary"][-1]
    assert result.data["total_minutes"] == (
        last_step["arrival_after_minutes"] + last_step["dwell_minutes"]
    )


@pytest.mark.parametrize(
    "payload",
    [
        {
            "entry_node": "north_gate",
            "available_minutes": 120,
            "must_see": ["panda_nursery"] * 21,
        },
        {
            "entry_node": "n" * 101,
            "available_minutes": 120,
            "must_see": ["panda_nursery"],
        },
    ],
)
def test_itinerary_input_has_bounded_node_lists_and_ids(payload):
    with pytest.raises(ValidationError):
        ItineraryRequest.model_validate(payload)
