import asyncio

import httpx

from pandaflow.api.app import app


def test_policy_endpoint_returns_business_status_inside_response_envelope():
    async def call_endpoint() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/api/v1/skills/visitor-policy-check",
                json={
                    "visit_date": "2026-07-04",
                    "entry_slot": "morning",
                    "reservation_status": "missing",
                },
            )

    response = asyncio.run(call_endpoint())

    assert response.status_code == 200
    assert response.json()["status"] == "needs_input"
    assert response.json()["skill"] == "visitor-policy-check"
