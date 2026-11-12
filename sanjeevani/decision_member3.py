"""
Member 3 Decision & Optimization Engine (`sanjeevani/decision.py`):
- Phase 5: Emergency Rescue Route Optimization
- Phase 6: Emergency Resource Allocation
- Phase 7: Rescue Strategy Comparison
- Phase 8: Active Observation Planning (Explainable Prototype)
"""

import heapq
import math
import networkx as nx

from sanjeevani.flood_vulnerability import estimate_edge_vulnerability, _parse_float


# --------------------------------------------------
# DEFAULT SPEED ASSUMPTIONS BY HIGHWAY CLASS (KM/H)
# --------------------------------------------------

DEFAULT_HIGHWAY_SPEED_KMH = {
    "motorway": 65.0,
    "motorway_link": 45.0,
    "trunk": 55.0,
    "trunk_link": 40.0,
    "primary": 45.0,
    "primary_link": 35.0,
    "secondary": 38.0,
    "secondary_link": 30.0,
    "tertiary": 32.0,
    "tertiary_link": 25.0,
    "residential": 22.0,
    "living_street": 15.0,
    "unclassified": 25.0,
    "service": 15.0,
    "road": 20.0,
}

RESTRICTIVE_ACCESS_VALUES = {
    "private",
    "customers",
    "destination",
    "military",
    "permit",
    "limited",
    "delivery",
    "agricultural",
    "forestry",
}

PROHIBITED_ACCESS_VALUES = {
    "no",
    "false",
    "0",
}

VERIFIED_EMERGENCY_VALUES = {
    "yes",
    "designated",
    "official",
    "permissive",
    "true",
    "1",
}


# ==================================================
# PHASE 5: EMERGENCY RESCUE ROUTE OPTIMIZATION
# ==================================================

def evaluate_emergency_access(edge_data):
    """
    Evaluate whether a road edge is passable and suitable for emergency vehicles.

    Does NOT assume every road in OSM is automatically accessible to emergency
    vehicles. Distinguishes:
    - "blocked": flooded (`condition == 'BLOCKED'` or `available is False`) or failed
    - "prohibited": explicit `emergency=no` or `access/motor_vehicle=no` without override
    - "verified_emergency_access": explicit `emergency=yes/designated`
    - "uncertain_emergency_access": `access=private/military/customers`, `oneway=conditional`,
      narrow service/living_street, or missing clearance verification
    - "public_drivable_unverified": public road without restrictive access tags
    """

    if edge_data.get("available") is False or edge_data.get("condition") == "BLOCKED" or edge_data.get("failed") is True:
        return {
            "status": "blocked",
            "passable": False,
            "uncertain": False,
            "reason": "Road segment is blocked by flooding or structural failure.",
        }

    emergency_tag = str(edge_data.get("emergency", "unknown")).strip().lower()
    if emergency_tag in PROHIBITED_ACCESS_VALUES:
        return {
            "status": "prohibited",
            "passable": False,
            "uncertain": False,
            "reason": "Explicit emergency=no tag prohibits emergency vehicle entry.",
        }

    if emergency_tag in VERIFIED_EMERGENCY_VALUES:
        return {
            "status": "verified_emergency_access",
            "passable": True,
            "uncertain": False,
            "reason": f"Explicit emergency={emergency_tag} tag present in OSM.",
        }

    access_tags = (
        str(edge_data.get("motor_vehicle", "unknown")).strip().lower(),
        str(edge_data.get("vehicle", "unknown")).strip().lower(),
        str(edge_data.get("access", "unknown")).strip().lower(),
    )

    if any(val in PROHIBITED_ACCESS_VALUES for val in access_tags):
        return {
            "status": "prohibited",
            "passable": False,
            "uncertain": True,
            "reason": "Tag access/vehicle/motor_vehicle=no without explicit emergency=yes override.",
        }

    uncertain_reasons = []
    if any(val in RESTRICTIVE_ACCESS_VALUES for val in access_tags):
        uncertain_reasons.append(
            f"Restrictive access tag ({'/'.join(v for v in access_tags if v in RESTRICTIVE_ACCESS_VALUES)}) may have physical gates/barriers"
        )

    if str(edge_data.get("oneway", "")).lower() == "conditional":
        uncertain_reasons.append("Conditional/reversible one-way flow requires field verification")

    highway = str(edge_data.get("highway", "unknown")).strip().lower()
    width_val = _parse_float(edge_data.get("width"))
    if width_val is not None and width_val < 3.2:
        uncertain_reasons.append(f"Narrow width ({width_val}m < 3.2m) may obstruct large fire/rescue vehicles")
    elif highway in ("service", "living_street") and width_val is None:
        uncertain_reasons.append(f"Unverified carriageway clearance on '{highway}' road")

    if uncertain_reasons:
        return {
            "status": "uncertain_emergency_access",
            "passable": True,
            "uncertain": True,
            "reason": "; ".join(uncertain_reasons),
        }

    return {
        "status": "public_drivable_unverified",
        "passable": True,
        "uncertain": False,
        "reason": "Public drivable road without restrictive OSM access tags (physical clearance unverified).",
    }


