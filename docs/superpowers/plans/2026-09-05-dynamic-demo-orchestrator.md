# Dynamic Demo Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce one end-to-end PandaFlow response that runs policy validation, creates an accessible itinerary, evaluates welfare risk, and automatically replans only when risk requires it.

**Architecture:** A thin service composes the existing three Skill functions and preserves their response envelopes as trace data. It treats `replan_required` as the only trigger for a second itinerary call, passing `avoid_nodes` as `closed_nodes`; it never changes an individual Skill's business rules.

**Tech Stack:** Python 3.11+, Pydantic 2, FastAPI, pytest.

**Spec:** `docs/superpowers/specs/2026-09-04-pandaflow-design.md`

## Constraints

- The orchestrator is not a seventh Skill.
- Stop before route planning if policy is not `ok`; never bypass `rejected` or `escalated`.
- Risk output must remain traceable, and a replan must exclude each risk-provided avoid node.
- Initial demo uses the fixed 120-minute, step-free family route and synthetic weather context.

### Task 1: Test and Implement Composition

- Create `src/pandaflow/orchestrator/service.py` and `tests/e2e/test_dynamic_demo.py`.
- Write a failing normal-weather test asserting one itinerary, no replan, and low risk.
- Write a failing high-heat test asserting `replanned=true`, original and final itinerary traces, and no `bamboo_grove` in the final route.
- Implement `run_demo(DemoRequest) -> SkillResponse` by calling policy, itinerary, risk, then optionally itinerary with `closed_nodes=risk.data["avoid_nodes"]`.
- Verify `.venv/bin/python -m pytest tests/e2e/test_dynamic_demo.py -v` is green.

### Task 2: HTTP Demo Endpoint and Full Regression

- Add `POST /api/v1/demo/run` and `tests/api/test_demo_endpoint.py` with an HTTP 200 high-heat replan case.
- Verify RED with HTTP 404, then GREEN after registering the thin endpoint.
- Run `.venv/bin/python -m pytest -v` and `.venv/bin/python -m compileall -q src`.
