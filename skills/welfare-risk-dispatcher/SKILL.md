---
name: welfare-risk-dispatcher
description: Assess synthetic weather and area-status risks, then request a safe itinerary replan when necessary.
---

# Welfare Risk Dispatcher

Send demo temperature, crowd level, current route nodes and optional closed nodes to `POST /api/v1/skills/welfare-risk-dispatcher`.

This Skill returns `risk_level`, `replan_required`, and `avoid_nodes`. It does not diagnose an animal, infer real-time animal location, notify a venue, or claim that any operating state changed. Current thresholds and status data are synthetic; a future adapter will fetch Open-Meteo data with an explicit degraded fallback.
