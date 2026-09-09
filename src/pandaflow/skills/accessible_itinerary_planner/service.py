"""Deterministic, safety-first routing over PandaFlow's synthetic park graph."""

import heapq
from collections import defaultdict
from typing import Any

from pandaflow.shared.contracts import SkillResponse, SkillStatus
from pandaflow.shared.rules import load_json_resource
from pandaflow.skills.accessible_itinerary_planner.schemas import ItineraryRequest


SKILL_NAME = "accessible-itinerary-planner"
SOURCE_REF = "source_demo_park_graph"
RULE_REFS = ["rule_accessibility_hard_constraint", "rule_time_budget"]


def _shortest_path(
    graph: dict[str, Any], start: str, destination: str, allowed_nodes: set[str]
) -> tuple[list[str], int] | None:
    edges: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for left, right, minutes in graph["edges"]:
        if left in allowed_nodes and right in allowed_nodes:
            edges[left].append((right, minutes))
            edges[right].append((left, minutes))

    queue: list[tuple[int, str, list[str]]] = [(0, start, [start])]
    shortest: dict[str, int] = {start: 0}
    while queue:
        walked, current, path = heapq.heappop(queue)
        if current == destination:
            return path, walked
        if walked != shortest[current]:
            continue
        for neighbour, edge_minutes in edges[current]:
            candidate = walked + edge_minutes
            if candidate < shortest.get(neighbour, float("inf")):
                shortest[neighbour] = candidate
                heapq.heappush(queue, (candidate, neighbour, [*path, neighbour]))
    return None


def plan_itinerary(request: ItineraryRequest) -> SkillResponse:
    """Plan requested stops only when an accessible, time-bounded path exists."""

    graph = load_json_resource("park_graph.json")
    nodes: dict[str, dict[str, Any]] = graph["nodes"]
    allowed_nodes = set(nodes).difference(request.closed_nodes)
    if request.mobility_need == "step_free":
        allowed_nodes = {node for node in allowed_nodes if nodes[node]["step_free"]}

    if request.entry_node not in allowed_nodes:
        return _rejected("The selected entry is unavailable for this itinerary.")

    itinerary = [{"node_id": request.entry_node, "arrival_after_minutes": 0, "dwell_minutes": 0}]
    current_node = request.entry_node
    total_minutes = 0
    omitted_preferences: list[str] = []

    for preference in request.must_see:
        if preference not in allowed_nodes:
            omitted_preferences.append(preference)
            continue
        route = _shortest_path(graph, current_node, preference, allowed_nodes)
        if route is None:
            omitted_preferences.append(preference)
            continue
        path, walking_minutes = route
        dwell_minutes = nodes[preference]["dwell_minutes"]
        if total_minutes + walking_minutes + dwell_minutes > request.available_minutes:
            omitted_preferences.append(preference)
            continue
        for node in path[1:]:
            edge_route = _shortest_path(graph, current_node, node, allowed_nodes)
            assert edge_route is not None
            total_minutes += edge_route[1]
            itinerary.append(
                {
                    "node_id": node,
                    "arrival_after_minutes": total_minutes,
                    "dwell_minutes": dwell_minutes if node == preference else 0,
                }
            )
            current_node = node
        total_minutes += dwell_minutes

    if not request.must_see or len(omitted_preferences) == len(request.must_see):
        return _rejected("No requested stop has a safe route within the current constraints.")

    rest_stops = [step["node_id"] for step in itinerary if nodes[step["node_id"]]["rest_stop"]]
    warnings = []
    if omitted_preferences:
        warnings.append("Some requested stops were omitted to preserve safety, accessibility, or time limits.")
    return SkillResponse.create(
        skill=SKILL_NAME,
        status=SkillStatus.OK,
        data={
            "itinerary": itinerary,
            "total_minutes": total_minutes,
            "rest_stops": rest_stops,
            "omitted_preferences": omitted_preferences,
        },
        source_refs=[SOURCE_REF],
        rule_refs=RULE_REFS,
        warnings=warnings,
        next_actions=["Replan if an area closes or visitor needs change."],
        demo_data=graph["classification"] == "demo",
    )


def _rejected(reason: str) -> SkillResponse:
    return SkillResponse.create(
        skill=SKILL_NAME,
        status=SkillStatus.REJECTED,
        data={"itinerary": [], "total_minutes": 0, "rest_stops": [], "omitted_preferences": []},
        source_refs=[SOURCE_REF],
        rule_refs=RULE_REFS,
        warnings=[reason],
        next_actions=["Ask staff for a safe alternative route."],
        demo_data=True,
    )
