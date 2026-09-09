# Incident Triage and Operations Review Implementation Plan

> Use superpowers:executing-plans with test-first verification for each task.

**Goal:** Deliver independent incident and review Skills and demonstrate interruption plus traceable review.

**Architecture:** Local versioned demo rules drive deterministic incident classification; an allowlisted metadata schema drives review. The orchestrator gives incident safety precedence, records only execution metadata and invokes review on both completed and stopped flows.

**Tech Stack:** Existing Python, Pydantic, FastAPI, pytest and JSON resources; no new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-04-pandaflow-design.md`, sections 7.5, 7.6, 8, 11. User approved continuous recommended implementation in the preceding task.

## Global Constraints

- Safety > welfare and park rules > accessibility > preferences.
- Six incident categories: medical, missing_person, lost_property, ticketing, order, facility. Unknown requests ask for clarification; possible danger escalates conservatively.
- P0 urgent danger; P1 medical, missing person and uncertain danger; P2 active routine incidents; P3 inactive routine requests. This is a synthetic routing matrix, never a clinical assessment.
- Only draft suggestions: `dispatch_status=draft`, `sent=false`. Do not echo free-text descriptions or identifying details.
- Medical and missing-person indicators override a low-risk category hint and claims of resolution. Return escalated even when location is absent.
- Review consumes explicit metadata fields only, rejects unknown nested/personal fields and duplicate record IDs, and provides observations with record IDs rather than causal claims.
- All new rules/resources and responses carry demo provenance. No WorkHub or real ticketing writes.

## Task 1: Independent incident Skill

Files: create `src/pandaflow/skills/incident_triage_dispatch/{__init__,schemas,service}.py`, `resources/incident_rules.json`, `skills/incident-triage-dispatch/SKILL.md`, `tests/api/test_incident_endpoint.py`; modify `src/pandaflow/api/app.py` and source registry.

Interface: `IncidentRequest(description, area, involved_groups, is_ongoing, measures_taken, category_hint)` -> `triage_incident(request) -> SkillResponse`.

- [x] Write HTTP tests for six categories, critical danger, conflicting hint, missing details, unknown description, no dispatch claims, invalid inputs and resource failure.
- [x] Run `.venv/bin/python -m pytest tests/api/test_incident_endpoint.py -q`; verify missing endpoint fails with 404.
- [x] Implement JSON rule matching with highest-priority evidence selected before routine categories. Missing location adds follow-up questions without downgrading escalation. Resource errors return a conservative manual-review response.
- [x] Run the same tests to GREEN; document Python/HTTP invocation and input/output boundaries.

Concrete acceptance example:
```python
response = post('/api/v1/skills/incident-triage-dispatch', {
    'description': '儿童走失', 'category_hint': 'lost_property'
})
assert response.json()['status'] == 'escalated'
assert response.json()['data']['category'] == 'missing_person'
assert response.json()['data']['sent'] is False
```

## Task 2: Independent review Skill

Files: create `src/pandaflow/skills/operations_review/{__init__,schemas,service}.py`, `resources/review_rules.json`, `skills/operations-review/SKILL.md`, `tests/api/test_review_endpoint.py`; modify API and source registry.

Interface: `ReviewRequest(records: list[dict])` -> `review_operations(request) -> SkillResponse`. Each record contains record_id, skill, status, rule_refs, source_refs, demo_data, optional incident_category and priority; no free text.

- [x] Write tests using three hand-checked records: degraded=1, escalated=1, medical=1, repeated rule counted per record, and observation IDs resolving to inputs. Test empty input, duplicate IDs, private/nested fields, invalid status and missing resource.
- [x] Run `.venv/bin/python -m pytest tests/api/test_review_endpoint.py -q`; verify HTTP 404.
- [x] Implement strict record parsing before aggregation, counts by status/skill/rule/category, evidence-backed observations and rule-update candidates; reject invalid payloads without echoing them.
- [x] Run to GREEN and document independent usage.

Concrete acceptance example:
```python
assert output['data']['total_calls'] == 3
assert output['data']['degraded_count'] == 1
assert output['data']['event_counts'] == {'medical': 1}
```

## Task 3: Integrate and verify

Files: modify `src/pandaflow/orchestrator/service.py`, `tests/e2e/test_dynamic_demo.py`, README; create root `mmr.md` and project `AGENTS.md` handoff.

- [x] Write E2E tests: urgent incident returns escalated before itinerary, includes a review of that one call; routine incident plus optional supported knowledge query completes with six Skill types represented; repeated final itinerary is counted only if it was executed again; rejected route retains previous metadata.
- [x] Run E2E tests to RED, add optional incident and knowledge inputs, centralize response finalization to collect sanitized execution records and review on every exit.
- [x] Verify `.venv/bin/python -m pytest -q` and `.venv/bin/python -m compileall -q src`; inspect diff and resolve review findings.
- [x] Update handoff with verified status and remaining weather/UI/evidence/platform work; commit and fast-forward local main after explicit confirmation. Implementation commit `ff984f5` is now on `main`; the merged result passed all 60 tests plus `compileall` and `git diff --check`.

Self-review: this milestone covers spec 7.5/7.6 and the interruption/review portions of section 8. Live weather, complete knowledge matching, web UI, export packaging and platform validation remain explicit later milestones.
