"""
sanjeevani/twin.py
------------------
Member 3 (Part A) Interface: Digital Twin & Future Disaster Scenario Simulation.
Simulates T+0 (Current), T+15 min, T+30 min, and T+60 min infrastructure conditions
using synthetic rainfall intensity (0-150 mm/hr), road vulnerability attributes,
and NetworkX connectivity evaluation.

NOTE: All projections are synthetic prototype calculations for decision-support
demonstration — not scientifically validated meteorological/hydrological forecasts.
"""

import networkx as nx
import numpy as np
import pandas as pd

from sanjeevani.data import (
    SYNTHETIC_JUNCTIONS,
    get_synthetic_roads,
)


HORIZONS_MINUTES = [0, 15, 30, 60]
HORIZON_LABELS = {
    0: "T+0 min (Current)",
    15: "T+15 min Projection",
    30: "T+30 min Projection",
    60: "T+60 min Projection",
}


def compute_projected_failure_prob(
    road: dict,
    rainfall_mm_hr: float,
    horizon_min: int,
    manual_failed_roads: set[str] | None = None,
) -> float:
    """
    Calculate synthetic projected road failure probability in [0.0, 1.0]
    based on road vulnerability score (0-100), rainfall intensity (0-150 mm/hr),
    and time horizon (0, 15, 30, 60 minutes).
    """
    manual_failed = manual_failed_roads or set()
    if road["road_id"] in manual_failed or road.get("is_manual_failure"):
        return 1.0

    vuln_norm = float(road["vulnerability_score"]) / 100.0
    rain_factor = float(np.clip(rainfall_mm_hr / 110.0, 0.0, 1.45))
    time_accumulation = 1.0 + 0.30 * (float(horizon_min) / 60.0)

    # Combine road's intrinsic vulnerability with rainfall accumulation over time
    raw_prob = (0.15 * vuln_norm) + (0.95 * (vuln_norm ** 0.80) * rain_factor * time_accumulation)

    # Ensure monotonic progression from scenario baseline when rainfall >= 55 mm/hr
    if rainfall_mm_hr >= 55 and road["status"] == "BLOCKED":
        raw_prob = max(raw_prob, road["failure_prob"])

    return float(np.clip(round(raw_prob, 2), 0.02, 0.99))


def classify_road_status(prob: float, is_manual_failure: bool = False) -> str:
    """Classify road availability status from synthetic failure probability."""
    if is_manual_failure or prob >= 0.72:
        return "BLOCKED"
    if prob >= 0.42:
        return "WARNING"
    return "SAFE"


