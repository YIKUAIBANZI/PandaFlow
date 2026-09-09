# PandaFlow Foundation and Visitor Policy Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the first independently executable PandaFlow Skill: a deterministic visitor-policy check with provenance, safety boundaries, and an HTTP endpoint.

**Architecture:** Create a small Python package using Pydantic for the shared response envelope and JSON resources for versioned, auditable policy data. The `visitor_policy_check` service reads only injected rule data, so it remains deterministic and testable; FastAPI is an adapter, not a place for business rules.

**Tech Stack:** Python 3.11, Pydantic 2, FastAPI, pytest, JSON resources.

**Spec:** `docs/superpowers/specs/2026-09-04-pandaflow-design.md`

## Global Constraints

- The system is a prototype and must not claim a relationship with Chengdu Research Base.
- All rule outputs include source and rule references; demo assumptions are explicitly marked.
- Never accept full ID numbers, phone numbers, real booking writes, diagnosis, or real work-order dispatch.
- Business statuses are exactly `ok`, `needs_input`, `degraded`, `escalated`, or `rejected`.
- Deterministic rules must not depend on an LLM, network access, or wall-clock time.
- The repository must run on Python 3.11 and be testable by `pytest`.

---

## File Structure

- `pyproject.toml` — package metadata, runtime dependencies, pytest configuration.
- `src/pandaflow/shared/contracts.py` — status enum and reusable response envelope.
- `src/pandaflow/shared/rules.py` — JSON resource loader with schema checks.
- `src/pandaflow/skills/visitor_policy_check/schemas.py` — privacy-safe request and result models.
- `src/pandaflow/skills/visitor_policy_check/service.py` — pure deterministic policy evaluation.
- `src/pandaflow/api/app.py` — FastAPI application and thin policy endpoint.
- `resources/source_registry.json` — provenance metadata used by the first Skill.
- `resources/visitor_rules.json` — versioned rules, marked as `demo` until the public rules are re-verified.
- `skills/visitor-policy-check/SKILL.md` — human and platform-neutral invocation contract.
- `tests/unit/` — real-code tests for contracts and policy evaluation.
- `tests/api/` — endpoint behavior test.

### Task 1: Establish the Testable Package Boundary and Shared Contract

**Files:**

- Create: `pyproject.toml`
- Create: `src/pandaflow/__init__.py`
- Create: `src/pandaflow/shared/__init__.py`
- Create: `src/pandaflow/shared/contracts.py`
- Create: `tests/unit/test_contracts.py`

**Interfaces:**

- Produces: `SkillStatus(str, Enum)` and `SkillResponse(BaseModel)`.
- `SkillResponse.create(skill: str, status: SkillStatus, data: dict, *, source_refs: list[str] = [], rule_refs: list[str] = [], warnings: list[str] = [], next_actions: list[str] = [], demo_data: bool = False) -> SkillResponse`.

- [ ] **Step 1: Write the failing envelope test**

```python
from pandaflow.shared.contracts import SkillResponse, SkillStatus


def test_response_contains_a_generated_request_id_and_required_fields():
    response = SkillResponse.create(
        skill="visitor-policy-check",
        status=SkillStatus.OK,
        data={"eligible": True},
        source_refs=["source_ticket_service"],
        rule_refs=["rule_reservation_required"],
        demo_data=True,
    )

    assert response.status is SkillStatus.OK
    assert response.request_id.startswith("req_")
    assert response.source_refs == ["source_ticket_service"]
    assert response.demo_data is True
```

- [ ] **Step 2: Run the test to verify RED**

Run: `python -m pytest tests/unit/test_contracts.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'pandaflow'`.

- [ ] **Step 3: Add the smallest package and envelope implementation**

```python
class SkillStatus(str, Enum):
    OK = "ok"
    NEEDS_INPUT = "needs_input"
    DEGRADED = "degraded"
    ESCALATED = "escalated"
    REJECTED = "rejected"


class SkillResponse(BaseModel):
    status: SkillStatus
    request_id: str
    skill: str
    data: dict[str, Any]
    source_refs: list[str] = Field(default_factory=list)
    rule_refs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    demo_data: bool = False
    generated_at: datetime
```

`create()` generates `req_<uuid4 hex>` and UTC `generated_at`; package configuration sets `src` as the import root.

- [ ] **Step 4: Run the test to verify GREEN**

Run: `python -m pytest tests/unit/test_contracts.py -v`

