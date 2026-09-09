# Welfare Risk Dispatcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a deterministic risk Skill that turns demo weather, crowd, closed-area and route context into a traceable risk decision and a safe replan instruction.

**Architecture:** A pure service evaluates a typed weather snapshot against versioned demo welfare rules. Its output names risk level, reasons, traveller reminders, `replan_required`, and nodes to avoid; it does not infer the health or position of an individual animal and does not claim a real closure action occurred.

**Tech Stack:** Python 3.11+, Pydantic 2, FastAPI, pytest, JSON resources.

**Spec:** `docs/superpowers/specs/2026-09-04-pandaflow-design.md`

## Global Constraints

- Safety and animal welfare override a visitor's route preference.
- All thresholds and area state are explicit demo data until public sources are re-verified.
- The local rule engine remains deterministic and network-free; Open-Meteo fetching is a separate adapter milestone.
- The Skill can request re-planning but cannot claim to have notified staff, changed an operating state, or diagnosed an animal.

---

### Task 1: Create the Pure High-Heat Replanning Rule

**Files:**
- Create: `resources/welfare_rules.json`
- Modify: `resources/source_registry.json`
- Create: `src/pandaflow/skills/welfare_risk_dispatcher/__init__.py`
- Create: `src/pandaflow/skills/welfare_risk_dispatcher/schemas.py`
- Create: `src/pandaflow/skills/welfare_risk_dispatcher/service.py`
- Create: `tests/unit/test_welfare_risk_dispatcher.py`

**Interfaces:**
- Produces: `RiskDispatchRequest(temperature_celsius: float, crowd_level: Literal["low", "medium", "high"], route_nodes: list[str], closed_nodes: list[str])` and `dispatch_risk(request) -> SkillResponse`.
- High heat at or above the resource threshold returns `data.risk_level="high"`, `data.replan_required=true`, and includes outdoor route nodes in `data.avoid_nodes`.

- [ ] Write a failing test for a 33°C route through `bamboo_grove`; assert high risk, replan true, the grove in `avoid_nodes`, and `demo_data=true`.
- [ ] Run `.venv/bin/python -m pytest tests/unit/test_welfare_risk_dispatcher.py -v`; expect a missing module error.
- [ ] Add the smallest resource-backed service to pass that test, with a provenance reference and reminder that conditions are demo data.
- [ ] Re-run the same command; expect PASS.

### Task 2: Make Closures and Normal Conditions Explicit

**Files:**
- Modify: `src/pandaflow/skills/welfare_risk_dispatcher/service.py`
- Modify: `tests/unit/test_welfare_risk_dispatcher.py`

- [ ] Add a failing closure test: `closed_nodes=["bamboo_grove"]` must request a replan even at 22°C and list the closed node as an avoidance target.
- [ ] Verify RED, implement the closure rule, then verify GREEN.
- [ ] Add a normal-condition test: 22°C, low crowd, no closures yields low risk and no replan.
- [ ] Verify RED, implement the low-risk path, then verify GREEN.

### Task 3: Expose and Document the Skill

**Files:**
- Modify: `src/pandaflow/api/app.py`
- Create: `tests/api/test_welfare_risk_endpoint.py`
- Create: `skills/welfare-risk-dispatcher/SKILL.md`
- Modify: `README.md`

- [ ] Write an HTTP test using `httpx.ASGITransport`; valid high-heat input returns HTTP 200, Skill name `welfare-risk-dispatcher`, and `replan_required=true`.
- [ ] Verify RED with 404, add `POST /api/v1/skills/welfare-risk-dispatcher`, then verify GREEN.
- [ ] Document synthetic thresholds, no diagnosis/notification claim, route replanning handoff and future Open-Meteo adapter boundary.
- [ ] Run `.venv/bin/python -m pytest -v` and `.venv/bin/python -m compileall -q src`; both must complete successfully.
