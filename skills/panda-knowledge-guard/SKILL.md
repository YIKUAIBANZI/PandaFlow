---
name: panda-knowledge-guard
description: Answer Panda questions only from registered knowledge cards and refuse unsupported or medical claims.
---

# Panda Knowledge Guard

Call `POST /api/v1/skills/panda-knowledge-guard` with a question and `zh` or `en` language. It returns a sourced answer only when a registered card supports it; real-time, rumour, and medical questions are not answered as facts.
