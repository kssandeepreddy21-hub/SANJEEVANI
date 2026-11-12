"""UI view-models, Plotly figures, and bounded Folium map helpers for Real Bengaluru OSM Mode."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import folium
import networkx as nx
import pandas as pd
import plotly.graph_objects as go

from sanjeevani.config import LOCAL_DATA_DIR, REPO_ROOT
from sanjeevani.decision_member3 import (
    allocate_emergency_resources,
    compare_rescue_strategies,
    find_alternative_route,
    find_shortest_safe_route,
    plan_active_observations,
)
from sanjeevani.flood_vulnerability import annotate_graph_vulnerability, summarize_graph_vulnerability
from sanjeevani.graph_adapter import remove_road, weak_component_summary
from sanjeevani.incident_bridge import incidents_to_affected_locations
from sanjeevani.twin_member3 import predict_future_scenarios, simulate_rainfall

SNAPSHOT_PATH: Path = LOCAL_DATA_DIR / "processed" / "member3_corridor_map_snapshot.json"

BENGALURU_CENTER: tuple[float, float] = (12.978, 77.594)
BENGALURU_LAT_BOUNDS: tuple[float, float] = (12.70, 13.30)
BENGALURU_LON_BOUNDS: tuple[float, float] = (77.30, 77.90)

MAX_ARTERIAL_OVERLAYS = 250
MAX_VULNERABLE_OVERLAYS = 250
MAX_FACILITY_OVERLAYS = 150
MAX_ROUTE_POINTS = 500

FACILITY_STYLE = {
    "hospitals": ("Hospital", "#3B82F6", "plus-sign"),
    "fire_stations": ("Fire Station", "#F97316", "fire"),
    "police_stations": ("Police Station", "#06B6D4", "shield"),
    "suitable_shelters": ("Emergency Shelter", "#10B981", "home"),
}


def _valid_bengaluru_coord(lat: Any, lon: Any) -> bool:
    try:
        la = float(lat)
        lo = float(lon)
    except (TypeError, ValueError):
        return False
    if not (math.isfinite(la) and math.isfinite(lo)):
        return False
    return (
        BENGALURU_LAT_BOUNDS[0] <= la <= BENGALURU_LAT_BOUNDS[1]
        and BENGALURU_LON_BOUNDS[0] <= lo <= BENGALURU_LON_BOUNDS[1]
    )


def load_corridor_snapshot(path: Path | str | None = None) -> dict[str, Any] | None:
    """Load the compact precomputed Central Bengaluru corridor geo-snapshot JSON if present."""
    target = Path(path) if path is not None else SNAPSHOT_PATH
    if not target.exists():
        return None
    with open(target, "r", encoding="utf-8") as f:
        return json.load(f)


def load_member1_artifacts(outputs_dir: Path | str | None = None) -> dict[str, Any]:
    """Inspect optional Member 1 16-node pipeline CSV/JSON/PNG artifacts under `outputs/`."""
    out_path = Path(outputs_dir) if outputs_dir is not None else (REPO_ROOT / "outputs")
    if not out_path.exists():
        return {"available": False, "path": str(out_path), "csv_files": {}, "png_files": [], "summary": None}

    csv_files: dict[str, pd.DataFrame] = {}
    for csv_path in sorted(out_path.glob("*.csv")):
        try:
            csv_files[csv_path.name] = pd.read_csv(csv_path)
        except Exception:
            continue

    summary = None
    for json_path in sorted(out_path.glob("*.json")):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                summary = json.load(f)
            break
        except Exception:
            continue

    png_files = [str(p) for p in sorted(out_path.glob("*.png"))]
    return {
        "available": bool(csv_files or png_files or summary),
        "path": str(out_path),
        "csv_files": csv_files,
        "png_files": png_files,
        "summary": summary,
    }


def get_osm_overview_kpis(payload: dict[str, Any]) -> list[dict[str, str]]:
    """Build 6 mission-control KPI card dictionaries for Real Bengaluru OSM Overview."""
    p1 = payload.get("phase1_network_validation", {})
    p2_corridor = payload.get("phase2_vulnerability", {}).get("central_corridor", {})
    p3_prog = payload.get("phase3_rainfall_simulation", {}).get("corridor_progression_scenarios", [])
    p4 = payload.get("phase4_cascading_and_facilities", {})
    p5 = payload.get("phase5_rescue_routing", {})
    p6 = payload.get("phase6_resource_allocation", {})

    t60 = p3_prog[-1] if p3_prog else {}
    t60_ways = t60.get("unique_road_way_counts", {})
    blocked_ways = int(t60_ways.get("BLOCKED", 0))
    at_risk_ways = int(t60_ways.get("AT RISK", 0))

    total_nodes = int(p1.get("total_nodes", 0))
    total_edges = int(p1.get("total_directed_edges", 0))
    corridor_nodes = int(p1.get("central_corridor_nodes", 0))

    avg_vuln = float(p2_corridor.get("average_way_vulnerability", 0.0))
    crit_ways = int(p2_corridor.get("way_risk_distribution", {}).get("CRITICAL", 0))

    city_fac = p4.get("facility_counts_citywide", {})
    hosp_count = int(city_fac.get("hospitals", {}).get("unique_facilities", 0))
    hosp_inacc = int(p4.get("facility_impact", {}).get("hospitals", {}).get("inaccessible_count", 0))

    primary = p5.get("primary_route", {})
    route_min = float(primary.get("estimated_travel_time_sec", 0.0)) / 60.0
    route_km = float(primary.get("total_distance_m", 0.0)) / 1000.0

    cov_pct = float(p6.get("metrics", {}).get("population_coverage_pct", 0.0))
    budget_used = float(p6.get("metrics", {}).get("total_budget_used", 0.0))
    budget_avail = float(p6.get("metrics", {}).get("total_budget_available", 0.0))

    return [
        {
            "label": "Bengaluru OSM Network",
            "value": f"{total_nodes:,}",
            "sub": f"{total_edges:,} directed edges | Corridor: {corridor_nodes:,} nodes",
            "color": "#38BDF8",
        },
        {
            "label": "T+60 Blocked Ways",
            "value": f"{blocked_ways}",
            "sub": f"{at_risk_ways:,} corridor ways AT RISK @ 95 mm/hr",
            "color": "#EF4444" if blocked_ways > 0 else "#22C55E",
        },
        {
            "label": "Corridor Vulnerability",
            "value": f"{avg_vuln:.3f}",
            "sub": f"{crit_ways} CRITICAL ways (Estimated from OSM Tags)",
            "color": "#F97316",
        },
        {
            "label": "OSM Hospitals (Unique)",
            "value": f"{hosp_count:,}",
            "sub": f"{hosp_inacc} corridor hospitals inaccessible @ T+60",
            "color": "#3B82F6",
        },
        {
            "label": "Primary Rescue Route",
            "value": f"{route_min:.1f} min",
            "sub": f"{route_km:.2f} km to K C General Hospital",
            "color": "#22C55E",
        },
        {
            "label": "Budget-Aware Coverage",
            "value": f"{cov_pct:.1f}%",
            "sub": f"₹{budget_used:,.0f} / ₹{budget_avail:,.0f} budget (Synthetic demand)",
            "color": "#A855F7",
        },
    ]


def get_vulnerability_summary_df(
    payload: dict[str, Any],
    scope: str = "central_corridor",
) -> pd.DataFrame:
    """Return vulnerability distribution DataFrame for `central_corridor` or `full_city`."""
    section = payload.get("phase2_vulnerability", {}).get(scope, {})
    edge_dist = section.get("edge_risk_distribution", {})
    way_dist = section.get("way_risk_distribution", {})
    rows = []
    for tier in ("CRITICAL", "HIGH", "MODERATE", "LOW"):
        rows.append(
            {
                "Risk Tier": tier,
                "Unique Road Ways": int(way_dist.get(tier, 0)),
                "Directed Edges": int(edge_dist.get(tier, 0)),
            }
        )
    return pd.DataFrame(rows)


def get_top_vulnerable_roads_df(
    snapshot: dict[str, Any] | None = None,
    live_graph: nx.Graph | None = None,
) -> pd.DataFrame:
    """Return top flood-vulnerable Bengaluru ways from live graph or precomputed snapshot."""
    if live_graph is not None and live_graph.number_of_edges() > 0:
        way_best: dict[str, dict[str, Any]] = {}
        for u, v, data in live_graph.edges(data=True):
            road_id = str(data.get("road_id", f"{u}-{v}"))
            vuln = float(data.get("vulnerability_score", data.get("flood_sensitivity", 0.0)))
            existing = way_best.get(road_id)
            if existing is None or vuln > existing["Vulnerability Score"]:
                way_best[road_id] = {
                    "Road ID": road_id,
                    "Road / Underpass": str(data.get("name", "") or "").strip() or f"OSM Way {road_id}",
                    "Highway": str(data.get("highway", "unknown")),
                    "Vulnerability Score": round(vuln, 4),
                    "Risk Category": str(data.get("risk_category", "MODERATE")),
                    "Condition": str(data.get("condition", "OPEN")),
                    "Tunnel / Underpass": str(data.get("tunnel", "no")).lower() not in ("no", "unknown", ""),
                    "Bridge": str(data.get("bridge", "no")).lower() not in ("no", "unknown", ""),
                    "Length (m)": round(float(data.get("length_m", 0.0)), 1),
                }
        rows = sorted(
            way_best.values(),
            key=lambda r: (r["Condition"] == "BLOCKED", r["Vulnerability Score"], r["Tunnel / Underpass"]),
            reverse=True,
        )[:25]
        return pd.DataFrame(rows)

    if snapshot and snapshot.get("top_vulnerable_roads"):
        rows = [
            {
                "Road ID": str(item.get("road_id", "")),
                "Road / Underpass": item.get("name") or f"OSM Way {item.get('road_id')}",
                "Highway": item.get("highway", "unknown"),
                "Vulnerability Score": item.get("vulnerability_score", 0.0),
                "Risk Category": item.get("risk_category", "MODERATE"),
                "Condition": item.get("t60_condition", "OPEN"),
                "Tunnel / Underpass": bool(item.get("is_tunnel", False)),
                "Bridge": bool(item.get("is_bridge", False)),
                "Length (m)": item.get("length_m", 0.0),
            }
            for item in snapshot["top_vulnerable_roads"]
        ]
        return pd.DataFrame(rows)

    return pd.DataFrame(
        columns=[
            "Road ID",
            "Road / Underpass",
            "Highway",
            "Vulnerability Score",
            "Risk Category",
            "Condition",
            "Tunnel / Underpass",
            "Bridge",
            "Length (m)",
        ]
    )


def get_corridor_progression_df(
    payload: dict[str, Any],
    live_scenarios: list[dict[str, Any]] | None = None,
) -> pd.DataFrame:
    """Build T+0..T+60 progression DataFrame from live simulation or precomputed payload."""
    source = (
        [
            {
                "time_minutes": item["time_minutes"],
                "rainfall_intensity": item["rainfall_intensity"],
                **item["summary"],
            }
            for item in live_scenarios
        ]
        if live_scenarios
        else payload.get("phase3_rainfall_simulation", {}).get("corridor_progression_scenarios", [])
    )

    rows = []
    for item in source:
        ways = item.get("unique_road_way_counts", {})
        edges = item.get("directed_edge_counts", {})
        kms = item.get("road_length_km", {})
        t_min = int(item.get("time_minutes", 0))
        rows.append(
            {
                "Horizon": f"T+{t_min} min",
                "Time (min)": t_min,
                "Rainfall (mm/hr)": float(item.get("rainfall_intensity", 0.0)),
                "Open Ways": int(ways.get("OPEN", 0)),
                "At-Risk Ways": int(ways.get("AT RISK", 0)),
                "Blocked Ways": int(ways.get("BLOCKED", 0)),
                "Blocked Edges": int(edges.get("BLOCKED", 0)),
                "Open Km": round(float(kms.get("OPEN", 0.0)), 2),
                "At-Risk Km": round(float(kms.get("AT RISK", 0.0)), 2),
                "Blocked Km": round(float(kms.get("BLOCKED", 0.0)), 2),
            }
        )
    return pd.DataFrame(rows)


def get_facility_counts_df(payload: dict[str, Any]) -> pd.DataFrame:
    """Return deduplicated citywide OSM facility inventory table."""
    fac = payload.get("phase4_cascading_and_facilities", {}).get("facility_counts_citywide", {})
    rows = []
    for cat, stats in fac.items():
        rows.append(
            {
                "Category": cat.replace("_", " ").title(),
                "Raw Nodes": int(stats.get("raw_nodes", 0)),
                "Raw Ways": int(stats.get("raw_ways", 0)),
                "Raw Relations": int(stats.get("raw_relations", 0)),
                "POI Duplicates Removed": int(stats.get("duplicate_poi_nodes_removed", 0)),
                "Unique Facilities": int(stats.get("unique_facilities", 0)),
                "Named": int(stats.get("named_facilities", 0)),
                "Verification": "Unverified OSM Record",
            }
        )
    return pd.DataFrame(rows)


def get_facility_impact_df(payload: dict[str, Any]) -> pd.DataFrame:
    """Return T+60 cascading road-failure accessibility impact across emergency facilities."""
    imp = payload.get("phase4_cascading_and_facilities", {}).get("facility_impact", {})
    rows = []
    for cat, stats in imp.items():
        rows.append(
            {
                "Category": cat.replace("_", " ").title(),
                "Evaluated (Corridor)": int(stats.get("total_evaluated", 0)),
                "Inaccessible": int(stats.get("inaccessible_count", 0)),
                "Delayed Access": int(stats.get("increased_travel_time_count", 0)),
                "Unaffected": int(stats.get("unaffected_count", 0)),
                "Verification": "Unverified OSM Record",
            }
        )
    return pd.DataFrame(rows)


def get_rescue_routes_df(
    payload: dict[str, Any],
    live_routing: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Return comparison DataFrame for Primary vs Alternative rescue route."""
    if live_routing:
        primary = live_routing.get("primary_route", {})
        alternative = live_routing.get("alternative_route", {})
    else:
        p5 = payload.get("phase5_rescue_routing", {})
        primary = p5.get("primary_route", {})
        alternative = p5.get("alternative_route", {})

    rows = []
    for label, route in (("Primary Safe Route", primary), ("Alternative Detour Route", alternative)):
        if not route:
            continue
        dist_m = float(route.get("total_distance_m", 0.0)) if route.get("reachable") else 0.0
        time_s = float(route.get("estimated_travel_time_sec", 0.0)) if route.get("reachable") else 0.0
        rows.append(
            {
                "Route": label,
                "Reachable": bool(route.get("reachable", False)),
                "Distance (km)": round(dist_m / 1000.0, 2),
                "Est. Time (min)": round(time_s / 60.0, 2),
                "Segments": int(route.get("segment_count", len(route.get("road_ids", [])))),
                "At-Risk Segments": int(route.get("at_risk_segments_count", 0)),
                "Uncertain Access": int(route.get("uncertain_access_segments_count", 0)),
                "Safety Status": str(route.get("route_safety_status", "UNKNOWN")),
                "Overlap Ratio": route.get("edge_overlap_ratio", "—"),
            }
        )
    return pd.DataFrame(rows)


