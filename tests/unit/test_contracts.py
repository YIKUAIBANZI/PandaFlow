from pandaflow.shared.contracts import SkillResponse, SkillStatus


def test_response_contains_a_generated_request_id_and_required_fields():
    response = SkillResponse.create(
        skill="visitor-policy-check",
        status=SkillStatus.OK,
        data={"eligible": True},
        source_refs=["source_ticket_service"],
        rule_refs=["rule_reservation_required"],
        demo_data=True,
    )

    assert response.status is SkillStatus.OK
    assert response.request_id.startswith("req_")
    assert response.source_refs == ["source_ticket_service"]
    assert response.rule_refs == ["rule_reservation_required"]
    assert response.demo_data is True