def simulate_horizon_state(
    scenario_name: str,
    rainfall_mm_hr: float,
    horizon_min: int,
    manual_failed_roads: set[str] | None = None,
) -> dict:
    """
    Simulate the synthetic city road network and NetworkX connectivity at a specific
    future horizon (0, 15, 30, or 60 minutes) under a given rainfall intensity.
    """
    manual_failed = manual_failed_roads or set()
    base_roads = get_synthetic_roads(scenario_name, manual_failed_roads=manual_failed)

    projected_roads = []
    for r in base_roads:
        r_copy = dict(r)
        is_manual = r_copy["road_id"] in manual_failed
        proj_prob = compute_projected_failure_prob(
            r_copy,
            rainfall_mm_hr=rainfall_mm_hr,
            horizon_min=horizon_min,
            manual_failed_roads=manual_failed,
        )
        proj_status = classify_road_status(proj_prob, is_manual_failure=is_manual)
        r_copy["projected_prob"] = proj_prob
        r_copy["projected_status"] = proj_status
        r_copy["status"] = proj_status
        r_copy["failure_prob"] = proj_prob
        projected_roads.append(r_copy)

    # Build passable NetworkX graph for this horizon (excluding BLOCKED roads)
    G_horizon = nx.Graph()
    for j_id, attrs in SYNTHETIC_JUNCTIONS.items():
        G_horizon.add_node(j_id, **attrs)

    for r in projected_roads:
        if r["projected_status"] != "BLOCKED":
            penalty = 1.0 if r["projected_status"] == "SAFE" else 1.35
            G_horizon.add_edge(
                r["u"],
                r["v"],
                road_id=r["road_id"],
                name=r["name"],
                distance_km=r["distance_km"],
                effective_cost=round(r["distance_km"] * penalty, 2),
                risk=r["projected_prob"],
                status=r["projected_status"],
            )

    hospital_nodes = [
        j_id for j_id, attrs in SYNTHETIC_JUNCTIONS.items() if attrs["hospital_id"] is not None
    ]

    sector_rows = []
    connected_pop = 0
    isolated_pop = 0
    isolated_sectors = []

    for j_id, attrs in SYNTHETIC_JUNCTIONS.items():
        best_hosp = None
        best_dist = float("inf")
        best_corridor = []

        for h_node in hospital_nodes:
            if nx.has_path(G_horizon, j_id, h_node):
                dist = nx.shortest_path_length(G_horizon, j_id, h_node, weight="distance_km")
                if dist < best_dist:
                    best_dist = dist
                    best_hosp = SYNTHETIC_JUNCTIONS[h_node]["hospital_id"]
                    path_nodes = nx.shortest_path(G_horizon, j_id, h_node, weight="distance_km")
                    best_corridor = [
                        G_horizon.get_edge_data(path_nodes[i], path_nodes[i + 1])["road_id"]
                        for i in range(len(path_nodes) - 1)
                    ]

        if best_hosp is not None:
            connected_pop += attrs["population"]
            access_state = "ACCESSIBLE"
            corridor_str = "Direct (Hospital Hub)" if not best_corridor else " → ".join(best_corridor)
        else:
            isolated_pop += attrs["population"]
            isolated_sectors.append(f"{j_id} ({attrs['sector']})")
            access_state = "ISOLATED"
            corridor_str = "NO PASSABLE ROUTE"

        sector_rows.append(
            {
                "Junction": j_id,
                "Residential Sector": attrs["sector"],
                "Population": attrs["population"],
                "Projected Hospital Access": access_state,
                "Reachable Hospital": best_hosp or "NONE",
                "Distance (km)": round(best_dist, 2) if best_hosp else None,
                "Projected Safe Corridor": corridor_str,
            }
        )

    total_pop = connected_pop + isolated_pop
    access_pct = round((connected_pop / total_pop) * 100.0, 1) if total_pop > 0 else 0.0

    blocked_roads = [r["road_id"] for r in projected_roads if r["projected_status"] == "BLOCKED"]
    warning_roads = [r["road_id"] for r in projected_roads if r["projected_status"] == "WARNING"]
    safe_roads = [r["road_id"] for r in projected_roads if r["projected_status"] == "SAFE"]

    affected_pop = sum(
        r["population_impact"]
        for r in projected_roads
        if r["projected_status"] == "BLOCKED"
    )

    return {
        "horizon_min": horizon_min,
        "horizon_label": HORIZON_LABELS.get(horizon_min, f"T+{horizon_min} min"),
        "rainfall_mm_hr": rainfall_mm_hr,
        "roads": projected_roads,
        "graph": G_horizon,
        "sector_df": pd.DataFrame(sector_rows),
        "safe_count": len(safe_roads),
        "warning_count": len(warning_roads),
        "blocked_count": len(blocked_roads),
        "blocked_road_ids": blocked_roads,
        "warning_road_ids": warning_roads,
        "safe_road_ids": safe_roads,
        "hospital_access_pct": access_pct,
        "connected_population": connected_pop,
        "isolated_population": isolated_pop,
        "isolated_sectors": isolated_sectors,
        "affected_population_estimate": affected_pop,
        "connected_components": nx.number_connected_components(G_horizon),
    }


def simulate_all_horizons(
    scenario_name: str,
    rainfall_mm_hr: float,
    manual_failed_roads: set[str] | None = None,
) -> dict[int, dict]:
    """Run synthetic projections across all four horizons: T+0, T+15, T+30, and T+60."""
    results = {}
    for h in HORIZONS_MINUTES:
        results[h] = simulate_horizon_state(
            scenario_name=scenario_name,
            rainfall_mm_hr=rainfall_mm_hr,
            horizon_min=h,
            manual_failed_roads=manual_failed_roads,
        )
    return results


def build_horizon_comparison_df(all_horizons: dict[int, dict]) -> pd.DataFrame:
    """Build a summary table comparing T+0, T+15, T+30, and T+60 projections."""
    rows = []
    for h in HORIZONS_MINUTES:
        state = all_horizons[h]
        rows.append(
            {
                "Timeline Horizon": state["horizon_label"],
                "Safe Roads": state["safe_count"],
                "Warning Roads": state["warning_count"],
                "Blocked Roads": state["blocked_count"],
                "Projected Closures": ", ".join(state["blocked_road_ids"]) if state["blocked_road_ids"] else "None",
                "Hospital Access (%)": f"{state['hospital_access_pct']}%",
                "Isolated Population": state["isolated_population"],
                "Potentially Isolated Areas": ", ".join(state["isolated_sectors"]) if state["isolated_sectors"] else "None (All Connected)",
            }
        )
    return pd.DataFrame(rows)


