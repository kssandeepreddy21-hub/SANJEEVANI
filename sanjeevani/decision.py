"""
sanjeevani/decision.py
----------------------
Member 3 (Part B) Interface: Intelligent Rescue Route & Emergency Resource Allocation.
Uses NetworkX shortest-path algorithms to allocate available rescue units/ambulances
to emergency incidents and route evacuees to reachable hospitals while strictly
avoiding BLOCKED roads.

Compares three distinct strategies:
  - STRATEGY A (SHORTEST DISTANCE): Minimizes physical distance (km) over passable roads.
  - STRATEGY B (FASTEST RESPONSE): Minimizes estimated travel time (minutes) accounting for congestion/flooding speed reductions on WARNING roads.
  - STRATEGY C (RISK-AWARE RESPONSE): Minimizes vulnerability-weighted risk exposure while prioritizing CRITICAL verified incidents first.
"""

import networkx as nx
import pandas as pd

from sanjeevani.data import (
    SECTOR_TO_JUNCTION,
    SYNTHETIC_JUNCTIONS,
    get_synthetic_rescue_teams,
    get_synthetic_roads,
)


STRATEGY_DEFINITIONS = {
    "Strategy A – Shortest Distance": {
        "short_code": "STRATEGY A",
        "weight_attr": "distance_km",
        "description": "Prioritizes shortest physical route (km) across passable roads without penalizing flood-warning corridors.",
    },
    "Strategy B – Fastest Response": {
        "short_code": "STRATEGY B",
        "weight_attr": "travel_time_min",
        "description": "Prioritizes minimum estimated travel time (minutes), accounting for slower speeds (22 km/h) on WARNING roads vs. 42 km/h on SAFE highways.",
    },
    "Strategy C – Risk-Aware Response (SANJEEVANI)": {
        "short_code": "STRATEGY C",
        "weight_attr": "risk_aware_cost",
        "description": "Prioritizes CRITICAL verified emergencies first and penalizes high-vulnerability / flood-warning roads so ambulances avoid cascading road closures.",
    },
}


def get_strategy_names() -> list[str]:
    """Return the list of available rescue optimization strategies."""
    return list(STRATEGY_DEFINITIONS.keys())


def build_routing_graph(
    scenario_name: str,
    manual_failed_roads: set[str] | None = None,
) -> tuple[nx.Graph, list[dict]]:
    """
    Build a passable NetworkX routing graph storing:
      - distance_km (for Strategy A)
      - travel_time_min (for Strategy B)
      - risk_aware_cost (for Strategy C)
    Strictly excludes BLOCKED roads so no rescue unit is ever routed onto a closed road.
    """
    G = nx.Graph()
    for j_id, attrs in SYNTHETIC_JUNCTIONS.items():
        G.add_node(j_id, **attrs)

    roads = get_synthetic_roads(scenario_name, manual_failed_roads=manual_failed_roads)
    for r in roads:
        if r["status"] == "BLOCKED":
            # Never include blocked roads in rescue routing
            continue

        dist = float(r["distance_km"])
        # Speed model: SAFE roads = 42 km/h; WARNING roads = 20 km/h (flooded surface slowdowns)
        speed_kmh = 42.0 if r["status"] == "SAFE" else 20.0
        travel_time_min = round((dist / speed_kmh) * 60.0, 1)

        # Risk-aware cost heavily penalizes WARNING roads and high failure probability
        risk_multiplier = 1.0 + (2.4 * float(r["failure_prob"])) + (
            1.25 if r["status"] == "WARNING" else 0.0
        )
        risk_aware_cost = round(dist * risk_multiplier, 2)

        G.add_edge(
            r["u"],
            r["v"],
            road_id=r["road_id"],
            name=r["name"],
            coords=r["coords"],
            status=r["status"],
            distance_km=dist,
            travel_time_min=travel_time_min,
            risk_aware_cost=risk_aware_cost,
            failure_prob=float(r["failure_prob"]),
            vulnerability_score=r["vulnerability_score"],
        )

    return G, roads