def estimate_edge_travel_time_sec(edge_data):
    """
    Estimate travel time in seconds across a single road segment, accounting for:
    - Segment length (`length_m`)
    - Posted `maxspeed` or highway-class default speed
    - Flood condition (`AT RISK` applies a 45% speed reduction / 1.8x time penalty)
    - Surface/smoothness degradation
    """

    length_m = float(edge_data.get("length_m", edge_data.get("length", 100.0)))
    if length_m <= 0:
        raise ValueError(f"Edge length must be positive, got {length_m}")

    highway = str(edge_data.get("highway", "residential")).strip().lower()
    speed_kmh = _parse_float(edge_data.get("maxspeed"))
    if speed_kmh is None or speed_kmh <= 0:
        speed_kmh = DEFAULT_HIGHWAY_SPEED_KMH.get(highway, 25.0)

    # Apply realistic flood & surface speed adjustments
    condition = str(edge_data.get("condition", "OPEN")).upper()
    if condition == "AT RISK":
        speed_kmh *= 0.55
    elif condition == "BLOCKED" or edge_data.get("available") is False:
        return float("inf")

    smoothness = str(edge_data.get("smoothness", "unknown")).strip().lower()
    if smoothness in ("impassable", "very_horrible", "horrible", "very_bad"):
        speed_kmh *= 0.60
    elif smoothness in ("bad", "intermediate"):
        speed_kmh *= 0.80

    speed_ms = max(1.0, (speed_kmh * 1000.0) / 3600.0)
    return length_m / speed_ms


def _select_best_parallel_edge(
    graph,
    u,
    v,
    optimize_for="time",
    allow_at_risk=True,
    allow_uncertain_access=True,
    penalized_edges=None,
    penalty_factor=2.5,
):
    """
    Inspect all parallel edges between `u` and `v` in a Graph, DiGraph, or
    MultiDiGraph and return `(best_cost, best_key, best_data, access_info)`.
    Returns `(None, None, None, None)` if no valid passable edge exists.
    """

    if not graph.has_edge(u, v):
        return None, None, None, None

    is_multi = graph.is_multigraph()
    raw_edges = graph[u][v]
    candidate_items = raw_edges.items() if is_multi else [(0, raw_edges)]

    best_cost = float("inf")
    best_key = None
    best_data = None
    best_access = None

    for key, data in candidate_items:
        access_info = evaluate_emergency_access(data)
        if not access_info["passable"]:
            continue

        if access_info["uncertain"] and not allow_uncertain_access:
            continue

        cond = str(data.get("condition", "OPEN")).upper()
        if cond == "AT RISK" and not allow_at_risk:
            continue

        length_m = float(data.get("length_m", data.get("length", 100.0)))
        if length_m <= 0:
            continue

        travel_time_s = estimate_edge_travel_time_sec(data)
        if math.isinf(travel_time_s):
            continue

        base_cost = travel_time_s if optimize_for == "time" else length_m

        # Soft safety penalties to prefer safer, verified-access roads when available
        if cond == "AT RISK":
            base_cost *= 1.50
        if access_info["uncertain"]:
            base_cost *= 1.35

        road_id = str(data.get("road_id", f"{u}-{v}"))
        if penalized_edges and (
            (u, v, key) in penalized_edges
            or (u, v) in penalized_edges
            or road_id in penalized_edges
        ):
            base_cost *= penalty_factor

        if base_cost < best_cost:
            best_cost = base_cost
            best_key = key
            best_data = data
            best_access = access_info

    if best_data is None:
        return None, None, None, None

    return best_cost, best_key, best_data, best_access


