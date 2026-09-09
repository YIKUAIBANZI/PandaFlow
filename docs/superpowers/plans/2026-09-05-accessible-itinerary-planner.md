# Accessible Itinerary Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, accessibility-aware route Skill for the fixed PandaFlow demo story: a family with a child and elder has 120 minutes after a morning entry.

**Architecture:** The Skill loads a versioned, explicitly demo-labelled park graph and uses a shortest-path calculation that removes closed and inaccessible nodes before scoring visitor preferences. It produces a structured itinerary, rest stops, omitted preferences and a rejection when no safe path exists; the existing FastAPI app only adapts the Skill at a new endpoint.

**Tech Stack:** Python 3.11+, Pydantic 2, FastAPI, pytest, JSON resources.

**Spec:** `docs/superpowers/specs/2026-09-04-pandaflow-design.md`

## Global Constraints

- Priority is safety, animal welfare and park rules, accessibility, then visitor preference.
- The park graph, duration and status data are demo data, not a representation of a real park map, queue, animal location or opening status.
- Closed or inaccessible nodes must never appear in an itinerary, even when requested as a preference.
- A route must fit within `available_minutes`; when no safe route exists, return `rejected` rather than invent one.
- All responses use the established `SkillResponse` envelope with provenance and `demo_data=true`.

---

## File Structure

- `resources/park_graph.json` — seven-node synthetic accessible map with walking minutes, dwell times, rest facilities and provenance.
- `resources/source_registry.json` — adds a demo-map provenance record.
- `src/pandaflow/skills/accessible_itinerary_planner/schemas.py` — input constraints for the route Skill.
- `src/pandaflow/skills/accessible_itinerary_planner/service.py` — graph loading, constrained shortest path and itinerary assembly.
- `skills/accessible-itinerary-planner/SKILL.md` — invocation and safety boundary documentation.
- `src/pandaflow/api/app.py` — new thin route endpoint.
- `tests/unit/test_accessible_itinerary_planner.py` — normal, closure and no-safe-route behavior.
- `tests/api/test_itinerary_endpoint.py` — HTTP response-envelope contract.

### Task 1: Prove the Planner Enforces Hard Safety and Accessibility Constraints

**Files:**

- Create: `tests/unit/test_accessible_itinerary_planner.py`
- Create: `src/pandaflow/skills/accessible_itinerary_planner/__init__.py`
- Create: `src/pandaflow/skills/accessible_itinerary_planner/schemas.py`
- Create: `src/pandaflow/skills/accessible_itinerary_planner/service.py`
- Create: `resources/park_graph.json`
- Modify: `resources/source_registry.json`

**Interfaces:**

- Consumes: `SkillResponse`, `SkillStatus`, and `load_json_resource()`.
- Produces: `ItineraryRequest(entry_node: str, available_minutes: int, must_see: list[str], mobility_need: Literal["standard", "step_free"], closed_nodes: list[str])` and `plan_itinerary(request: ItineraryRequest) -> SkillResponse`.
- `data` always includes `itinerary`, `total_minutes`, `rest_stops`, and `omitted_preferences`; route steps expose `node_id`, `arrival_after_minutes`, and `dwell_minutes`.

- [ ] **Step 1: Write the failing normal-route test**

```python
def test_step_free_family_route_has_a_rest_stop_and_stays_within_time_budget():
    result = plan_itinerary(
        ItineraryRequest(
            entry_node="north_gate",
            available_minutes=120,
            must_see=["panda_nursery", "science_hall"],
            mobility_need="step_free",
        )
    )

    assert result.status is SkillStatus.OK
    assert result.data["total_minutes"] <= 120
    assert "science_hall" in result.data["rest_stops"]
    assert "hillside_trail" not in [step["node_id"] for step in result.data["itinerary"]]
    assert result.demo_data is True
```

- [ ] **Step 2: Run it to verify RED**

Run: `.venv/bin/python -m pytest tests/unit/test_accessible_itinerary_planner.py -v`

Expected: FAIL because the planner module does not exist.

- [ ] **Step 3: Implement only the requested normal route**

Create a synthetic graph with `north_gate`, `panda_nursery`, `science_hall`, `bamboo_grove`, `hillside_trail`, `lake_pavilion`, and `south_gate`. Mark `hillside_trail` as not step-free. Use Dijkstra with node filtering to calculate the lowest-walking-time path between waypoints; append requested waypoints in request order only when travel plus dwell time remains in budget. `science_hall` is the demo rest facility and its dwell time is included in the total.

- [ ] **Step 4: Run it to verify GREEN**

Run: `.venv/bin/python -m pytest tests/unit/test_accessible_itinerary_planner.py -v`

Expected: PASS.

