import asyncio

import httpx

from pandaflow.api import app as app_module
from pandaflow.api.app import app


def get(path: str, *, raise_app_exceptions: bool = True) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(
            app=app,
            raise_app_exceptions=raise_app_exceptions,
        )
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.get(path)

    return asyncio.run(request())


def post(path: str, payload: dict, *, raise_app_exceptions: bool = True) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(
            app=app,
            raise_app_exceptions=raise_app_exceptions,
        )
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.post(path, json=payload)

    return asyncio.run(request())


def test_liveness_and_resource_readiness_are_distinct():
    health = get("/health")
    ready = get("/ready")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready"}


def test_readiness_masks_resource_failure_and_keeps_liveness_available(monkeypatch):
    def unavailable(_filename: str):
        raise OSError("/private/path/rules.json")

    monkeypatch.setattr(app_module, "load_json_resource", unavailable)

    ready = get("/ready", raise_app_exceptions=False)
    health = get("/health")

    assert ready.status_code == 503
    assert ready.json() == {"detail": "运行资源暂时不可用。"}
    assert "/private/path" not in ready.text
    assert health.status_code == 200


def test_skill_resource_failure_returns_a_stable_safe_http_error(monkeypatch):
    from pandaflow.skills.accessible_itinerary_planner import service

    def unavailable(_filename: str):
        raise OSError("/private/path/park_graph.json")

    monkeypatch.setattr(service, "load_json_resource", unavailable)
    response = post(
        "/api/v1/skills/accessible-itinerary-planner",
        {
            "entry_node": "north_gate",
            "available_minutes": 120,
            "must_see": ["panda_nursery"],
        },
        raise_app_exceptions=False,
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "运行资源暂时不可用。"}
    assert "/private/path" not in response.text


def test_non_resource_value_error_is_not_mislabeled_as_resource_unavailable(monkeypatch):
    def broken_planner(_request):
        raise ValueError("programming defect")

    monkeypatch.setattr(app_module, "plan_itinerary", broken_planner)
    response = post(
        "/api/v1/skills/accessible-itinerary-planner",
        {
            "entry_node": "north_gate",
            "available_minutes": 120,
            "must_see": ["panda_nursery"],
        },
        raise_app_exceptions=False,
    )

    assert response.status_code == 500
    assert response.text == "Internal Server Error"
    assert "运行资源暂时不可用" not in response.text
