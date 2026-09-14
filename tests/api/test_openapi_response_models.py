import asyncio

import httpx

from pandaflow.api.app import app


EXPECTED_RESPONSES = {
    "/api/v1/skills/visitor-policy-check": "VisitorPolicyResponse",
    "/api/v1/skills/accessible-itinerary-planner": "ItineraryResponse",
    "/api/v1/skills/panda-knowledge-guard": "KnowledgeResponse",
    "/api/v1/skills/welfare-risk-dispatcher": "RiskDispatchResponse",
    "/api/v1/skills/incident-triage-dispatch": "IncidentResponse",
    "/api/v1/skills/operations-review": "OperationsReviewResponse",
    "/api/v1/demo/run": "DemoResponse",
}

EXPECTED_DATA_FIELDS = {
    "VisitorPolicyData": {"eligible", "missing_fields", "reason", "visit_date", "entry_slot"},
    "ItineraryData": {
        "itinerary", "total_minutes", "rest_stops", "omitted_preferences",
        "fulfilled_preferences",
    },
    "KnowledgeData": {"answer"},
    "RiskDispatchData": {
        "risk_level", "replan_required", "avoid_nodes", "active_avoid_nodes",
        "reasons", "weather",
    },
    "IncidentData": {
        "category", "priority", "responsible_role", "immediate_actions",
        "prohibited_actions", "reply_template", "dispatch_status", "sent",
        "missing_fields", "rule_version", "safety_signals",
    },
    "OperationsReviewData": {
        "total_calls", "sample_size", "status_counts", "skill_counts",
        "degraded_count", "rule_hit_counts", "event_counts", "observations",
        "rule_update_candidates", "record_ids", "causal_claims", "rule_version",
    },
    "DemoData": {
        "weather", "policy", "initial_itinerary", "risk", "final_itinerary",
        "incident", "knowledge", "replanned", "stopped_after", "response",
        "violating_nodes", "execution_records", "review",
    },
}


def test_each_post_endpoint_exposes_a_specific_response_component():
    schema = app.openapi()

    for path, response_name in EXPECTED_RESPONSES.items():
        response_schema = schema["paths"][path]["post"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        assert response_schema == {"$ref": f"#/components/schemas/{response_name}"}


def test_openapi_names_concrete_data_fields_instead_of_arbitrary_objects():
    schemas = app.openapi()["components"]["schemas"]

    for name, expected_fields in EXPECTED_DATA_FIELDS.items():
        data_schema = schemas[name]
        assert set(data_schema["properties"]) == expected_fields
        assert data_schema.get("additionalProperties") is False


def test_typed_response_validation_does_not_add_fields_to_the_wire_contract():
    async def request_bodies() -> tuple[dict, dict]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            policy_response = await client.post(
                "/api/v1/skills/visitor-policy-check",
                json={
                    "visit_date": "2026-09-20",
                    "entry_slot": "morning",
                    "reservation_status": "confirmed",
                    "document_type": "passport",
                },
            )
            knowledge_response = await client.post(
                "/api/v1/skills/panda-knowledge-guard",
                json={"question": "大熊猫主要吃什么？", "language": "zh"},
            )
            return policy_response.json(), knowledge_response.json()

    policy, knowledge = asyncio.run(request_bodies())

    assert set(policy["data"]) == {"eligible", "visit_date", "entry_slot"}
    assert set(knowledge["data"]) == {"answer"}