def get_active_observations_df(
    payload: dict[str, Any],
    live_observations: list[dict[str, Any]] | None = None,
) -> pd.DataFrame:
    """Return Phase 8 Active Observation Priorities DataFrame."""
    recs = (
        live_observations
        if live_observations is not None
        else payload.get("phase8_active_observation_plan", {}).get("recommendations", [])
    )
    rows = []
    for rec in recs:
        reasons = rec.get("inspection_reasons", [])
        rows.append(
            {
                "Rank": int(rec.get("rank", 0)),
                "Road ID": str(rec.get("road_id", "")),
                "Corridor / Underpass": str(rec.get("name", "") or "").strip() or f"OSM Way {rec.get('road_id')}",
                "Highway": str(rec.get("highway", "unknown")),
                "Condition": str(rec.get("condition", "AT RISK")),
                "Priority Score": round(float(rec.get("observation_priority_score", 0.0)), 4),
                "Vulnerability": round(float(rec.get("vulnerability_score", 0.0)), 2),
                "Uncertainty": round(float(rec.get("uncertainty_score", 0.0)), 3),
                "Changes Strategy?": bool(rec.get("could_change_rescue_strategy", False)),
                "Key Reason": reasons[0] if reasons else "Inspect segment state",
            }
        )
    return pd.DataFrame(rows)