def find_shortest_safe_route(
    graph,
    origin,
    destination,
    optimize_for="time",
    allow_at_risk=True,
    allow_uncertain_access=True,
    penalized_edges=None,
    penalty_factor=2.5,
):
    """
    Find the optimal safe rescue route from `origin` to `destination` using
    Dijkstra's algorithm while respecting:
    - Directed one-way edges
    - Multiple parallel edges between the same nodes
    - Blocked road avoidance (`condition == 'BLOCKED'` or `available == False`)
    - Emergency access restrictions and uncertainty flags
    """

    if optimize_for not in ("time", "distance"):
        raise ValueError("optimize_for must be either 'time' or 'distance'.")

    if origin not in graph:
        raise ValueError(f"Origin node '{origin}' not found in graph.")
    if destination not in graph:
        raise ValueError(f"Destination node '{destination}' not found in graph.")

    if origin == destination:
        return {
            "reachable": True,
            "origin": origin,
            "destination": destination,
            "optimize_for": optimize_for,
            "nodes": [origin],
            "edges": [],
            "road_ids": [],
            "total_distance_m": 0.0,
            "estimated_travel_time_sec": 0.0,
            "at_risk_segments_count": 0,
            "uncertain_access_segments_count": 0,
            "uncertain_access_warnings": [],
            "route_safety_status": "SAFE_OPEN",
        }

    # Custom Dijkstra over graph adjacency to handle MultiDiGraph parallel edges cleanly
    dist_cost = {origin: 0.0}
    prev_step = {}  # node -> (prev_node, edge_key, edge_data, access_info)
    pq = [(0.0, str(origin), origin)]
    visited = set()

    while pq:
        cost_u, _, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)

        if u == destination:
            break

        for v in graph.neighbors(u):
            if v in visited:
                continue
            step_cost, key, data, acc = _select_best_parallel_edge(
                graph,
                u,
                v,
                optimize_for=optimize_for,
                allow_at_risk=allow_at_risk,
                allow_uncertain_access=allow_uncertain_access,
                penalized_edges=penalized_edges,
                penalty_factor=penalty_factor,
            )
            if step_cost is None:
                continue

            new_cost = cost_u + step_cost
            if new_cost < dist_cost.get(v, float("inf")):
                dist_cost[v] = new_cost
                prev_step[v] = (u, key, data, acc)
                heapq.heappush(pq, (new_cost, str(v), v))

    if destination not in prev_step:
        return {
            "reachable": False,
            "origin": origin,
            "destination": destination,
            "optimize_for": optimize_for,
            "nodes": [],
            "edges": [],
            "road_ids": [],
            "total_distance_m": None,
            "estimated_travel_time_sec": None,
            "at_risk_segments_count": 0,
            "uncertain_access_segments_count": 0,
            "uncertain_access_warnings": [],
            "route_safety_status": "NO_SAFE_ROUTE",
        }

    # Reconstruct path
    path_nodes = [destination]
    path_edges = []
    road_ids = []
    total_distance_m = 0.0
    total_time_sec = 0.0
    at_risk_count = 0
    uncertain_count = 0
    warnings = []

    curr = destination
    while curr != origin:
        u, key, data, acc = prev_step[curr]
        path_nodes.append(u)

        seg_len = float(data.get("length_m", data.get("length", 100.0)))
        seg_time = estimate_edge_travel_time_sec(data)
        road_id = str(data.get("road_id", f"{u}-{curr}"))
        cond = str(data.get("condition", "OPEN")).upper()

        total_distance_m += seg_len
        total_time_sec += seg_time
        road_ids.append(road_id)

        if cond == "AT RISK":
            at_risk_count += 1
        if acc["uncertain"]:
            uncertain_count += 1
            warnings.append(
                {
                    "from": u,
                    "to": curr,
                    "road_id": road_id,
                    "access_status": acc["status"],
                    "reason": acc["reason"],
                }
            )

        path_edges.append(
            {
                "u": u,
                "v": curr,
                "key": key,
                "road_id": road_id,
                "name": data.get("name", ""),
                "highway": data.get("highway", "unknown"),
                "length_m": round(seg_len, 2),
                "travel_time_sec": round(seg_time, 2),
                "condition": cond,
                "access_status": acc["status"],
                "access_uncertain": acc["uncertain"],
            }
        )
        curr = u

    path_nodes.reverse()
    path_edges.reverse()
    road_ids.reverse()
    warnings.reverse()

    if at_risk_count == 0 and uncertain_count == 0:
        safety_status = "SAFE_OPEN"
    elif at_risk_count > 0 and uncertain_count == 0:
        safety_status = "PASSABLE_WITH_AT_RISK_ROADS"
    elif at_risk_count == 0 and uncertain_count > 0:
        safety_status = "PASSABLE_WITH_UNCERTAIN_ACCESS"
    else:
        safety_status = "PASSABLE_WITH_AT_RISK_AND_UNCERTAIN_ACCESS"

    return {
        "reachable": True,
        "origin": origin,
        "destination": destination,
        "optimize_for": optimize_for,
        "nodes": path_nodes,
        "edges": path_edges,
        "road_ids": road_ids,
        "total_distance_m": round(total_distance_m, 2),
        "estimated_travel_time_sec": round(total_time_sec, 2),
        "at_risk_segments_count": at_risk_count,
        "uncertain_access_segments_count": uncertain_count,
        "uncertain_access_warnings": warnings,
        "route_safety_status": safety_status,
    }


