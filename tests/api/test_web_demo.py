import asyncio
from datetime import date

import httpx

from pandaflow.api import app as app_module
from pandaflow.api.app import app
from pandaflow.api.demo_scenarios import load_demo_scenarios


def request(
    method: str,
    path: str,
    *,
    raise_app_exceptions: bool = True,
) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(
            app=app,
            raise_app_exceptions=raise_app_exceptions,
        )
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path)

    return asyncio.run(send())


def test_demo_page_and_assets_are_served_by_fastapi():
    page = request("GET", "/demo")
    css = request("GET", "/demo/assets/styles.css")
    script = request("GET", "/demo/assets/app.js")

    assert page.status_code == css.status_code == script.status_code == 200
    assert "PandaFlow" in page.text
    assert page.headers["content-type"].startswith("text/html")


def test_scenario_catalog_contains_four_safe_presets_and_normalizes_live_date():
    catalog = load_demo_scenarios(current_date=date(2026, 9, 9))

    assert catalog["classification"] == "demo"
    assert catalog["demo_data"] is True
    assert len(catalog["scenarios"]) == 4
    live = next(
        item for item in catalog["scenarios"] if item["id"] == "live_current_weather"
    )
    assert live["request"]["visit_date"] == "2026-09-09"
    assert all(
        "name" not in item["request"] and "phone" not in item["request"]
        for item in catalog["scenarios"]
    )


def test_scenario_endpoint_returns_public_catalog():
    response = request("GET", "/api/v1/demo/scenarios")

    assert response.status_code == 200
    body = response.json()
    assert {row["id"] for row in body["scenarios"]} == {
        "normal_all_skills",
        "heat_replan",
        "human_escalation",
        "live_current_weather",
    }


def test_scenario_endpoint_masks_resource_failures(monkeypatch):
    def unavailable():
        raise OSError("/private/path/demo_scenarios.json")

    monkeypatch.setattr(app_module, "load_demo_scenarios", unavailable)
    response = request(
        "GET",
        "/api/v1/demo/scenarios",
        raise_app_exceptions=False,
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "演示场景暂时不可用。"}
    assert "/private/path" not in response.text


def test_demo_page_has_accessible_regions_and_truthfulness_labels():
    html = request("GET", "/demo").text

    assert 'rel="icon"' in html
    assert 'href="data:image/svg+xml,' in html
    assert 'id="scenario-list"' in html
    assert 'id="run-scenario"' in html
    assert 'aria-live="polite"' in html
    assert 'id="decision-result"' in html
    assert 'id="execution-evidence"' in html
    assert "Demo Data" in html
    assert "No Real Dispatch" in html
    assert 'id="scope-note"' in html
    assert 'id="initial-route-summary"' in html
    assert 'id="final-route-summary"' in html
    assert 'id="incident-actions"' in html


def test_browser_code_avoids_unsafe_html_and_storage():
    script = request("GET", "/demo/assets/app.js").text

    assert "innerHTML" not in script
    assert "localStorage" not in script
    assert "sessionStorage" not in script
    assert 'fetch("/api/v1/demo/scenarios")' in script
    assert 'fetch("/api/v1/demo/run"' in script


def test_stylesheet_has_responsive_accessible_status_system():
    css = request("GET", "/demo/assets/styles.css").text

    assert "--color-bamboo" in css
    assert "grid-template-columns" in css
    assert '[data-tone="escalated"]' in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "@media (max-width:" in css
    assert ":focus-visible" in css
