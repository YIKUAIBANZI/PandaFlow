---
name: welfare-risk-dispatcher
description: Assess synthetic weather and area-status risks, then request a safe itinerary replan when necessary.
---

# Welfare Risk Dispatcher

Send demo temperature, crowd level, current route nodes and optional closed nodes to `POST /api/v1/skills/welfare-risk-dispatcher`.

This Skill returns `risk_level`, `replan_required`, route-specific `avoid_nodes`, and the complete `active_avoid_nodes` set. Simultaneous closure and high-heat rules are merged. It does not diagnose an animal, infer real-time animal location, notify a venue, or claim that any operating state changed. Thresholds and closure state are synthetic; the orchestrator may supply fresh Open-Meteo current-model data and otherwise uses an explicit synthetic fallback.