def get_strategy_comparison_df(
    payload: dict[str, Any],
    live_comparison: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Return Phase 7 Rescue Strategy comparison DataFrame."""
    summary = (
        live_comparison.get("comparison_summary", [])
        if live_comparison
        else payload.get("phase7_strategy_comparison", {}).get("comparison_summary", [])
    )
    rows = []
    for item in summary:
        rows.append(
            {
                "Strategy": str(item.get("strategy", "")),
                "Served Pop (Synth)": int(item.get("served_population", 0)),
                "Unserved Pop (Synth)": int(item.get("unserved_population", 0)),
                "Coverage (%)": round(float(item.get("population_coverage_pct", 0.0)), 2),
                "Priority-Weighted": round(float(item.get("priority_weighted_served", 0.0)), 1),
                "Avg Response (min)": round(float(item.get("average_response_time_sec", 0.0)) / 60.0, 2),
                "Units Deployed": int(item.get("total_units_deployed", 0)),
                "Budget Used (₹)": round(float(item.get("total_budget_used", 0.0)), 0),
                "Budget Util (%)": round(float(item.get("budget_utilization_pct", 0.0)), 2),
            }
        )
    return pd.DataFrame(rows)


def get_allocations_df(
    payload: dict[str, Any],
    live_allocation: dict[str, Any] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return `(allocations_df, location_outcomes_df)` from live run or precomputed payload."""
    src = live_allocation if live_allocation else payload.get("phase6_resource_allocation", {})
    alloc_rows = [
        {
            "Location ID": a.get("location_id"),
            "Target Zone": a.get("location_name"),
            "Priority": a.get("location_priority"),
            "Resource": a.get("resource_id"),
            "Units": a.get("units_deployed"),
            "Served (Synth)": a.get("population_served"),
            "Distance (m)": a.get("distance_m"),
            "Est. ETA (min)": round(float(a.get("estimated_response_time_sec", 0.0)) / 60.0, 2),
            "Cost (₹)": a.get("cost"),
        }
        for a in src.get("allocations", [])
    ]
    loc_rows = [
        {
            "Location ID": loc.get("location_id"),
            "Zone / Hospital Catchment": loc.get("name"),
            "Priority": loc.get("priority"),
            "Synthetic Demand": loc.get("initial_demand"),
            "Served": loc.get("served_population"),
            "Unserved": loc.get("unserved_population"),
            "Coverage (%)": loc.get("coverage_pct"),
            "Status": loc.get("status"),
            "Population Source": "Synthetic Scenario" if loc.get("is_synthetic_population", True) else "Observed",
        }
        for loc in src.get("location_outcomes", [])
    ]
    return pd.DataFrame(alloc_rows), pd.DataFrame(loc_rows)


def snap_emergency_reports_to_corridor(
    incidents_df: pd.DataFrame,
    corridor_graph: nx.Graph | None = None,
    snapshot: dict[str, Any] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Map Member 2 incident reports onto Bengaluru OSM nodes via `incident_bridge`
    when `corridor_graph` is loaded, or preview against snapshot anchor nodes offline.
    """
    if corridor_graph is not None and corridor_graph.number_of_nodes() > 0:
        bridged = incidents_to_affected_locations(incidents_df, corridor_graph, require_verified=True)
        status_by_id: dict[str, dict[str, Any]] = {}
        for item in bridged["affected_locations"]:
            status_by_id[str(item["location_id"])] = {
                "osm_node": str(item["node"]),
                "snap_distance_m": item["snap_distance_m"],
                "queue_state": "READY FOR DISPATCH",
            }
        for item in bridged["held_incidents"]:
            status_by_id[str(item["incident_id"])] = {
                "osm_node": str(item["node"]) if item["node"] is not None else "—",
                "snap_distance_m": item["snap_distance_m"],
                "queue_state": f"HELD ({item['hold_reason']})",
            }
        for item in bridged["unmapped_incidents"]:
            status_by_id[str(item["incident_id"])] = {
                "osm_node": "—",
                "snap_distance_m": None,
                "queue_state": "UNMAPPED",
            }

        enriched = incidents_df.copy()
        enriched["OSM Node"] = enriched["incident_id"].astype(str).map(
            lambda iid: status_by_id.get(iid, {}).get("osm_node", "—")
        )
        enriched["Snap (m)"] = enriched["incident_id"].astype(str).map(
            lambda iid: status_by_id.get(iid, {}).get("snap_distance_m")
        )
        enriched["OSM Dispatch Queue"] = enriched["incident_id"].astype(str).map(
            lambda iid: status_by_id.get(iid, {}).get("queue_state", "PENDING")
        )
        return enriched, bridged

    # Offline snapshot preview: check hold/dispatch rules + show snapshot proximity
    enriched = incidents_df.copy()
    anchors = snapshot.get("facilities", []) if snapshot else []
    anchor_nodes: list[str] = []
    for _, row in enriched.iterrows():
        dup = "FLAGGED" in str(row.get("duplicate_warning", "")).upper()
        ver = bool(row.get("verified", False))
        if not ver:
            anchor_nodes.append("HELD (Pending operator verification)")
        elif dup:
            anchor_nodes.append("HELD (Duplicate/recycled evidence warning)")
        else:
            anchor_nodes.append("VERIFIED (Load RESQ_AI_DATA_DIR for exact OSM node snap)")
    enriched["OSM Node"] = [
        anchors[0]["nearest_node"] if (anchors and "VERIFIED" in q) else "Corridor Preview"
        for q in anchor_nodes
    ]
    enriched["Snap (m)"] = None
    enriched["OSM Dispatch Queue"] = anchor_nodes
    return enriched, {"affected_locations": [], "held_incidents": [], "unmapped_incidents": []}


def run_live_corridor_rainfall(
    corridor_graph: nx.MultiDiGraph,
    current_rainfall: float,
    increase_per_15_min: float = 10.0,
) -> dict[str, Any]:
    """Execute live corridor vulnerability annotation + T+0..T+60 rainfall progression."""
    vuln_graph = annotate_graph_vulnerability(corridor_graph)
    vuln_summary = summarize_graph_vulnerability(vuln_graph)
    scenarios = predict_future_scenarios(
        vuln_graph,
        current_rainfall=float(current_rainfall),
        increase_per_15_min=float(increase_per_15_min),
    )
    return {
        "vulnerability_summary": vuln_summary,
        "scenarios": scenarios,
        "latest_graph": scenarios[-1]["updated_graph"] if scenarios else vuln_graph,
    }


def _extract_route_coords(graph: nx.Graph, nodes: list[Any], limit: int = MAX_ROUTE_POINTS) -> list[list[float]]:
    coords: list[list[float]] = []
    for nid in nodes:
        if nid not in graph:
            continue
        nd = graph.nodes[nid]
        lat = nd.get("y", nd.get("lat"))
        lon = nd.get("x", nd.get("lon"))
        if _valid_bengaluru_coord(lat, lon):
            coords.append([round(float(lat), 6), round(float(lon), 6)])
    if len(coords) > limit:
        step = max(1, len(coords) // limit)
        last_pt = coords[-1]
        coords = coords[::step]
        if coords and coords[-1] != last_pt:
            coords.append(last_pt)
    return coords


def run_live_corridor_routing(
    corridor_graph: nx.MultiDiGraph,
    origin_node: Any,
    destination_node: Any,
    rainfall_intensity: float = 95.0,
    optimize_for: str = "time",
    failed_road_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Compute live rescue routes, detour, component connectivity, and active observations."""
    vuln_graph = annotate_graph_vulnerability(corridor_graph)
    sim_graph, _ = simulate_rainfall(vuln_graph, float(rainfall_intensity))

    work_graph = sim_graph
    for rid in failed_road_ids or []:
        work_graph = remove_road(work_graph, rid, inplace=False)

    baseline_comp = weak_component_summary(corridor_graph)
    post_comp = weak_component_summary(work_graph)

    primary = find_shortest_safe_route(
        work_graph,
        origin_node,
        destination_node,
        optimize_for=optimize_for,
    )
    alt_bundle = find_alternative_route(
        work_graph,
        origin_node,
        destination_node,
        primary_route=primary if primary.get("reachable") else None,
        optimize_for=optimize_for,
    )
    alternative = alt_bundle.get("alternative_route", {})

    primary_coords = _extract_route_coords(work_graph, primary.get("nodes", []))
    alt_coords = _extract_route_coords(work_graph, alternative.get("nodes", []))

    critical_road_ids = list(dict.fromkeys(primary.get("road_ids", []) + alternative.get("road_ids", [])))
    obs_plan = plan_active_observations(
        work_graph,
        top_k=8,
        critical_route_road_ids=critical_road_ids,
        facility_nodes=[destination_node],
        rainfall_intensity=float(rainfall_intensity),
    )

    return {
        "primary_route": primary,
        "alternative_route": alternative,
        "primary_coords": primary_coords,
        "alternative_coords": alt_coords,
        "observations": obs_plan.get("recommendations", []),
        "baseline_connectivity": baseline_comp,
        "post_connectivity": post_comp,
        "work_graph": work_graph,
    }


def run_live_corridor_allocation(
    corridor_graph: nx.MultiDiGraph,
    incidents_df: pd.DataFrame,
    strategy: str = "budget_aware_optimized",
    total_budget: float = 3200.0,
) -> dict[str, Any]:
    """
    Feed verified Member 2 reports snapped via `incident_bridge` into Member 3's
    `allocate_emergency_resources` & `compare_rescue_strategies`.
    """
    bridged = incidents_to_affected_locations(incidents_df, corridor_graph, require_verified=True)
    affected = bridged["affected_locations"]
    if not affected:
        return {
            "bridged": bridged,
            "allocation": None,
            "comparison": None,
            "message": "No verified, non-duplicate incidents available for corridor dispatch.",
        }

    # Build clean resource units using corridor sample coordinates & shortest distances
    node_list = list(corridor_graph.nodes())
    hub_a = node_list[0]
    hub_b = node_list[len(node_list) // 2]

    # Precompute lightweight shortest distances from hubs on a copy (no all-pairs!)
    dist_a = nx.single_source_dijkstra_path_length(corridor_graph, hub_a, weight="length_m")
    dist_b = nx.single_source_dijkstra_path_length(corridor_graph, hub_b, weight="length_m")
    for loc in affected:
        nid = loc["node"]
        d1 = float(dist_a.get(nid, 3500.0))
        d2 = float(dist_b.get(nid, 4200.0))
        loc["distance_m"] = round(min(d1, d2), 2)

    resources = [
        {
            "resource_id": "RESQ_ALS_CORRIDOR",
            "resource_type": "advanced_life_support_ambulance",
            "units_available": 4,
            "capacity_per_unit": 150,
            "cost_per_unit": 450.0,
            "speed_kmh": 32.0,
        },
        {
            "resource_id": "RESQ_BOAT_CORRIDOR",
            "resource_type": "inflatable_flood_rescue_boat",
            "units_available": 3,
            "capacity_per_unit": 220,
            "cost_per_unit": 650.0,
            "speed_kmh": 20.0,
        },
        {
            "resource_id": "RESQ_MED_VAN",
            "resource_type": "rapid_medical_unit",
            "units_available": 4,
            "capacity_per_unit": 120,
            "cost_per_unit": 250.0,
            "speed_kmh": 35.0,
        },
    ]

    allocation = allocate_emergency_resources(
        affected,
        resources,
        total_budget=float(total_budget),
        strategy=strategy,
    )
    comparison = compare_rescue_strategies(
        affected,
        resources,
        total_budget=float(total_budget),
    )
    return {
        "bridged": bridged,
        "allocation": allocation,
        "comparison": comparison,
        "message": "Live corridor optimization completed.",
    }


# ---------------------------------------------------------------------------
# PLOTLY CHARTS (DARK NAVY EOC THEME)
# ---------------------------------------------------------------------------

def _apply_eoc_layout(fig: go.Figure, title: str, height: int = 330) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#F8FAFC")),
        paper_bgcolor="#111C33",
        plot_bgcolor="#111C33",
        font=dict(color="#CBD5E1", size=12),
        margin=dict(l=20, r=20, t=48, b=36),
        height=height,
    )
    return fig


def build_vulnerability_distribution_chart(
    payload: dict[str, Any],
    scope: str = "central_corridor",
) -> go.Figure:
    df = get_vulnerability_summary_df(payload, scope=scope)
    colors = {"CRITICAL": "#EF4444", "HIGH": "#F97316", "MODERATE": "#EAB308", "LOW": "#22C55E"}
    fig = go.Figure(
        data=[
            go.Bar(
                x=df["Risk Tier"],
                y=df["Unique Road Ways"],
                marker_color=[colors.get(t, "#38BDF8") for t in df["Risk Tier"]],
                text=[f"{v:,}" for v in df["Unique Road Ways"]],
                textposition="auto",
            )
        ]
    )
    label = "Central Corridor (9,521 Ways)" if scope == "central_corridor" else "Full City (135,302 Ways)"
    fig.update_xaxes(title="Estimated Flood Risk Tier")
    fig.update_yaxes(title="Unique OSM Road Ways", gridcolor="#1E293B")
    return _apply_eoc_layout(fig, f"OSM Tag-Based Flood Vulnerability — {label}")


def build_corridor_rainfall_progression_chart(prog_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if prog_df.empty:
        return _apply_eoc_layout(fig, "Rainfall Progression (No Data)")

    for col, color in (
        ("Open Ways", "#22C55E"),
        ("At-Risk Ways", "#F97316"),
        ("Blocked Ways", "#EF4444"),
    ):
        fig.add_trace(
            go.Bar(
                name=col,
                x=prog_df["Horizon"],
                y=prog_df[col],
                marker_color=color,
                text=prog_df[col],
                textposition="auto",
            )
        )
    fig.update_layout(barmode="group", legend=dict(orientation="h", yanchor="bottom", y=1.02))
    fig.update_yaxes(title="Unique Corridor Road Ways", gridcolor="#1E293B")
    return _apply_eoc_layout(fig, "Hypothetical Corridor Progression (T+0 to T+60)")


def build_facility_impact_chart(impact_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if impact_df.empty:
        return _apply_eoc_layout(fig, "Facility Accessibility Impact")
    for col, color in (
        ("Unaffected", "#22C55E"),
        ("Delayed Access", "#F97316"),
        ("Inaccessible", "#EF4444"),
    ):
        fig.add_trace(
            go.Bar(
                name=col,
                x=impact_df["Category"],
                y=impact_df[col],
                marker_color=color,
                text=impact_df[col],
                textposition="auto",
            )
        )
    fig.update_layout(barmode="stack", legend=dict(orientation="h", yanchor="bottom", y=1.02))
    fig.update_yaxes(title="Corridor OSM Facilities", gridcolor="#1E293B")
    return _apply_eoc_layout(fig, "Post-Failure Emergency Facility Reachability (Unverified OSM)")


def build_osm_strategy_comparison_chart(comp_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if comp_df.empty:
        return _apply_eoc_layout(fig, "Strategy Comparison")
    fig.add_trace(
        go.Bar(
            name="Population Coverage (%)",
            x=comp_df["Strategy"],
            y=comp_df["Coverage (%)"],
            marker_color="#38BDF8",
            text=[f"{v:.1f}%" for v in comp_df["Coverage (%)"]],
            textposition="auto",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Avg Response (min)",
            x=comp_df["Strategy"],
            y=comp_df["Avg Response (min)"],
            marker_color="#A855F7",
            text=[f"{v:.1f}m" for v in comp_df["Avg Response (min)"]],
            textposition="auto",
        )
    )
    fig.update_layout(barmode="group", legend=dict(orientation="h", yanchor="bottom", y=1.02))
    fig.update_yaxes(gridcolor="#1E293B")
    return _apply_eoc_layout(fig, "Bengaluru Rescue Strategy Trade-off (Synthetic Demand)")


# ---------------------------------------------------------------------------
# BOUNDED FOLIUM BENGALURU MAP BUILDER
# ---------------------------------------------------------------------------

def build_bengaluru_osm_map(
    payload: dict[str, Any],
    snapshot: dict[str, Any] | None = None,
    *,
    tile_layer: str = "OpenStreetMap",
    focus: str = "overview",
    live_primary_coords: list[list[float]] | None = None,
    live_alt_coords: list[list[float]] | None = None,
    incidents_df: pd.DataFrame | None = None,
    max_arterial: int = MAX_ARTERIAL_OVERLAYS,
    max_vulnerable: int = MAX_VULNERABLE_OVERLAYS,
    max_facilities: int = MAX_FACILITY_OVERLAYS,
) -> folium.Map:
    """
    Build a smooth, size-bounded interactive Folium map over Central Bengaluru.
    Never accepts or iterates the 437k-node full graph directly.
    """
    safe_tile = "OpenStreetMap" if tile_layer not in ("OpenStreetMap", "CartoDB positron") else tile_layer
    m = folium.Map(
        location=list(BENGALURU_CENTER),
        zoom_start=13,
        tiles=safe_tile,
        control_scale=True,
    )

    stats = {
        "arterial_polylines": 0,
        "vulnerable_polylines": 0,
        "facility_markers": 0,
        "route_polylines": 0,
        "observation_markers": 0,
        "incident_markers": 0,
    }

    if snapshot:
        # 1. Arterial Corridor Backbone
        if focus in ("overview", "vulnerability", "rainfall"):
            fg_art = folium.FeatureGroup(name="Bengaluru Arterial Backbone", show=True)
            for seg in snapshot.get("arterial_segments", [])[:max_arterial]:
                coords = seg.get("coords", [])
                if len(coords) == 2 and all(_valid_bengaluru_coord(p[0], p[1]) for p in coords):
                    folium.PolyLine(
                        locations=coords,
                        color="#38BDF8",
                        weight=2.2,
                        opacity=0.55,
                        tooltip=f"{seg.get('name') or seg.get('road_id')} ({seg.get('highway')})",
                    ).add_to(fg_art)
                    stats["arterial_polylines"] += 1
            fg_art.add_to(m)

        # 2. Flood-Vulnerable / Blocked / At-Risk Corridors
        fg_vuln = folium.FeatureGroup(name="Flood Risk & T+60 Blocked Roads", show=True)
        for seg in snapshot.get("vulnerable_segments", [])[:max_vulnerable]:
            coords = seg.get("coords", [])
            if len(coords) != 2 or not all(_valid_bengaluru_coord(p[0], p[1]) for p in coords):
                continue
            cond = str(seg.get("condition", "OPEN"))
            color = "#EF4444" if cond == "BLOCKED" else ("#F97316" if cond == "AT RISK" else "#EAB308")
            weight = 5.0 if cond == "BLOCKED" else 3.2
            label = seg.get("name") or f"OSM Way {seg.get('road_id')}"
            folium.PolyLine(
                locations=coords,
                color=color,
                weight=weight,
                opacity=0.88,
                tooltip=(
                    f"{label} | Condition: {cond} | Est. Vuln: {seg.get('vulnerability')} "
                    f"({seg.get('risk_category')})"
                ),
            ).add_to(fg_vuln)
            stats["vulnerable_polylines"] += 1
        fg_vuln.add_to(m)

        # 3. Deduplicated Central Corridor OSM Facilities
        fg_fac = folium.FeatureGroup(
            name="OSM Emergency Facilities (Unverified)",
            show=(focus in ("overview", "facilities", "routing")),
        )
        for fac in snapshot.get("facilities", [])[:max_facilities]:
            lat, lon = fac.get("lat"), fac.get("lon")
            if not _valid_bengaluru_coord(lat, lon):
                continue
            cat = str(fac.get("category", "hospitals"))
            label_cat, hex_col, _ = FACILITY_STYLE.get(cat, ("Facility", "#3B82F6", "info-sign"))
            folium.CircleMarker(
                location=[float(lat), float(lon)],
                radius=5,
                color="#F8FAFC",
                weight=1,
                fill=True,
                fill_color=hex_col,
                fill_opacity=0.85,
                tooltip=f"{fac.get('name')} [{label_cat} — Unverified OSM Record]",
            ).add_to(fg_fac)
            stats["facility_markers"] += 1
        fg_fac.add_to(m)

    # 4. Phase 5 Rescue Routes (live override OR snapshot coordinates)
    routes_block = snapshot.get("routes", {}) if snapshot else {}
    p_coords = live_primary_coords if live_primary_coords is not None else routes_block.get("primary_coords", [])
    a_coords = live_alt_coords if live_alt_coords is not None else routes_block.get("alternative_coords", [])

    p_valid = [pt for pt in p_coords if len(pt) == 2 and _valid_bengaluru_coord(pt[0], pt[1])][:MAX_ROUTE_POINTS]
    a_valid = [pt for pt in a_coords if len(pt) == 2 and _valid_bengaluru_coord(pt[0], pt[1])][:MAX_ROUTE_POINTS]

    fg_routes = folium.FeatureGroup(name="Phase 5 Emergency Rescue Routes", show=True)
    if len(p_valid) >= 2:
        folium.PolyLine(
            locations=p_valid,
            color="#22C55E",
            weight=5.5,
            opacity=0.92,
            tooltip="Primary Rescue Route (Avoids BLOCKED Roads)",
        ).add_to(fg_routes)
        stats["route_polylines"] += 1
    if len(a_valid) >= 2:
        folium.PolyLine(
            locations=a_valid,
            color="#A855F7",
            weight=4.5,
            dash_array="8, 6",
            opacity=0.88,
            tooltip="Alternative Detour Rescue Route",
        ).add_to(fg_routes)
        stats["route_polylines"] += 1

    # Dispatch origin + Target Hospital marker from payload (works even without snapshot!)
    origin_coords = routes_block.get("origin_coords")
    if origin_coords and _valid_bengaluru_coord(origin_coords[0], origin_coords[1]):
        folium.Marker(
            location=origin_coords,
            tooltip=f"Dispatch Origin Node ({routes_block.get('origin_node')})",
            icon=folium.Icon(color="purple", icon="send"),
        ).add_to(fg_routes)
        stats["facility_markers"] += 1

    target_hosp = payload.get("phase5_rescue_routing", {}).get("target_hospital", {})
    if _valid_bengaluru_coord(target_hosp.get("lat"), target_hosp.get("lon")):
        folium.Marker(
            location=[float(target_hosp["lat"]), float(target_hosp["lon"])],
            tooltip=f"Target: {target_hosp.get('name', 'Target Hospital')} (Unverified OSM Record)",
            icon=folium.Icon(color="blue", icon="plus-sign"),
        ).add_to(fg_routes)
        stats["facility_markers"] += 1
    fg_routes.add_to(m)

    # 5. Phase 8 Active Observation Targets
    if snapshot and snapshot.get("phase8_observations"):
        fg_obs = folium.FeatureGroup(
            name="Phase 8 Field Observation Priorities",
            show=(focus in ("overview", "routing", "vulnerability")),
        )
        for obs in snapshot["phase8_observations"][:20]:
            lat, lon = obs.get("lat"), obs.get("lon")
            if not _valid_bengaluru_coord(lat, lon):
                continue
            folium.CircleMarker(
                location=[float(lat), float(lon)],
                radius=7,
                color="#FACC15",
                weight=2,
                fill=True,
                fill_color="#EF4444" if obs.get("condition") == "BLOCKED" else "#FACC15",
                fill_opacity=0.9,
                tooltip=(
                    f"Obs #{obs.get('rank')}: {obs.get('name')} | "
                    f"Priority: {obs.get('observation_priority_score')} ({obs.get('condition')})"
                ),
            ).add_to(fg_obs)
            stats["observation_markers"] += 1
        fg_obs.add_to(m)

    # 6. Reported Emergencies (Member 2 feed)
    if incidents_df is not None and not incidents_df.empty:
        fg_inc = folium.FeatureGroup(name="Reported Emergencies (Member 2)", show=True)
        for _, row in incidents_df.head(50).iterrows():
            lat, lon = row.get("lat"), row.get("lon")
            if not _valid_bengaluru_coord(lat, lon):
                continue
            urg = str(row.get("urgency", "WARNING")).upper()
            col = "#EF4444" if urg == "CRITICAL" else "#F97316"
            folium.CircleMarker(
                location=[float(lat), float(lon)],
                radius=7,
                color="#FFFFFF",
                weight=1.5,
                fill=True,
                fill_color=col,
                fill_opacity=0.95,
                tooltip=f"[{urg}] {row.get('title', 'Incident')} | Confidence: {row.get('confidence', 0):.2f}",
            ).add_to(fg_inc)
            stats["incident_markers"] += 1
        fg_inc.add_to(m)

    folium.LayerControl(collapsed=True).add_to(m)
    m._resq_overlay_stats = stats  # type: ignore[attr-defined]
    return m