def build_road_progression_df(all_horizons: dict[int, dict]) -> pd.DataFrame:
    """Build a road-by-road progression table across T+0, T+15, T+30, and T+60."""
    base_roads = all_horizons[0]["roads"]
    rows = []
    for idx, r0 in enumerate(base_roads):
        r15 = all_horizons[15]["roads"][idx]
        r30 = all_horizons[30]["roads"][idx]
        r60 = all_horizons[60]["roads"][idx]
        rows.append(
            {
                "Road ID": r0["road_id"],
                "Corridor Name": r0["name"],
                "Junctions": f"{r0['u']} ↔ {r0['v']}",
                "Vuln Score": r0["vulnerability_score"],
                "T+0 (Current)": f"{r0['projected_status']} ({int(r0['projected_prob']*100)}%)",
                "T+15 min": f"{r15['projected_status']} ({int(r15['projected_prob']*100)}%)",
                "T+30 min": f"{r30['projected_status']} ({int(r30['projected_prob']*100)}%)",
                "T+60 min": f"{r60['projected_status']} ({int(r60['projected_prob']*100)}%)",
            }
        )
    return pd.DataFrame(rows)


def get_cascading_impacts_and_observations(all_horizons: dict[int, dict]) -> dict:
    """
    Generate synthetic cascading infrastructure impacts and active observation
    recommendations based on projected T+30 and T+60 states.
    """
    state_30 = all_horizons[30]
    state_60 = all_horizons[60]
    rain = state_60["rainfall_mm_hr"]

    cascading_impacts = []
    observations = []

    if "RD-103" in state_30["blocked_road_ids"]:
        cascading_impacts.append(
            {
                "System": "Stormwater & Underpass Pumping (Sector 4)",
                "Trigger": "RD-103 submerged at T+15 / T+30",
                "Cascading Impact": "Sump pump overload increases local water table around J4 Lowland Junction, threatening RD-105 embankment.",
                "Severity": "CRITICAL",
            }
        )
        observations.append(
            {
                "Target": "RD-105 • South Valley Causeway Embankment",
                "Action": "Deploy drone / ultrasonic water-level sensor before T+15 to verify whether J4 retains southern evacuation access.",
                "Priority": "HIGH",
            }
        )

    if "RD-101" in state_30["blocked_road_ids"]:
        cascading_impacts.append(
            {
                "System": "Central Riverfront Feeder Substation",
                "Trigger": "RD-101 bridge deck flood threshold exceeded",
                "Cascading Impact": "Potential voltage sag at HOSP-01 Central Trauma; automatic switchover to hospital backup generators recommended.",
                "Severity": "CRITICAL" if rain >= 70 else "WARNING",
            }
        )
        observations.append(
            {
                "Target": "Substation #4 & HOSP-01 Generator Telemetry",
                "Action": "Request field verification of flood barrier seals at Central Riverfront (J2) within 10 minutes.",
                "Priority": "HIGH",
            }
        )

    if "RD-108" in state_60["blocked_road_ids"] or "RD-105" in state_60["blocked_road_ids"]:
        cascading_impacts.append(
            {
                "System": "Sector 4 Lowlands Medical Reachability",
                "Trigger": "Simultaneous closure risk on RD-103, RD-105, and RD-108 by T+60",
                "Cascading Impact": "8,400 residents in J4 risk complete road isolation from all 3 hospitals unless pre-positioned boat/ALS units are staged.",
                "Severity": "CRITICAL",
            }
        )
        observations.append(
            {
                "Target": "J1 ↔ J4 Service Link (RD-108)",
                "Action": "Station mobile spotter unit at West-South Service Link to monitor culvert clearance every 15 minutes.",
                "Priority": "CRITICAL",
            }
        )

    if not cascading_impacts:
        cascading_impacts.append(
            {
                "System": "Primary Urban Road & Hospital Grid",
                "Trigger": f"Low simulated rainfall ({rain} mm/hr)",
                "Cascading Impact": "No cascading substation or hospital isolation projected through T+60.",
                "Severity": "LOW",
            }
        )
        observations.append(
            {
                "Target": "RD-103 • Sector 4 Underpass Culvert",
                "Action": "Maintain routine 30-minute automated gauge polling; no emergency drone dispatch required.",
                "Priority": "NORMAL",
            }
        )

    return {
        "cascading_df": pd.DataFrame(cascading_impacts),
        "observations_df": pd.DataFrame(observations),
    }