def find_alternative_route(
    graph,
    origin,
    destination,
    primary_route=None,
    optimize_for="time",
    allow_at_risk=True,
    allow_uncertain_access=True,
    penalty_factor=3.5,
):
    """
    Generate an alternative safe rescue route between `origin` and `destination`
    by penalizing the edges traversed by the primary route.
    """

    if primary_route is None:
        primary_route = find_shortest_safe_route(
            graph,
            origin,
            destination,
            optimize_for=optimize_for,
            allow_at_risk=allow_at_risk,
            allow_uncertain_access=allow_uncertain_access,
        )

    if not primary_route.get("reachable") or len(primary_route.get("edges", [])) == 0:
        return {
            "primary_route": primary_route,
            "alternative_route": {
                "reachable": False,
                "origin": origin,
                "destination": destination,
                "nodes": [],
                "edges": [],
                "road_ids": [],
                "total_distance_m": None,
                "estimated_travel_time_sec": None,
                "is_distinct_from_primary": False,
                "edge_overlap_ratio": None,
            },
        }

    primary_edge_keys = {
        (e["u"], e["v"], e["key"]) for e in primary_route["edges"]
    }

    alt_route = find_shortest_safe_route(
        graph,
        origin,
        destination,
        optimize_for=optimize_for,
        allow_at_risk=allow_at_risk,
        allow_uncertain_access=allow_uncertain_access,
        penalized_edges=primary_edge_keys,
        penalty_factor=penalty_factor,
    )

    if alt_route["reachable"]:
        alt_edge_keys = {(e["u"], e["v"], e["key"]) for e in alt_route["edges"]}
        overlap = len(primary_edge_keys & alt_edge_keys) / max(1, len(primary_edge_keys))
        alt_route["edge_overlap_ratio"] = round(overlap, 4)
        alt_route["is_distinct_from_primary"] = alt_edge_keys != primary_edge_keys
    else:
        alt_route["edge_overlap_ratio"] = None
        alt_route["is_distinct_from_primary"] = False

    return {
        "primary_route": primary_route,
        "alternative_route": alt_route,
    }


def optimize_multi_destination_routes(
    graph,
    origin,
    destinations,
    optimize_for="time",
    allow_at_risk=True,
    allow_uncertain_access=True,
):
    """
    Compute optimal safe routes from `origin` to multiple emergency destinations
    simultaneously using a single-source Dijkstra pass (scalable to 437k nodes).
    """

    if optimize_for not in ("time", "distance"):
        raise ValueError("optimize_for must be either 'time' or 'distance'.")
    if origin not in graph:
        raise ValueError(f"Origin node '{origin}' not found in graph.")
    if not destinations:
        raise ValueError("destinations list cannot be empty.")

    target_set = set(destinations)
    remaining_targets = {d for d in target_set if d in graph and d != origin}

    dist_cost = {origin: 0.0}
    prev_step = {}
    pq = [(0.0, str(origin), origin)]
    visited = set()

    while pq and remaining_targets:
        cost_u, _, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)

        if u in remaining_targets:
            remaining_targets.remove(u)
            if not remaining_targets:
                break

        for v in graph.neighbors(u):
            if v in visited:
                continue
            step_cost, key, data, acc = _select_best_parallel_edge(
                graph,
                u,
                v,
                optimize_for=optimize_for,
                allow_at_risk=allow_at_risk,
                allow_uncertain_access=allow_uncertain_access,
            )
            if step_cost is None:
                continue

            new_cost = cost_u + step_cost
            if new_cost < dist_cost.get(v, float("inf")):
                dist_cost[v] = new_cost
                prev_step[v] = (u, key, data, acc)
                heapq.heappush(pq, (new_cost, str(v), v))

    results = {}
    for dest in destinations:
        if dest == origin:
            results[dest] = find_shortest_safe_route(
                graph, origin, dest, optimize_for=optimize_for
            )
        elif dest not in graph or dest not in prev_step:
            results[dest] = {
                "reachable": False,
                "origin": origin,
                "destination": dest,
                "optimize_for": optimize_for,
                "nodes": [],
                "edges": [],
                "road_ids": [],
                "total_distance_m": None,
                "estimated_travel_time_sec": None,
                "at_risk_segments_count": 0,
                "uncertain_access_segments_count": 0,
                "uncertain_access_warnings": [],
                "route_safety_status": "NO_SAFE_ROUTE",
            }
        else:
            # Reconstruct path for this destination
            path_nodes = [dest]
            path_edges = []
            road_ids = []
            total_distance_m = 0.0
            total_time_sec = 0.0
            at_risk_count = 0
            uncertain_count = 0
            warnings = []

            curr = dest
            while curr != origin:
                u, key, data, acc = prev_step[curr]
                path_nodes.append(u)
                seg_len = float(data.get("length_m", data.get("length", 100.0)))
                seg_time = estimate_edge_travel_time_sec(data)
                road_id = str(data.get("road_id", f"{u}-{curr}"))
                cond = str(data.get("condition", "OPEN")).upper()

                total_distance_m += seg_len
                total_time_sec += seg_time
                road_ids.append(road_id)
                if cond == "AT RISK":
                    at_risk_count += 1
                if acc["uncertain"]:
                    uncertain_count += 1
                    warnings.append(
                        {
                            "from": u,
                            "to": curr,
                            "road_id": road_id,
                            "access_status": acc["status"],
                            "reason": acc["reason"],
                        }
                    )
                path_edges.append(
                    {
                        "u": u,
                        "v": curr,
                        "key": key,
                        "road_id": road_id,
                        "length_m": round(seg_len, 2),
                        "travel_time_sec": round(seg_time, 2),
                        "condition": cond,
                        "access_status": acc["status"],
                    }
                )
                curr = u

            path_nodes.reverse()
            path_edges.reverse()
            road_ids.reverse()
            warnings.reverse()

            results[dest] = {
                "reachable": True,
                "origin": origin,
                "destination": dest,
                "optimize_for": optimize_for,
                "nodes": path_nodes,
                "edges": path_edges,
                "road_ids": road_ids,
                "total_distance_m": round(total_distance_m, 2),
                "estimated_travel_time_sec": round(total_time_sec, 2),
                "at_risk_segments_count": at_risk_count,
                "uncertain_access_segments_count": uncertain_count,
                "uncertain_access_warnings": warnings,
                "route_safety_status": (
                    "SAFE_OPEN"
                    if at_risk_count == 0 and uncertain_count == 0
                    else "PASSABLE_WITH_WARNINGS"
                ),
            }

    return {
        "origin": origin,
        "optimize_for": optimize_for,
        "destinations_count": len(destinations),
        "reachable_count": sum(1 for r in results.values() if r["reachable"]),
        "unreachable_count": sum(1 for r in results.values() if not r["reachable"]),
        "routes": results,
    }