def _compute_path_metrics(
    G: nx.Graph,
    source_node: str,
    target_node: str,
    weight_attr: str,
) -> dict:
    """Compute shortest path and aggregate distance, travel time, and risk along that path."""
    if not nx.has_path(G, source_node, target_node):
        return {
            "reachable": False,
            "nodes": [],
            "road_ids": [],
            "coords_list": [],
            "distance_km": None,
            "travel_time_min": None,
            "max_road_risk": None,
            "warning_edges_used": 0,
        }

    path_nodes = nx.shortest_path(G, source_node, target_node, weight=weight_attr)
    if len(path_nodes) == 1:
        # Already co-located at the same junction node
        j_lat = SYNTHETIC_JUNCTIONS[source_node]["lat"]
        j_lon = SYNTHETIC_JUNCTIONS[source_node]["lon"]
        return {
            "reachable": True,
            "nodes": path_nodes,
            "road_ids": ["Direct (Co-located Hub)"],
            "coords_list": [[[j_lat, j_lon], [j_lat, j_lon]]],
            "distance_km": 0.6,
            "travel_time_min": 1.2,
            "max_road_risk": 0.05,
            "warning_edges_used": 0,
        }

    road_ids = []
    coords_list = []
    total_dist = 0.0
    total_time = 0.0
    max_risk = 0.0
    warning_edges = 0

    for i in range(len(path_nodes) - 1):
        edge = G.get_edge_data(path_nodes[i], path_nodes[i + 1])
        road_ids.append(edge["road_id"])
        coords_list.append(edge["coords"])
        total_dist += float(edge["distance_km"])
        total_time += float(edge["travel_time_min"])
        max_risk = max(max_risk, float(edge["failure_prob"]))
        if edge["status"] == "WARNING":
            warning_edges += 1

    return {
        "reachable": True,
        "nodes": path_nodes,
        "road_ids": road_ids,
        "coords_list": coords_list,
        "distance_km": round(total_dist, 2),
        "travel_time_min": round(total_time, 1),
        "max_road_risk": round(max_risk, 2),
        "warning_edges_used": warning_edges,
    }


ALLOCATION_COLUMNS = [
    "Incident ID",
    "Urgency",
    "Sector (Node)",
    "Assigned Unit",
    "Dispatch Route (Unit → Incident)",
    "Evacuation Hospital",
    "Hospital Route (Incident → Hospital)",
    "Total Distance (km)",
    "Est. Response ETA (min)",
    "Route Status",
]