- [ ] **Step 5: Add a failing closure-replan test**

```python
def test_closed_preferred_node_is_omitted_without_violating_accessibility():
    result = plan_itinerary(
        ItineraryRequest(
            entry_node="north_gate",
            available_minutes=120,
            must_see=["panda_nursery", "bamboo_grove"],
            mobility_need="step_free",
            closed_nodes=["bamboo_grove"],
        )
    )

    nodes = [step["node_id"] for step in result.data["itinerary"]]
    assert result.status is SkillStatus.OK
    assert "bamboo_grove" not in nodes
    assert result.data["omitted_preferences"] == ["bamboo_grove"]
```

- [ ] **Step 6: Implement and verify the closure branch**

Filter `closed_nodes` before path search, return the omitted requested node in `omitted_preferences`, and give an explanatory warning without changing the normal status to `degraded`.

Run: `.venv/bin/python -m pytest tests/unit/test_accessible_itinerary_planner.py -v`

Expected: PASS.

- [ ] **Step 7: Add and satisfy the no-safe-route test**

```python
def test_no_safe_path_is_rejected_instead_of_returning_a_fabricated_route():
    result = plan_itinerary(
        ItineraryRequest(
            entry_node="north_gate",
            available_minutes=120,
            must_see=["panda_nursery"],
            mobility_need="step_free",
            closed_nodes=["panda_nursery", "science_hall"],
        )
    )

    assert result.status is SkillStatus.REJECTED
    assert result.data["itinerary"] == []
```

If every requested must-see node is unavailable or inaccessible, return `rejected`, an empty itinerary and a next action asking staff for a safe alternative. Run the same command and confirm PASS.

- [ ] **Step 8: Commit the route engine**

```bash
git add resources/park_graph.json resources/source_registry.json src/pandaflow/skills/accessible_itinerary_planner tests/unit/test_accessible_itinerary_planner.py
git commit -m "feat: add accessible itinerary planner"
```

### Task 2: Expose and Document the Independent Skill

**Files:**

- Modify: `src/pandaflow/api/app.py`
- Create: `tests/api/test_itinerary_endpoint.py`
- Create: `skills/accessible-itinerary-planner/SKILL.md`
- Modify: `README.md`

**Interfaces:**

- Consumes: `ItineraryRequest` and `plan_itinerary()`.
- Produces: `POST /api/v1/skills/accessible-itinerary-planner`, with valid business requests returning HTTP 200 and a response envelope.

- [ ] **Step 1: Write the failing endpoint test**

```python
def test_itinerary_endpoint_returns_a_route_envelope():
    response = asyncio.run(post_route())
    assert response.status_code == 200
    assert response.json()["skill"] == "accessible-itinerary-planner"
    assert response.json()["status"] == "ok"
```

`post_route()` uses `httpx.ASGITransport(app=app)` with the fixed step-free, 120-minute request, matching the existing API test style.

- [ ] **Step 2: Run it to verify RED**

Run: `.venv/bin/python -m pytest tests/api/test_itinerary_endpoint.py -v`

Expected: FAIL with HTTP 404.

- [ ] **Step 3: Add the thin HTTP route**

```python
@app.post("/api/v1/skills/accessible-itinerary-planner")
def accessible_itinerary_planner(request: ItineraryRequest) -> SkillResponse:
    return plan_itinerary(request)
```

- [ ] **Step 4: Run it to verify GREEN**

Run: `.venv/bin/python -m pytest tests/api/test_itinerary_endpoint.py -v`

Expected: PASS.

- [ ] **Step 5: Write operating docs, then verify the whole milestone**

The Skill document declares the synthetic-map boundary, its required input, closure replan behavior, rejection behavior and HTTP path. Update README to list both delivered Skills. Do not add a test that only searches prose text.

Run: `.venv/bin/python -m pytest -v`

Expected: all existing and new tests PASS.

Run: `.venv/bin/python -m compileall -q src`

Expected: exit code 0.

- [ ] **Step 6: Commit API and docs**

```bash
git add src/pandaflow/api/app.py tests/api/test_itinerary_endpoint.py skills/accessible-itinerary-planner/SKILL.md README.md
git commit -m "feat: expose itinerary planning API"
```

## Plan Self-Review

- **Spec coverage:** The plan covers map-based routing, time budget, rest stops, hard accessibility and closure constraints, an infeasible-route rejection, function/HTTP invocation, provenance and independent Skill documentation. Weather-based risk scoring, orchestration and UI remain separate later Skills.
- **Placeholder scan:** Every implementation and verification step provides a concrete command, test behaviour or implementation rule.
- **Type consistency:** Task 1 defines the request and return type; Task 2 consumes the same models and does not recreate route logic in the API.