# ==================================================
# PHASE 6: EMERGENCY RESOURCE ALLOCATION
# ==================================================

VALID_STRATEGIES = (
    "nearest_resource_first",
    "highest_priority_first",
    "budget_aware_optimized",
)


def allocate_emergency_resources(
    affected_locations,
    available_resources,
    total_budget=None,
    strategy="budget_aware_optimized",
):
    """
    Allocate emergency response resources across affected locations considering:
    - Priority of affected locations (`priority`)
    - Estimated affected population (`affected_population` / `demand`)
    - Distance and response time (`distance_m` or `distances_by_resource`)
    - Available resource units and per-unit capacity (`units`, `capacity_per_unit`)
    - Per-unit deployment cost and total budget constraint (`cost_per_unit`, `total_budget`)
    """

    if strategy not in VALID_STRATEGIES:
        raise ValueError(
            f"Unsupported strategy '{strategy}'. Choose from {VALID_STRATEGIES}."
        )

    if total_budget is not None and (
        not isinstance(total_budget, (int, float)) or total_budget < 0
    ):
        raise ValueError("total_budget must be a non-negative number or None.")

    if not isinstance(affected_locations, list) or not isinstance(available_resources, list):
        raise ValueError("affected_locations and available_resources must be lists.")

    # Normalize and validate locations
    loc_state = {}
    for loc in affected_locations:
        loc_id = str(loc["location_id"])
        priority = float(loc.get("priority", 1.0))
        demand = int(loc.get("affected_population", loc.get("demand", 0)))
        default_dist = float(loc.get("distance_m", 1000.0))

        if priority <= 0:
            raise ValueError(f"Location '{loc_id}' priority must be positive.")
        if demand < 0:
            raise ValueError(f"Location '{loc_id}' affected_population cannot be negative.")
        if default_dist < 0:
            raise ValueError(f"Location '{loc_id}' distance_m cannot be negative.")

        loc_state[loc_id] = {
            "location_id": loc_id,
            "name": loc.get("name", loc_id),
            "priority": priority,
            "initial_demand": demand,
            "remaining_demand": demand,
            "served_demand": 0,
            "default_distance_m": default_dist,
            "distances_by_resource": loc.get("distances_by_resource", {}),
            "is_synthetic_population": bool(loc.get("is_synthetic_population", True)),
        }

    # Normalize and validate resources
    res_state = {}
    total_units_available = 0
    for res in available_resources:
        res_id = str(res["resource_id"])
        units = int(res.get("units", res.get("available_units", 0)))
        cap = int(res.get("capacity_per_unit", res.get("capacity", 0)))
        cost = float(res.get("cost_per_unit", res.get("cost", 0.0)))
        speed_kmh = float(res.get("speed_kmh", 30.0))

        if units < 0:
            raise ValueError(f"Resource '{res_id}' units cannot be negative.")
        if cap <= 0:
            raise ValueError(f"Resource '{res_id}' capacity_per_unit must be positive.")
        if cost < 0:
            raise ValueError(f"Resource '{res_id}' cost_per_unit cannot be negative.")

        total_units_available += units
        res_state[res_id] = {
            "resource_id": res_id,
            "resource_type": res.get("resource_type", "general_rescue"),
            "initial_units": units,
            "remaining_units": units,
            "deployed_units": 0,
            "capacity_per_unit": cap,
            "cost_per_unit": cost,
            "speed_kmh": max(5.0, speed_kmh),
        }

    remaining_budget = float("inf") if total_budget is None else float(total_budget)
    budget_spent = 0.0
    allocations = []

    def _get_pair_distance(loc_obj, res_id):
        d = float(loc_obj["distances_by_resource"].get(res_id, loc_obj["default_distance_m"]))
        if d < 0:
            raise ValueError("Distance between resource and location cannot be negative.")
        return d

    # Iteratively assign 1 unit at a time (or batch of units for the best pair)
    while True:
        best_candidate = None
        best_sort_key = None

        for loc_id, loc_obj in loc_state.items():
            if loc_obj["remaining_demand"] <= 0:
                continue

            for res_id, res_obj in res_state.items():
                if res_obj["remaining_units"] <= 0:
                    continue
                if res_obj["cost_per_unit"] > remaining_budget:
                    continue

                dist_m = _get_pair_distance(loc_obj, res_id)
                eff_served = min(loc_obj["remaining_demand"], res_obj["capacity_per_unit"])
                if eff_served <= 0:
                    continue

                if strategy == "nearest_resource_first":
                    # Minimize distance first, tie-break by higher priority, then lower cost
                    sort_key = (-dist_m, loc_obj["priority"], -res_obj["cost_per_unit"])
                elif strategy == "highest_priority_first":
                    # Maximize priority first, then remaining demand, then closer resource
                    sort_key = (
                        loc_obj["priority"],
                        loc_obj["remaining_demand"],
                        -dist_m,
                        -res_obj["cost_per_unit"],
                    )
                else:  # "budget_aware_optimized"
                    # Maximize priority-weighted people served per unit of cost and distance penalty
                    dist_km = dist_m / 1000.0
                    cost_factor = max(1.0, res_obj["cost_per_unit"])
                    dist_penalty = 1.0 + 0.15 * dist_km
                    efficiency_score = (loc_obj["priority"] * eff_served) / (
                        cost_factor * dist_penalty
                    )
                    sort_key = (efficiency_score, loc_obj["priority"], -dist_m)

                if best_sort_key is None or sort_key > best_sort_key:
                    best_sort_key = sort_key
                    best_candidate = (loc_id, res_id, dist_m)

        if best_candidate is None:
            break

        loc_id, res_id, dist_m = best_candidate
        loc_obj = loc_state[loc_id]
        res_obj = res_state[res_id]

        # Deploy 1 unit in this step so multi-location trade-offs update dynamically
        units_to_deploy = 1
        pop_covered = min(
            loc_obj["remaining_demand"],
            units_to_deploy * res_obj["capacity_per_unit"],
        )
        step_cost = units_to_deploy * res_obj["cost_per_unit"]

        loc_obj["remaining_demand"] -= pop_covered
        loc_obj["served_demand"] += pop_covered
        res_obj["remaining_units"] -= units_to_deploy
        res_obj["deployed_units"] += units_to_deploy
        remaining_budget -= step_cost
        budget_spent += step_cost

        speed_ms = (res_obj["speed_kmh"] * 1000.0) / 3600.0
        travel_time_sec = dist_m / speed_ms

        # Merge with existing allocation record if same (loc_id, res_id)
        merged = False
        for rec in allocations:
            if rec["location_id"] == loc_id and rec["resource_id"] == res_id:
                rec["units_deployed"] += units_to_deploy
                rec["population_served"] += pop_covered
                rec["cost"] = round(rec["cost"] + step_cost, 2)
                merged = True
                break

        if not merged:
            allocations.append(
                {
                    "location_id": loc_id,
                    "location_name": loc_obj["name"],
                    "location_priority": loc_obj["priority"],
                    "resource_id": res_id,
                    "resource_type": res_obj["resource_type"],
                    "units_deployed": units_to_deploy,
                    "population_served": pop_covered,
                    "distance_m": round(dist_m, 2),
                    "estimated_response_time_sec": round(travel_time_sec, 2),
                    "cost": round(step_cost, 2),
                    "strategy_used": strategy,
                }
            )

    # Summarize per-location outcomes
    location_outcomes = []
    for loc_id, loc_obj in loc_state.items():
        init_d = loc_obj["initial_demand"]
        serv_d = loc_obj["served_demand"]
        unserv_d = loc_obj["remaining_demand"]
        if init_d == 0 or unserv_d == 0:
            status = "FULLY_SERVED"
        elif serv_d > 0:
            status = "PARTIALLY_SERVED"
        else:
            status = "UNSERVED"

        location_outcomes.append(
            {
                "location_id": loc_id,
                "name": loc_obj["name"],
                "priority": loc_obj["priority"],
                "initial_demand": init_d,
                "served_population": serv_d,
                "unserved_population": unserv_d,
                "coverage_pct": round((serv_d / init_d * 100.0) if init_d > 0 else 100.0, 2),
                "status": status,
                "is_synthetic_population": loc_obj["is_synthetic_population"],
            }
        )

    total_demand = sum(x["initial_demand"] for x in location_outcomes)
    total_served = sum(x["served_population"] for x in location_outcomes)
    total_unserved = sum(x["unserved_population"] for x in location_outcomes)
    total_units_deployed = sum(r["deployed_units"] for r in res_state.values())

    total_weighted_dist = sum(a["distance_m"] * a["units_deployed"] for a in allocations)
    total_weighted_time = sum(
        a["estimated_response_time_sec"] * a["units_deployed"] for a in allocations
    )

    metrics = {
        "strategy": strategy,
        "total_demand_population": total_demand,
        "total_served_population": total_served,
        "total_unserved_population": total_unserved,
        "population_coverage_pct": round(
            (total_served / total_demand * 100.0) if total_demand > 0 else 100.0, 2
        ),
        "locations_fully_served": sum(
            1 for x in location_outcomes if x["status"] == "FULLY_SERVED"
        ),
        "locations_partially_served": sum(
            1 for x in location_outcomes if x["status"] == "PARTIALLY_SERVED"
        ),
        "locations_unserved": sum(
            1 for x in location_outcomes if x["status"] == "UNSERVED"
        ),
        "total_response_distance_m": round(total_weighted_dist, 2),
        "average_response_distance_m": round(
            (total_weighted_dist / total_units_deployed) if total_units_deployed > 0 else 0.0,
            2,
        ),
        "average_response_time_sec": round(
            (total_weighted_time / total_units_deployed) if total_units_deployed > 0 else 0.0,
            2,
        ),
        "total_units_available": total_units_available,
        "total_units_deployed": total_units_deployed,
        "resource_utilization_pct": round(
            (total_units_deployed / total_units_available * 100.0)
            if total_units_available > 0
            else 0.0,
            2,
        ),
        "total_budget_available": total_budget,
        "total_budget_used": round(budget_spent, 2),
        "budget_utilization_pct": (
            round((budget_spent / total_budget * 100.0), 2)
            if total_budget is not None and total_budget > 0
            else None
        ),
    }

    return {
        "strategy": strategy,
        "allocations": allocations,
        "location_outcomes": location_outcomes,
        "resource_summary": list(res_state.values()),
        "metrics": metrics,
    }


