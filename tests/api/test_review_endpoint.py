import asyncio

import httpx
import pytest

from pandaflow.api.app import app


def post_review(records, **extra):
    async def post():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.post("/api/v1/skills/operations-review", json={"records": records, **extra})
    return asyncio.run(post())


def records():
    return [
        {"record_id": "req_one", "skill": "visitor-policy-check", "status": "ok", "rule_refs": ["demo_entry", "demo_entry"], "demo_data": True},
        {"record_id": "req_two", "skill": "welfare-risk-dispatcher", "status": "degraded", "rule_refs": ["demo_heat"], "demo_data": True},
        {"record_id": "req_three", "skill": "incident-triage-dispatch", "status": "escalated", "rule_refs": ["demo_heat"], "demo_data": True, "incident_category": "medical", "priority": "P1"},
    ]


def test_aggregates_actual_calls_and_every_observation_has_evidence():
    response = post_review(records())
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    data = body["data"]
    assert data["total_calls"] == 3
    assert data["degraded_count"] == 1
    assert data["status_counts"] == {"ok": 1, "degraded": 1, "escalated": 1}
    assert data["event_counts"] == {"medical": 1}
    assert data["rule_hit_counts"] == {"demo_entry": 1, "demo_heat": 2}
    assert data["skill_counts"]["incident-triage-dispatch"] == 1
    assert data["sample_size"] == 3 and data["causal_claims"] is False
    assert data["observations"]
    for observation in data["observations"] + data["rule_update_candidates"]:
        assert observation["record_ids"]
        assert set(observation["record_ids"]) <= {"req_one", "req_two", "req_three"}
    assert body["source_refs"] and body["rule_refs"] and body["demo_data"]


def test_empty_sample_returns_no_invented_findings():
    body = post_review([]).json()
    assert body["status"] == "needs_input"
    assert body["data"]["total_calls"] == 0
    assert body["data"]["observations"] == []


@pytest.mark.parametrize("extra", [{"phone": "13812345678"}, {"data": {"name": "张三"}}, {"description": "老人张三"}])
def test_private_or_unallowlisted_fields_reject_the_entire_batch_without_echo(extra):
    rows = records()
    rows[1].update(extra)
    response = post_review(rows)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["data"]["total_calls"] == 0
    assert "13812345678" not in str(body) and "张三" not in str(body)
    assert body["warnings"]


def test_duplicate_ids_are_rejected_instead_of_double_counting():
    rows = records()
    rows.append(rows[0])
    assert post_review(rows).json()["status"] == "rejected"


@pytest.mark.parametrize("changes", [
    {"status": "invented"}, {"skill": "unknown-skill"}, {"record_id": "张三 13812345678"},
    {"incident_category": "medical"},
])
def test_invalid_or_inconsistent_metadata_is_rejected(changes):
    rows = records()
    rows[0].update(changes)
    assert post_review(rows).json()["status"] == "rejected"


def test_unavailable_review_rules_returns_degraded_without_made_up_counts(monkeypatch):
    from pandaflow.skills.operations_review import service
    def unavailable(_):
        raise OSError("private path")
    monkeypatch.setattr(service, "load_json_resource", unavailable)
    body = post_review(records()).json()
    assert body["status"] == "degraded"
    assert body["data"]["total_calls"] == 0
    assert body["rule_refs"] == []


@pytest.mark.parametrize("rows,extra", [
    ([], {"phone": "13812345678"}),
    (["张三 13812345678"], {}),
    ([], {"张三13812345678": "private"}),
])
def test_outer_validation_errors_do_not_echo_private_values_or_field_names(rows, extra):
    response = post_review(rows, **extra)
    assert response.status_code == 422
    assert "13812345678" not in response.text
    assert "张三" not in response.text
