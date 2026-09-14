"""Smoke-test the authorized public demo without sending personal data."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx


def verify(base_url: str) -> dict:
    assert base_url.startswith("https://"), "Use a TLS-verified HTTPS endpoint"
    results = {"base_url": base_url, "verified_at": datetime.now(timezone.utc).isoformat(), "checks": []}
    with httpx.Client(base_url=base_url, timeout=40, follow_redirects=False) as client:
        for path in ("/ready", "/health", "/demo", "/openapi.json"):
            r = client.get(path)
            assert r.status_code == 200, (path, r.status_code)
            if path == "/ready":
                assert r.json() == {"status": "ready"}
            results["checks"].append({"path": path, "http_status": r.status_code})
        root = client.get("/")
        assert root.status_code == 302 and root.headers["location"] == "/demo"
        for name, status, semantic in (("normal", 200, "ok"), ("missing-entry-slot", 200, "needs_input"), ("invalid-entry-slot", 422, None)):
            request = json.loads((Path(__file__).resolve().parents[1] / "docs/workhub-smoke" / f"{name}.request.json").read_text())
            request["visit_date"] = datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
            r = client.post("/api/v1/skills/visitor-policy-check", json=request)
            body = r.json()
            assert r.status_code == status
            if semantic:
                assert body["status"] == semantic and body["demo_data"] is True
                assert body["source_refs"] and body["rule_refs"]
                assert body["data"]["eligible"] is (True if semantic == "ok" else None)
            else:
                assert "overnight" not in r.text
            results["checks"].append({"case": name, "http_status": r.status_code, "status": body.get("status")})
        catalog = client.get("/api/v1/demo/scenarios").json()
        assert len(catalog["scenarios"]) == 4
        for scenario in catalog["scenarios"]:
            r = client.post("/api/v1/demo/run", json=scenario["request"])
            assert r.status_code == 200
            body = r.json()
            data = body["data"]
            sid = scenario["id"]
            if sid == "human_escalation":
                assert body["status"] == "escalated" and "final_itinerary" not in data
            elif sid == "heat_replan":
                assert body["status"] == "ok" and data["replanned"] is True
                route = {s["node_id"] for s in data["final_itinerary"]["data"]["itinerary"]}
                assert not route.intersection(data["risk"]["data"]["active_avoid_nodes"])
            elif sid == "normal_all_skills":
                assert body["status"] == "ok"
            else:
                assert body["status"] in ("ok", "degraded")
            results["checks"].append({"scenario": sid, "http_status": r.status_code, "status": body["status"], "weather": data.get("weather")})
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.base_url.rstrip("/"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    for check in result["checks"]:
        print(check.get("scenario", check.get("case", check.get("path"))), check.get("status", check.get("http_status")))
