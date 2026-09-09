# Panda Knowledge Guard Implementation Plan

**Goal:** Add a source-bound knowledge Skill that answers only registered PandaFlow knowledge cards and refuses unsupported or medical claims.

**Architecture:** A deterministic keyword matcher searches local JSON cards; an answer carries its card source. No match returns `needs_input`; medical keywords return `rejected` before retrieval. A thin API route exposes the same service.

**Tests:** known fact returns an answer and source; rumour returns no-evidence status; medical question is rejected; HTTP response carries the Skill envelope.
