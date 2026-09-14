---
name: accessible-itinerary-planner
description: Produce a short, accessibility-aware itinerary from PandaFlow's synthetic demo map.
---

# Accessible Itinerary Planner

Use this Skill for a non-identifying pre-visit route request. Send `entry_node`, `available_minutes`, `must_see`, `mobility_need`, and optional `closed_nodes` to `POST /api/v1/skills/accessible-itinerary-planner`.

The map and all venue status are synthetic demo data. Closed or non-step-free nodes are hard constraints, never preference trade-offs. `must_see` is treated as an ordered set: duplicates do not create hidden dwell time, fulfilled targets are returned in `fulfilled_preferences`, and closed or unavailable targets appear in `omitted_preferences`. If no requested location is safely reachable, the Skill returns `rejected` and asks for a staff-provided alternative. `step_free` only describes the synthetic graph flag; it is not evidence of real slope, surface, wheelchair, or elder suitability.