# ==================================================
# PHASE 7: RESCUE STRATEGY COMPARISON
# ==================================================

def compare_rescue_strategies(
    affected_locations,
    available_resources,
    total_budget=None,
):
    """
    Execute and compare three distinct rescue resource allocation strategies:
    - Strategy A: `nearest_resource_first`
    - Strategy B: `highest_priority_first`
    - Strategy C: `budget_aware_optimized`
    """

    strategy_results = {}
    comparison_table = []

    for strat in VALID_STRATEGIES:
        res = allocate_emergency_resources(
            affected_locations=affected_locations,
            available_resources=available_resources,
            total_budget=total_budget,
            strategy=strat,
        )
        strategy_results[strat] = res
        m = res["metrics"]

        # Calculate priority-weighted population coverage for transparent comparison
        priority_weighted_served = sum(
            loc["priority"] * loc["served_population"]
            for loc in res["location_outcomes"]
        )

        row = {
            "strategy": strat,
            "served_population": m["total_served_population"],
            "unserved_population": m["total_unserved_population"],
            "population_coverage_pct": m["population_coverage_pct"],
            "priority_weighted_served": round(priority_weighted_served, 2),
            "total_response_distance_m": m["total_response_distance_m"],
            "average_response_distance_m": m["average_response_distance_m"],
            "average_response_time_sec": m["average_response_time_sec"],
            "total_units_deployed": m["total_units_deployed"],
            "resource_utilization_pct": m["resource_utilization_pct"],
            "total_budget_used": m["total_budget_used"],
            "budget_utilization_pct": m["budget_utilization_pct"],
        }
        comparison_table.append(row)

    # Select recommended strategy based on priority-weighted population served,
    # then total population coverage, then lower average response time
    best_row = max(
        comparison_table,
        key=lambda r: (
            r["priority_weighted_served"],
            r["population_coverage_pct"],
            -r["average_response_time_sec"],
        ),
    )

    return {
        "strategies": strategy_results,
        "comparison_summary": comparison_table,
        "recommended_strategy": best_row["strategy"],
        "recommendation_reason": (
            f"Strategy '{best_row['strategy']}' achieved the highest priority-weighted "
            f"population coverage ({best_row['priority_weighted_served']} priority-person units, "
            f"{best_row['population_coverage_pct']}% total demand covered) with an average "
            f"response time of {best_row['average_response_time_sec']}s."
        ),
    }


