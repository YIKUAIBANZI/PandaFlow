# Open-Meteo Weather Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an attributed Open-Meteo current-weather adapter to the existing demo flow while preserving deterministic synthetic input and a safe offline fallback.

**Architecture:** Keep HTTP fetching outside all six Skills in `pandaflow.integrations`; resolve live, supplied-synthetic, or fixed-fallback weather in a small orchestration helper. The welfare Skill remains deterministic and receives a typed snapshot. The demo only fetches weather after incident, policy, and initial-route gates succeed, so a weather dependency can never delay urgent incident escalation.

**Tech Stack:** Python 3.13, HTTPX, Pydantic 2, FastAPI, pytest.

**Spec:** `docs/superpowers/specs/2026-09-04-pandaflow-design.md`

## Global Constraints

- Open-Meteo calls use the fixed `https://api.open-meteo.com/v1/forecast` endpoint with a 3.0-second total timeout and no user-controlled URL.
- Request only `temperature_2m`, `apparent_temperature`, `precipitation`, `weather_code`, and `wind_speed_10m` as current conditions in Celsius and `Asia/Shanghai` time.
- Live data carry Open-Meteo attribution and source references; free API use remains explicitly non-commercial and CC BY 4.0 attributed.
- Timeout, transport, HTTP, JSON, unit, or schema failure returns one fixed high-temperature demo snapshot and marks the workflow `degraded` without bypassing safety or route rules.
- `weather_mode="synthetic"` remains the default; existing requests with `temperature_celsius` retain their deterministic behavior.
- The adapter is not a seventh Skill and is excluded from `operations-review` Skill invocation counts.

---

### Task 1: Typed Open-Meteo Boundary and Deterministic Fallback

**Files:**
- Create: `src/pandaflow/integrations/__init__.py`
- Create: `src/pandaflow/integrations/open_meteo.py`
- Create: `src/pandaflow/orchestrator/weather.py`
- Create: `resources/weather_config.json`
- Test: `tests/unit/test_open_meteo_weather.py`

**Interfaces:**
- Produces: `WeatherSnapshot`, `WeatherResolution`, `OpenMeteoError`, `fetch_open_meteo_current(transport=None, timeout_seconds=3.0)`, and `resolve_weather(mode, temperature_celsius, visit_date, fetcher=None)`.
- `transport(url: str, timeout_seconds: float) -> bytes` is the only replaced boundary in tests; fixtures return a complete documented Open-Meteo `current` object.

- [x] **Step 1: Write failing adapter tests** for exact query variables and timeout, complete response parsing, oversized/malformed/wrong-unit payload rejection, fixed fallback values, supplied synthetic temperature, and non-current visit-date degradation without a network call.
- [x] **Step 2: Run `tests/unit/test_open_meteo_weather.py`** and verify collection fails because the integration module does not exist.
- [x] **Step 3: Implement the minimal adapter and resolver** with a 64 KiB response cap, finite numeric validation, exact unit validation, fixed demo coordinates from `weather_config.json`, and narrow exception translation to `OpenMeteoError`.
- [x] **Step 4: Run the unit file and full suite**; verify all weather boundary cases pass without a real network call.
- [x] **Step 5: Commit** with `feat: add resilient Open-Meteo weather adapter`.

### Task 2: Demo Orchestration and HTTP Contract

**Files:**
- Modify: `src/pandaflow/orchestrator/service.py`
- Modify: `src/pandaflow/skills/welfare_risk_dispatcher/schemas.py`
- Modify: `src/pandaflow/skills/welfare_risk_dispatcher/service.py`
- Modify: `tests/e2e/test_dynamic_demo.py`
- Modify: `tests/api/test_demo_endpoint.py`
- Modify: `tests/unit/test_welfare_risk_dispatcher.py`

**Interfaces:**
- `DemoRequest` adds `weather_mode: Literal["synthetic", "live_current"] = "synthetic"`; `temperature_celsius` becomes optional so live requests do not need a fake temperature.
- `run_demo(request, *, weather_fetcher=None)` resolves weather after the initial itinerary and adds the complete trusted snapshot to `data.weather`; `RiskDispatchRequest` accepts only the numeric fields needed for deterministic risk decisions.

- [x] **Step 1: Write failing orchestration tests** proving a successful live 33°C snapshot replans, dependency failure still replans from the fixed fallback and returns `degraded`, urgent incidents never call weather, and existing synthetic requests remain `ok`.
- [x] **Step 2: Run the focused E2E/API tests** and verify failures name the missing weather mode/data contract.
- [x] **Step 3: Implement minimal orchestration wiring**; merge weather source refs/warnings into the final envelope, preserve the stronger `escalated`/`rejected`/`needs_input` statuses, expose the complete source/time/location/attribution snapshot in the orchestrator response, and label the risk Skill's numeric evidence as caller supplied.
- [x] **Step 4: Run focused and full tests** and verify operations-review counts remain unchanged because the adapter is not a Skill.
- [x] **Step 5: Commit** with `feat: integrate live weather into demo flow`.

### Task 3: Attribution, Evidence, and Handoff

**Files:**
- Modify: `resources/source_registry.json`
- Modify: `README.md`
- Modify: `resources/demo_scenarios.json`
- Create: `evidence/open-meteo-weather-test-report.md`
- Modify: `mmr.md`

**Interfaces:**
- Source IDs: `source_open_meteo_forecast`, `source_open_meteo_license`, and `source_demo_weather_fallback`.
- Demo JSON retains the existing offline scenarios and adds one opt-in `live_current` request whose `visit_date` must be replaced with the actual run date.

- [x] **Step 1: Register official documentation and licence sources** with access date `2026-09-08`, plus the explicitly synthetic fallback source.
- [x] **Step 2: Document live usage, attribution, non-commercial free-tier boundary, exact fallback semantics, and the fact that crowd data remains synthetic.**
- [x] **Step 3: Run full tests, `compileall`, `git diff --check`, and an offline HTTP smoke** that forces dependency failure and proves a 200/degraded response with a safe route result.
- [x] **Step 4: If network access is available, run one real Open-Meteo smoke** and record the observed schema only; never make the real call a test prerequisite.
- [x] **Step 5: Update `mmr.md`** with verified results, correct the removed old-worktree environment path, and retain UI/knowledge/package/WorkHub work as incomplete.
- [x] **Step 6: Commit** with `docs: verify live weather milestone`.

### Task 4: Independent Review Hardening

- [x] Add regression tests for a total wall-clock deadline across streamed reads and truncated HTTP bodies.
- [x] Parse and validate the observation time in `Asia/Shanghai`, and compare live-current dates against the Shanghai calendar rather than the host timezone.
- [x] Prevent callers of the independent welfare Skill from claiming trusted Open-Meteo provenance; trusted source metadata remains on the orchestrator-owned weather snapshot.
- [x] Move HTTPX into runtime dependencies, correct the documented scenario count, and rerun focused plus full tests.

## Plan Self-Review

- **Spec coverage:** Covers required weather variables, 3-second timeout, fallback degradation, offline end-to-end completion, source traceability, and deterministic local behavior. New rain/wind welfare thresholds are intentionally excluded because no approved rule source exists.
- **Placeholder scan:** No implementation placeholder or unspecified error branch remains; the opt-in demo date instruction is user-facing runtime input, not unfinished code.
- **Type consistency:** The adapter returns one `WeatherResolution`; orchestration passes its `WeatherSnapshot` into the existing deterministic welfare Skill and does not add an execution record for the adapter.
