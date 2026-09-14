---
name: visitor-policy-check
description: Validate only the minimum non-identifying pre-visit conditions for PandaFlow's demo scenario.
---

# Visitor Policy Check

Use this Skill for the fixed demo's required date, time slot, reservation state, and document-type completeness check. `language` and `accessibility_needs` are accepted as bounded context but do not currently change the policy decision.

## Boundaries

- This is a PandaFlow prototype, not an official system of Chengdu Research Base of Giant Panda Breeding.
- It does not execute ticket purchase, modify reservations, verify a real identity, or guarantee admission.
- Do not request or accept an ID number, phone number, payment information, or a booking reference.
- Current rules are explicit `demo` rules. The output marks this through `demo_data: true` and a warning until public sources are re-verified.

## HTTP interface

Send a JSON request to `POST /api/v1/skills/visitor-policy-check`:

```json
{
  "visit_date": "2026-07-04",
  "entry_slot": "morning",
  "reservation_status": "confirmed",
  "document_type": "passport",
  "language": "en",
  "accessibility_needs": ["wheelchair"]
}
```

`reservation_status` accepts `confirmed`, `missing`, or `unknown`. Document types are descriptive labels only; a new or unsupported label routes the visitor to a human check. The response follows the common PandaFlow envelope and uses one of `ok`, `needs_input`, `degraded`, `escalated`, or `rejected`.

## Local operation

```bash
uv venv .venv
uv pip install -e '.[test]'
.venv/bin/uvicorn pandaflow.api.app:app --reload
```

The local API documentation is available at `/docs`. Run the unit and API checks with `.venv/bin/python -m pytest -v`.