Expected: PASS.

- [ ] **Step 5: Commit the contract boundary**

```bash
git add pyproject.toml src/pandaflow tests/unit/test_contracts.py
git commit -m "feat: add PandaFlow response contract"
```

### Task 2: Add Versioned Resources and Safe Visitor-Policy Evaluation

**Files:**

- Create: `resources/source_registry.json`
- Create: `resources/visitor_rules.json`
- Create: `src/pandaflow/shared/rules.py`
- Create: `src/pandaflow/skills/__init__.py`
- Create: `src/pandaflow/skills/visitor_policy_check/__init__.py`
- Create: `src/pandaflow/skills/visitor_policy_check/schemas.py`
- Create: `src/pandaflow/skills/visitor_policy_check/service.py`
- Create: `tests/unit/test_visitor_policy_check.py`

**Interfaces:**

- Consumes: `SkillResponse` and `SkillStatus` from Task 1.
- Produces: `VisitorPolicyRequest(visit_date: date | None, entry_slot: str | None, reservation_status: Literal["confirmed", "missing", "unknown"] | None, document_type: str | None, language: Literal["zh", "en"] = "zh", accessibility_needs: list[str] = [])` and `evaluate_policy(request: VisitorPolicyRequest, rules_path: Path | None = None) -> SkillResponse`.
- The JSON source entry must have `source_id`, `title`, `publisher`, `url`, `accessed_on`, `summary`, and `applies_to`.

- [ ] **Step 1: Write failing tests for the three decision branches**

```python
from datetime import date

from pandaflow.shared.contracts import SkillStatus
from pandaflow.skills.visitor_policy_check.schemas import VisitorPolicyRequest
from pandaflow.skills.visitor_policy_check.service import evaluate_policy


def test_missing_visit_date_requests_required_information():
    result = evaluate_policy(VisitorPolicyRequest(reservation_status="confirmed"))
    assert result.status is SkillStatus.NEEDS_INPUT
    assert result.data["missing_fields"] == ["visit_date"]


def test_unconfirmed_reservation_does_not_promise_entry():
    result = evaluate_policy(
        VisitorPolicyRequest(
            visit_date=date(2026, 7, 4), entry_slot="morning", reservation_status="missing"
        )
    )
    assert result.status is SkillStatus.NEEDS_INPUT
    assert result.data["eligible"] is False
    assert "booking" in result.next_actions[0].lower()


def test_unknown_document_type_is_escalated_for_human_verification():
    result = evaluate_policy(
        VisitorPolicyRequest(
            visit_date=date(2026, 7, 4), entry_slot="morning", reservation_status="confirmed", document_type="other"
        )
    )
    assert result.status is SkillStatus.ESCALATED
    assert result.data["eligible"] is None
```

- [ ] **Step 2: Run the policy tests to verify RED**

Run: `python -m pytest tests/unit/test_visitor_policy_check.py -v`

Expected: FAIL with `ModuleNotFoundError` for `pandaflow.skills.visitor_policy_check`.

- [ ] **Step 3: Implement only the rules required by the tests**

```python
def evaluate_policy(request: VisitorPolicyRequest, rules_path: Path | None = None) -> SkillResponse:
    if request.visit_date is None:
        return response_for_missing_field("visit_date")
    if request.reservation_status != "confirmed":
        return response_for_reservation_gap(request.reservation_status)
    if request.document_type not in {None, "passport", "mainland_id", "resident_permit"}:
        return response_for_unknown_document(request.document_type)
    return response_for_confirmed_conditions(request)
```

The JSON resource contains a `rule_version`, a public-service source reference, and conservative **demo** time windows. It must never contain a ticket price, a real-time capacity claim, or a promise of admission. The Pydantic request model must not define any ID-number or phone field.

- [ ] **Step 4: Run the policy tests to verify GREEN**

Run: `python -m pytest tests/unit/test_visitor_policy_check.py -v`

Expected: PASS.

- [ ] **Step 5: Add one regression test for privacy-safe input**

```python
from pydantic import ValidationError


def test_request_rejects_unmodelled_personal_identifier_field():
    with pytest.raises(ValidationError):
        VisitorPolicyRequest.model_validate({"visit_date": "2026-07-04", "id_number": "510000199001011234"})
```

Run: `python -m pytest tests/unit/test_visitor_policy_check.py -v`

Expected: PASS after setting the request model to `extra="forbid"`.

