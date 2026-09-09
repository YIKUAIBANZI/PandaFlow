import asyncio

import httpx

from pandaflow.api.app import app


def test_welfare_risk_endpoint_returns_a_replan_instruction():
    async def post_risk() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/api/v1/skills/welfare-risk-dispatcher",
                json={
                    "temperature_celsius": 33,
                    "crowd_level": "high",
                    "route_nodes": ["north_gate", "panda_nursery", "bamboo_grove"],
                },
            )

    response = asyncio.run(post_risk())

    assert response.status_code == 200
    assert response.json()["skill"] == "welfare-risk-dispatcher"
    assert response.json()["data"]["replan_required"] is True