# ==================================================
# PHASE 8: ACTIVE OBSERVATION PLANNING
# ==================================================

def plan_active_observations(
    graph,
    top_k=10,
    critical_route_road_ids=None,
    facility_nodes=None,
    rainfall_intensity=None,
):
    """
    Identify which road segments should be inspected next to reduce decision
    uncertainty during a flood emergency.

    PROTOTYPE DISCLAIMER:
    This module is an explainable active-observation prioritization algorithm
    for field teams or road sensors. It does NOT control or deploy physical drones.
    """

    if top_k <= 0:
        raise ValueError("top_k must be a positive integer.")

    critical_roads_set = set(str(r) for r in (critical_route_road_ids or []))
    facility_nodes_set = set(facility_nodes or [])

    candidates_by_road_id = {}

    for u, v, data in graph.edges(data=True):
        road_id = str(data.get("road_id", f"{u}-{v}"))

        # 1. Flood vulnerability score
        if "vulnerability_score" in data:
            vuln_score = float(data["vulnerability_score"])
            uncertainty_attr = float(data.get("uncertainty_score", 0.5))
        elif "flood_sensitivity" in data:
            vuln_score = float(data["flood_sensitivity"])
            uncertainty_attr = float(data.get("uncertainty_score", 0.5))
        else:
            est = estimate_edge_vulnerability(data)
            vuln_score = est["vulnerability_score"]
            uncertainty_attr = est["uncertainty_score"]

        # 2. Threshold boundary uncertainty (how close the road is to flipping
        #    between OPEN/AT RISK (40) or AT RISK/BLOCKED (70))
        if "flood_impact" in data:
            impact = float(data["flood_impact"])
        elif rainfall_intensity is not None:
            impact = float(rainfall_intensity) * vuln_score
        else:
            impact = 60.0 * vuln_score

        dist_to_blocked = abs(impact - 70.0)
        dist_to_at_risk = abs(impact - 40.0)
        min_thresh_dist = min(dist_to_blocked, dist_to_at_risk)
        threshold_sensitivity = max(0.0, 1.0 - (min_thresh_dist / 25.0))

        access_info = evaluate_emergency_access(data)
        access_uncertainty = 0.25 if access_info["uncertain"] else 0.0

        combined_uncertainty = min(
            1.0,
            round(0.45 * uncertainty_attr + 0.35 * threshold_sensitivity + access_uncertainty, 4),
        )

        # 3. Network & Rescue Criticality
        highway = str(data.get("highway", "residential")).strip().lower()
        is_on_rescue_route = road_id in critical_roads_set
        is_near_facility = (u in facility_nodes_set) or (v in facility_nodes_set)
        is_tunnel = str(data.get("tunnel", "no")).lower() not in ("no", "unknown", "")
        is_bridge = str(data.get("bridge", "no")).lower() not in ("no", "unknown", "")

        criticality = 0.20
        reasons = []

        if is_on_rescue_route:
            criticality += 0.45
            reasons.append("Active primary/alternative emergency rescue route segment")
        if is_near_facility:
            criticality += 0.25
            reasons.append("Direct road access node for hospital/emergency facility")
        if highway in ("motorway", "trunk", "primary", "secondary"):
            criticality += 0.20
            reasons.append(f"Major arterial corridor ({highway})")
        elif highway == "tertiary":
            criticality += 0.10
        if is_tunnel:
            criticality += 0.20
            reasons.append("Underpass/tunnel choke point")
        elif is_bridge:
            criticality += 0.15
            reasons.append("Bridge river/rail crossing")

        criticality = min(1.0, round(criticality, 4))

        # 4. Would a new observation potentially change the recommended rescue strategy?
        would_change_strategy = bool(
            (is_on_rescue_route or is_near_facility or criticality >= 0.55)
            and (threshold_sensitivity >= 0.35 or vuln_score >= 0.50 or access_info["uncertain"])
        )
        strategy_change_bonus = 0.20 if would_change_strategy else 0.0

        if threshold_sensitivity >= 0.50:
            reasons.append(
                f"Impact score ({round(impact, 1)}) is near condition threshold (40/70)"
            )
        if access_info["uncertain"]:
            reasons.append(f"Uncertain emergency access ({access_info['reason']})")
        if vuln_score >= 0.65:
            reasons.append(f"High infrastructure flood vulnerability ({vuln_score})")

        priority_score = round(
            0.30 * vuln_score
            + 0.25 * combined_uncertainty
            + 0.25 * criticality
            + strategy_change_bonus,
            4,
        )

        record = {
            "road_id": road_id,
            "name": data.get("name", ""),
            "u": u,
            "v": v,
            "highway": highway,
            "condition": data.get("condition", "OPEN"),
            "observation_priority_score": priority_score,
            "vulnerability_score": round(vuln_score, 4),
            "uncertainty_score": combined_uncertainty,
            "criticality_score": criticality,
            "could_change_rescue_strategy": would_change_strategy,
            "inspection_reasons": reasons or ["Routine network monitoring"],
        }

        existing = candidates_by_road_id.get(road_id)
        if (
            existing is None
            or record["observation_priority_score"] > existing["observation_priority_score"]
        ):
            candidates_by_road_id[road_id] = record

    ranked = sorted(
        candidates_by_road_id.values(),
        key=lambda x: (
            x["could_change_rescue_strategy"],
            x["observation_priority_score"],
            x["criticality_score"],
            x["vulnerability_score"],
        ),
        reverse=True,
    )

    selected = ranked[:top_k]
    for idx, item in enumerate(selected, start=1):
        item["rank"] = idx

    return {
        "total_candidate_roads_evaluated": len(candidates_by_road_id),
        "recommended_observations_count": len(selected),
        "strategy_changing_candidates_count": sum(
            1 for r in selected if r["could_change_rescue_strategy"]
        ),
        "recommendations": selected,
        "prototype_disclaimer": (
            "Explainable active-observation prioritization prototype for field teams "
            "or road sensors. Does not represent autonomous drone deployment."
        ),
    }

