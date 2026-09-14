from datetime import date

import pytest
from pydantic import ValidationError

from pandaflow.shared.contracts import SkillStatus
from pandaflow.skills.visitor_policy_check.schemas import VisitorPolicyRequest
from pandaflow.skills.visitor_policy_check.service import evaluate_policy


def test_missing_visit_date_requests_required_information():
    result = evaluate_policy(VisitorPolicyRequest(reservation_status="confirmed"))

    assert result.status is SkillStatus.NEEDS_INPUT
    assert result.data["missing_fields"] == ["visit_date"]
    assert result.data["eligible"] is None


def test_unconfirmed_reservation_does_not_promise_entry():
    result = evaluate_policy(
        VisitorPolicyRequest(
            visit_date=date(2026, 7, 4),
            entry_slot="morning",
            reservation_status="missing",
        )
    )

    assert result.status is SkillStatus.NEEDS_INPUT
    assert result.data["eligible"] is False
    assert "booking" in result.next_actions[0].lower()


def test_missing_entry_slot_does_not_return_an_executable_policy_result():
    result = evaluate_policy(
        VisitorPolicyRequest(
            visit_date=date(2026, 7, 4),
            reservation_status="confirmed",
            document_type="passport",
        )
    )

    assert result.status is SkillStatus.NEEDS_INPUT
    assert result.data == {"eligible": None, "missing_fields": ["entry_slot"]}
    assert result.next_actions == ["Provide the intended entry slot."]


def test_unknown_document_type_is_escalated_for_human_verification():
    result = evaluate_policy(
        VisitorPolicyRequest(
            visit_date=date(2026, 7, 4),
            entry_slot="morning",
            reservation_status="confirmed",
            document_type="other",
        )
    )

    assert result.status is SkillStatus.ESCALATED
    assert result.data["eligible"] is None
    assert result.next_actions == ["Ask staff to verify the accepted document type."]


def test_confirmed_conditions_return_a_traceable_previsit_reminder():
    result = evaluate_policy(
        VisitorPolicyRequest(
            visit_date=date(2026, 7, 4),
            entry_slot="morning",
            reservation_status="confirmed",
            document_type="passport",
        )
    )

    assert result.status is SkillStatus.OK
    assert result.data["eligible"] is True
    assert result.source_refs == ["source_base_visitor_service"]
    assert result.rule_refs == ["rule_reservation_required", "rule_document_check"]
    assert result.demo_data is True
    assert "does not guarantee admission" in result.warnings[0].lower()


def test_request_rejects_unmodelled_personal_identifier_field():
    with pytest.raises(ValidationError):
        VisitorPolicyRequest.model_validate(
            {"visit_date": "2026-07-04", "id_number": "510000199001011234"}
        )
