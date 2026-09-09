"""Deterministic pre-visit policy evaluation; this module never books a visit."""

from typing import Any

from pandaflow.shared.contracts import SkillResponse, SkillStatus
from pandaflow.shared.rules import load_json_resource
from pandaflow.skills.visitor_policy_check.schemas import VisitorPolicyRequest


SKILL_NAME = "visitor-policy-check"
DEMO_WARNING = "This prototype uses demo rules and does not guarantee admission."


def _response(
    *,
    status: SkillStatus,
    data: dict[str, Any],
    rule_refs: list[str],
    next_actions: list[str],
) -> SkillResponse:
    rules = load_json_resource("visitor_rules.json")
    return SkillResponse.create(
        skill=SKILL_NAME,
        status=status,
        data=data,
        source_refs=rules["source_refs"],
        rule_refs=rule_refs,
        warnings=[DEMO_WARNING],
        next_actions=next_actions,
        demo_data=rules["classification"] == "demo",
    )


def evaluate_policy(request: VisitorPolicyRequest) -> SkillResponse:
    """Assess a pre-visit request without claiming a booking or entry result."""

    rules = load_json_resource("visitor_rules.json")
    reservation_rule = rules["rules"]["reservation"]
    document_rule = rules["rules"]["document"]

    if request.visit_date is None:
        return _response(
            status=SkillStatus.NEEDS_INPUT,
            data={"eligible": None, "missing_fields": ["visit_date"]},
            rule_refs=[reservation_rule],
            next_actions=["Provide the intended visit date."],
        )

    if request.reservation_status != "confirmed":
        action = (
            "Complete or confirm the booking before visiting."
            if request.reservation_status == "missing"
            else "Confirm the reservation status before visiting."
        )
        return _response(
            status=SkillStatus.NEEDS_INPUT,
            data={"eligible": False, "missing_fields": ["reservation_status"]},
            rule_refs=[reservation_rule],
            next_actions=[action],
        )

    if request.document_type not in {None, *rules["known_document_types"]}:
        return _response(
            status=SkillStatus.ESCALATED,
            data={"eligible": None, "reason": "Unknown document type."},
            rule_refs=[document_rule],
            next_actions=["Ask staff to verify the accepted document type."],
        )

    if request.document_type is None:
        return _response(
            status=SkillStatus.NEEDS_INPUT,
            data={"eligible": None, "missing_fields": ["document_type"]},
            rule_refs=[document_rule],
            next_actions=["Provide a document type without submitting its number."],
        )

    return _response(
        status=SkillStatus.OK,
        data={
            "eligible": True,
            "visit_date": request.visit_date.isoformat(),
            "entry_slot": request.entry_slot,
        },
        rule_refs=[reservation_rule, document_rule],
        next_actions=["Bring the selected document and follow on-site guidance."],
    )