- [ ] **Step 6: Commit the independent Skill**

```bash
git add resources src/pandaflow/skills tests/unit/test_visitor_policy_check.py
git commit -m "feat: add visitor policy check skill"
```

### Task 3: Expose the Skill Through a Thin HTTP Adapter

**Files:**

- Create: `src/pandaflow/api/__init__.py`
- Create: `src/pandaflow/api/app.py`
- Create: `tests/api/test_policy_endpoint.py`

**Interfaces:**

- Consumes: `VisitorPolicyRequest` and `evaluate_policy()` from Task 2.
- Produces: `app` with `GET /health` and `POST /api/v1/skills/visitor-policy-check`.
- Valid request payloads return HTTP 200 even when the business response status is `needs_input` or `escalated`; malformed JSON/schema input retains FastAPI 422 behavior.

- [ ] **Step 1: Write the failing endpoint test**

```python
from fastapi.testclient import TestClient
from pandaflow.api.app import app


def test_policy_endpoint_returns_business_status_inside_response_envelope():
    response = TestClient(app).post(
        "/api/v1/skills/visitor-policy-check",
        json={"visit_date": "2026-07-04", "entry_slot": "morning", "reservation_status": "missing"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "needs_input"
    assert response.json()["skill"] == "visitor-policy-check"
```

- [ ] **Step 2: Run the endpoint test to verify RED**

Run: `python -m pytest tests/api/test_policy_endpoint.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'pandaflow.api'`.

- [ ] **Step 3: Implement the minimal FastAPI adapter**

```python
app = FastAPI(title="PandaFlow")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/skills/visitor-policy-check")
def visitor_policy_check(request: VisitorPolicyRequest) -> SkillResponse:
    return evaluate_policy(request)
```

- [ ] **Step 4: Run the endpoint test to verify GREEN**

Run: `python -m pytest tests/api/test_policy_endpoint.py -v`

Expected: PASS.

- [ ] **Step 5: Commit the API adapter**

```bash
git add src/pandaflow/api tests/api/test_policy_endpoint.py
git commit -m "feat: expose visitor policy API"
```

### Task 4: Document the Skill and Verify the Milestone as a Whole

**Files:**

- Create: `skills/visitor-policy-check/SKILL.md`
- Create: `README.md`

**Interfaces:**

- Documents the request schema and output envelope defined by Tasks 1–3.
- Explicitly says resources are demo-labelled until source re-verification, and says it does not book tickets or guarantee entry.

- [ ] **Step 1: Write failing documentation-presence test**

```python
from pathlib import Path


def test_skill_document_declares_the_http_entrypoint_and_safety_boundary():
    text = Path("skills/visitor-policy-check/SKILL.md").read_text(encoding="utf-8")
    assert "POST /api/v1/skills/visitor-policy-check" in text
    assert "不执行购票" in text
```

- [ ] **Step 2: Run the test to verify RED**

Run: `python -m pytest tests/unit/test_skill_documentation.py -v`

Expected: FAIL because the document is missing.

- [ ] **Step 3: Write the minimal operating documentation**

The Skill document names its trigger, JSON input, response statuses, source and demo rules, and local command `uvicorn pandaflow.api.app:app --reload`. The README gives only the first-mile installation, test, and launch commands; it does not claim WorkHub integration is complete.

- [ ] **Step 4: Run all milestone checks**

Run: `python -m pytest -v`

Expected: all tests PASS.

Run: `python -m compileall -q src`

Expected: exit code 0.

- [ ] **Step 5: Commit documentation and proof**

```bash
git add README.md skills/visitor-policy-check tests/unit/test_skill_documentation.py
git commit -m "docs: document visitor policy skill"
```

## Plan Self-Review

- **Spec coverage:** This milestone implements the shared envelope and source/rule traceability, the entire `visitor-policy-check` decision path, its function and HTTP interface, privacy rejection, and documentation. The other five independent Skills, orchestrator, weather adapter, web demo, evidence export, and WorkHub mapping deliberately remain later milestones; this avoids falsely representing a partial prototype as the full six-Skill submission.
- **Placeholder scan:** No unresolved or future-code placeholder is used in executable steps. The resource data is explicitly constrained as demo data rather than disguised as current operating data.
- **Type consistency:** Task 1 defines `SkillResponse` and `SkillStatus`; Task 2 consumes both and returns the former; Task 3 adapts the same request/response models without reimplementing rules.
