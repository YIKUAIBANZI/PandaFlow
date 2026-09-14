import asyncio

import httpx
import pytest

from pandaflow.api.app import app


def post_incident(payload):
    async def post():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.post("/api/v1/skills/incident-triage-dispatch", json=payload)
    return asyncio.run(post())


@pytest.mark.parametrize("description,category,priority,status", [
    ("老人身体不适", "medical", "P1", "escalated"),
    ("儿童走失", "missing_person", "P1", "escalated"),
    ("手机遗失", "lost_property", "P2", "ok"),
    ("预约票务问题", "ticketing", "P2", "ok"),
    ("游客插队争吵", "order", "P2", "ok"),
    ("无障碍电梯故障", "facility", "P2", "ok"),
    ("visitor unconscious", "medical", "P0", "escalated"),
    ("missing child", "missing_person", "P1", "escalated"),
])
def test_classifies_and_produces_only_an_unsent_draft(description, category, priority, status):
    response = post_incident({"description": description, "area": "north_gate", "is_ongoing": True})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == status
    assert body["data"]["category"] == category
    assert body["data"]["priority"] == priority
    assert body["data"]["sent"] is False
    assert body["data"]["dispatch_status"] == "draft"
    assert body["data"]["responsible_role"]
    assert body["data"]["immediate_actions"] and body["data"]["prohibited_actions"]
    assert body["data"]["reply_template"]
    assert body["demo_data"] and body["source_refs"] and body["rule_refs"]


def test_danger_overrides_low_risk_hint_missing_area_and_claimed_resolution():
    body = post_incident({
        "description": "手机遗失，同时老人昏迷", "category_hint": "lost_property",
        "is_ongoing": False, "measures_taken": ["已处理"],
    }).json()
    assert body["status"] == "escalated"
    assert body["data"]["priority"] == "P0"
    assert body["data"]["category"] == "medical"
    assert "area" in body["data"]["missing_fields"]


@pytest.mark.parametrize(
    ("description", "category", "priority"),
    [
        ("有人晕倒了，顺便问一下门票怎么退", "medical", "P1"),
        ("孩子找不到了，想问门票退款", "missing_person", "P1"),
        ("a visitor collapsed and needs a refund", "medical", "P1"),
        ("my child cannot be found; I also need a ticket refund", "missing_person", "P1"),
    ],
)
def test_mixed_safety_and_ticketing_intents_always_escalate(
    description, category, priority
):
    body = post_incident(
        {"description": description, "area": "north_gate", "is_ongoing": True}
    ).json()

    assert body["status"] == "escalated"
    assert body["data"]["category"] == category
    assert body["data"]["priority"] == priority
    assert body["data"]["safety_signals"]


def test_routine_ticketing_has_no_safety_signal():
    body = post_incident(
        {"description": "请问门票怎么退款", "area": "north_gate", "is_ongoing": False}
    ).json()

    assert body["status"] == "ok"
    assert body["data"]["category"] == "ticketing"
    assert body["data"]["safety_signals"] == []


@pytest.mark.parametrize("payload", [{}, {"description": "请问一下"}])
def test_insufficient_input_requests_details_without_inventing_category(payload):
    response = post_incident(payload)
    assert response.status_code == 200
    assert response.json()["status"] == "needs_input"
    assert response.json()["data"]["category"] == "unknown"


def test_uncertain_danger_escalates_instead_of_waiting_for_more_information():
    body = post_incident({"description": "救命，出事了"}).json()
    assert body["status"] == "escalated"
    assert body["data"]["priority"] == "P1"
    assert body["data"]["missing_fields"]


def test_inactive_routine_request_has_low_priority_and_does_not_echo_text():
    body = post_incident({"description": "手机遗失 联系13812345678", "is_ongoing": False}).json()
    assert body["data"]["priority"] == "P3"
    assert "13812345678" not in str(body)


@pytest.mark.parametrize("payload", [{"phone": "13812345678"}, {"description": "a" * 2001}])
def test_rejects_unknown_fields_and_overlong_input(payload):
    response = post_incident(payload)
    assert response.status_code == 422
    assert "13812345678" not in response.text
    assert "a" * 2001 not in response.text


@pytest.mark.parametrize("field,value", [
    ("measures_taken", ["老人昏迷，已找工作人员"]),
    ("area", "北门，有人昏迷"),
])
def test_high_risk_evidence_in_other_free_text_fields_overrides_routine_description(field, value):
    payload = {"description": "手机遗失", "area": "north_gate", "is_ongoing": True}
    payload[field] = value
    body = post_incident(payload).json()
    assert body["status"] == "escalated"
    assert body["data"]["priority"] == "P0"
    assert body["data"]["category"] == "medical"


def test_rules_unavailable_fails_closed_without_claiming_a_rule_hit(monkeypatch):
    from pandaflow.skills.incident_triage_dispatch import service
    def unavailable(_):
        raise OSError("private path")
    monkeypatch.setattr(service, "load_json_resource", unavailable)
    body = post_incident({"description": "儿童走失"}).json()
    assert body["status"] == "escalated"
    assert body["data"]["sent"] is False
    assert body["rule_refs"] == []
    assert "private path" not in str(body)
