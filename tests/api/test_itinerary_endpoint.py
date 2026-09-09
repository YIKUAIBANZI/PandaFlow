import asyncio

import httpx

from pandaflow.api.app import app


def test_itinerary_endpoint_returns_a_route_envelope():
    async def post_route() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/api/v1/skills/accessible-itinerary-planner",
                json={
                    "entry_node": "north_gate",
                    "available_minutes": 120,
                    "must_see": ["panda_nursery", "science_hall"],
                    "mobility_need": "step_free",
                },
            )

    response = asyncio.run(post_route())

    assert response.status_code == 200
    assert response.json()["skill"] == "accessible-itinerary-planner"
    assert response.json()["status"] == "ok"
