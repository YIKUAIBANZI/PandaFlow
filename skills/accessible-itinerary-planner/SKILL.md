---
name: accessible-itinerary-planner
description: Produce a short, accessibility-aware itinerary from PandaFlow's synthetic demo map.
---

# Accessible Itinerary Planner

Use this Skill for a non-identifying pre-visit route request. Send `entry_node`, `available_minutes`, `must_see`, `mobility_need`, and optional `closed_nodes` to `POST /api/v1/skills/accessible-itinerary-planner`.

The map and all venue status are synthetic demo data. Closed or non-step-free nodes are hard constraints, never preference trade-offs. A closed preference is returned in `omitted_preferences`; if no requested location is safely reachable, the Skill returns `rejected` and asks for a staff-provided alternative.