def allocate_rescue_resources(
    scenario_name: str,
    incidents_df: pd.DataFrame,
    strategy_name: str,
    manual_failed_roads: set[str] | None = None,
    units_df_override: pd.DataFrame | None = None,
) -> dict:
    """
    Allocate available rescue units to active incidents and compute full two-leg routes:
      Leg 1: Rescue Unit Junction -> Incident Junction
      Leg 2: Incident Junction -> Nearest Reachable Hospital Junction
    """
    G, roads = build_routing_graph(scenario_name, manual_failed_roads=manual_failed_roads)
    strategy_cfg = STRATEGY_DEFINITIONS.get(
        strategy_name,
        STRATEGY_DEFINITIONS["Strategy C – Risk-Aware Response (SANJEEVANI)"],
    )
    weight_attr = strategy_cfg["weight_attr"]

    units_df = (
        units_df_override.copy()
        if units_df_override is not None
        else get_synthetic_rescue_teams().copy()
    )

    if not units_df.empty and "assigned_sector" in units_df.columns:
        # Map each rescue unit to its home junction node
        units_df["junction"] = units_df["assigned_sector"].map(
            lambda s: SECTOR_TO_JUNCTION.get(s, "J2")
        )
        available_units = units_df.to_dict("records")
    else:
        available_units = []

    if incidents_df is None or incidents_df.empty:
        return {
            "strategy_name": strategy_name,
            "strategy_meta": strategy_cfg,
            "allocations_df": pd.DataFrame(columns=ALLOCATION_COLUMNS),
            "map_routes": [],
            "assigned_count": 0,
            "unreachable_count": 0,
            "avg_response_eta_min": 0.0,
            "avg_total_distance_km": 0.0,
            "warning_corridor_exposures": 0,
            "unit_utilization_pct": 0.0,
            "passable_edges_count": G.number_of_edges(),
            "total_edges_count": len(roads),
        }

    # Sort incidents according to strategy priority
    inc_df = incidents_df.copy()
    if "Risk-Aware" in strategy_name:
        # Prioritize verified CRITICAL incidents with highest confidence first
        inc_df["urg_rank"] = inc_df["urgency"].map(lambda u: 0 if u == "CRITICAL" else 1)
        inc_df["ver_rank"] = inc_df["verified"].map(lambda v: 0 if v else 1)
        inc_df = inc_df.sort_values(
            by=["ver_rank", "urg_rank", "confidence"],
            ascending=[True, True, False],
        )
    else:
        inc_df["urg_rank"] = inc_df["urgency"].map(lambda u: 0 if u == "CRITICAL" else 1)
        inc_df = inc_df.sort_values(by=["urg_rank", "incident_id"], ascending=[True, True])

    hospital_nodes = [
        j_id for j_id, attrs in SYNTHETIC_JUNCTIONS.items() if attrs["hospital_id"] is not None
    ]

    used_unit_ids: set[str] = set()

    allocations = []
    map_routes = []
    unreachable_count = 0
    assigned_count = 0
    total_eta_list = []
    total_dist_list = []
    warning_corridor_exposures = 0

    for _, inc in inc_df.iterrows():
        inc_id = inc["incident_id"]
        inc_sector = inc["sector"]
        inc_j = SECTOR_TO_JUNCTION.get(inc_sector, "J2")

        # Skip automatic dispatch for unverified duplicate-flagged reports under Strategy C
        if "Risk-Aware" in strategy_name and not bool(inc.get("verified", True)):
            allocations.append(
                {
                    "Incident ID": inc_id,
                    "Urgency": inc["urgency"],
                    "Sector (Node)": f"{inc_sector} ({inc_j})",
                    "Assigned Unit": "HOLD (Unverified Duplicate)",
                    "Dispatch Route (Unit → Incident)": "Awaiting Verification",
                    "Evacuation Hospital": "Pending",
                    "Hospital Route (Incident → Hospital)": "Pending",
                    "Total Distance (km)": None,
                    "Est. Response ETA (min)": None,
                    "Route Status": "⚠️ Verification Hold",
                }
            )
            continue

        # Find best reachable unit for Leg 1 (Unit -> Incident)
        best_unit = None
        best_leg1 = None
        best_score = float("inf")

        # Prefer unused units first; if all 4 units are busy, allow secondary queued dispatch
        candidate_pool = [u for u in available_units if u["unit_id"] not in used_unit_ids]
        is_queued = False
        if not candidate_pool:
            candidate_pool = available_units
            is_queued = True

        for u in candidate_pool:
            u_node = u["junction"]
            leg1 = _compute_path_metrics(G, u_node, inc_j, weight_attr=weight_attr)
            if leg1["reachable"]:
                score = (
                    leg1["distance_km"]
                    if weight_attr == "distance_km"
                    else (
                        leg1["travel_time_min"]
                        if weight_attr == "travel_time_min"
                        else leg1["distance_km"] * (1.0 + leg1["max_road_risk"])
                    )
                )
                if score < best_score:
                    best_score = score
                    best_unit = u
                    best_leg1 = leg1

        # Find best reachable hospital for Leg 2 (Incident -> Hospital)
        best_hosp_id = None
        best_leg2 = None
        best_h_score = float("inf")

        for h_node in hospital_nodes:
            leg2 = _compute_path_metrics(G, inc_j, h_node, weight_attr=weight_attr)
            if leg2["reachable"]:
                h_score = (
                    leg2["distance_km"]
                    if weight_attr == "distance_km"
                    else (
                        leg2["travel_time_min"]
                        if weight_attr == "travel_time_min"
                        else leg2["distance_km"] * (1.0 + leg2["max_road_risk"])
                    )
                )
                if h_score < best_h_score:
                    best_h_score = h_score
                    best_hosp_id = SYNTHETIC_JUNCTIONS[h_node]["hospital_id"]
                    best_leg2 = leg2

        if best_unit is None or best_leg1 is None or best_leg2 is None:
            unreachable_count += 1
            allocations.append(
                {
                    "Incident ID": inc_id,
                    "Urgency": inc["urgency"],
                    "Sector (Node)": f"{inc_sector} ({inc_j})",
                    "Assigned Unit": "NONE (Road Blocked)",
                    "Dispatch Route (Unit → Incident)": "UNREACHABLE — All Connecting Roads Blocked",
                    "Evacuation Hospital": "UNREACHABLE",
                    "Hospital Route (Incident → Hospital)": "NO PASSABLE CORRIDOR",
                    "Total Distance (km)": None,
                    "Est. Response ETA (min)": None,
                    "Route Status": "🚨 UNREACHABLE (Air/Boat Required)",
                }
            )
            continue

        used_unit_ids.add(best_unit["unit_id"])
        assigned_count += 1

        combined_dist = round(best_leg1["distance_km"] + best_leg2["distance_km"], 2)
        queue_delay = 4.5 if is_queued else 0.0
        response_eta = round(best_leg1["travel_time_min"] + queue_delay, 1)
        total_eta_list.append(response_eta)
        total_dist_list.append(combined_dist)
        warning_corridor_exposures += (
            best_leg1["warning_edges_used"] + best_leg2["warning_edges_used"]
        )

        leg1_str = " → ".join(best_leg1["road_ids"])
        leg2_str = " → ".join(best_leg2["road_ids"])
        unit_label = (
            f"{best_unit['unit_id']} (Queued)" if is_queued else best_unit["unit_id"]
        )

        allocations.append(
            {
                "Incident ID": inc_id,
                "Urgency": inc["urgency"],
                "Sector (Node)": f"{inc_sector} ({inc_j})",
                "Assigned Unit": unit_label,
                "Dispatch Route (Unit → Incident)": leg1_str,
                "Evacuation Hospital": best_hosp_id,
                "Hospital Route (Incident → Hospital)": leg2_str,
                "Total Distance (km)": combined_dist,
                "Est. Response ETA (min)": response_eta,
                "Route Status": "✅ Safe Route Active"
                if (best_leg1["warning_edges_used"] + best_leg2["warning_edges_used"]) == 0
                else "⚠️ Uses Flood-Warning Corridor",
            }
        )

        map_routes.append(
            {
                "incident_id": inc_id,
                "unit_id": best_unit["unit_id"],
                "hospital_id": best_hosp_id,
                "leg1_coords": best_leg1["coords_list"],
                "leg2_coords": best_leg2["coords_list"],
                "leg1_roads": leg1_str,
                "leg2_roads": leg2_str,
                "eta_min": response_eta,
            }
        )

    avg_eta = round(sum(total_eta_list) / len(total_eta_list), 1) if total_eta_list else 0.0
    avg_dist = round(sum(total_dist_list) / len(total_dist_list), 2) if total_dist_list else 0.0
    utilization_pct = round((len(used_unit_ids) / max(len(available_units), 1)) * 100.0, 1)

    return {
        "strategy_name": strategy_name,
        "strategy_meta": strategy_cfg,
        "allocations_df": pd.DataFrame(allocations),
        "map_routes": map_routes,
        "assigned_count": assigned_count,
        "unreachable_count": unreachable_count,
        "avg_response_eta_min": avg_eta,
        "avg_total_distance_km": avg_dist,
        "warning_corridor_exposures": warning_corridor_exposures,
        "unit_utilization_pct": utilization_pct,
        "passable_edges_count": G.number_of_edges(),
        "total_edges_count": len(roads),
    }


def compare_all_strategies(
    scenario_name: str,
    incidents_df: pd.DataFrame,
    manual_failed_roads: set[str] | None = None,
) -> pd.DataFrame:
    """Evaluate and compare Strategy A, Strategy B, and Strategy C side by side."""
    rows = []
    for s_name in get_strategy_names():
        res = allocate_rescue_resources(
            scenario_name=scenario_name,
            incidents_df=incidents_df,
            strategy_name=s_name,
            manual_failed_roads=manual_failed_roads,
        )
        rows.append(
            {
                "Strategy": s_name,
                "Optimization Objective": res["strategy_meta"]["weight_attr"],
                "Incidents Reached": res["assigned_count"],
                "Unreachable Incidents": res["unreachable_count"],
                "Avg Dispatch ETA (min)": res["avg_response_eta_min"],
                "Avg Mission Distance (km)": res["avg_total_distance_km"],
                "Flood-Warning Road Exposures": res["warning_corridor_exposures"],
                "Unit Utilisation (%)": f"{res['unit_utilization_pct']}%",
            }
        )
    return pd.DataFrame(rows)
