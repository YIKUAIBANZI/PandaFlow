import asyncio

import httpx

from pandaflow.api.app import app


def test_knowledge_endpoint_returns_the_source_bound_answer():
    async def post_question() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/api/v1/skills/panda-knowledge-guard",
                json={"question": "大熊猫主要吃什么？", "language": "zh"},
            )

    response = asyncio.run(post_question())
    assert response.status_code == 200
    assert response.json()["skill"] == "panda-knowledge-guard"
    assert "竹" in response.json()["data"]["answer"]
    assert response.json()["source_refs"] == ["source_panda_base_diet"]


def test_knowledge_endpoint_supports_an_english_diet_question():
    async def post_question() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/api/v1/skills/panda-knowledge-guard",
                json={"question": "What do giant pandas eat?", "language": "en"},
            )

    response = asyncio.run(post_question())

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "bamboo" in response.json()["data"]["answer"].lower()
