import asyncio

import httpx

from pandaflow.api.app import app


def test_demo_endpoint_returns_a_high_heat_replanned_route():
    async def post_demo() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/api/v1/demo/run",
                json={
                    "visit_date": "2026-07-04",
                    "temperature_celsius": 33,
                    "crowd_level": "high",
                    "must_see": ["panda_nursery", "bamboo_grove"],
                },
            )

    response = asyncio.run(post_demo())

    assert response.status_code == 200
    assert response.json()["data"]["replanned"] is True
    assert response.json()["data"]["weather"]["source"] == "provided_synthetic"
