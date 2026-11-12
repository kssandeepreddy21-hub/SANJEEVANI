"""
SANJEEVANI – Member 3 Complete Demonstration Script
(`python -m sanjeevani.member3_demo`)

Executes Phases 2 through 8 on the real Bengaluru OpenStreetMap dataset:
- Phase 2: Road-level Flood Vulnerability Estimation (full city + central corridor)
- Phase 3: Real Road Network Rainfall Simulation (0, +15, +30, +60 min scenarios)
- Phase 4: Cascading Failure & Deduplicated Emergency Facility Impact Analysis
- Phase 5: Emergency Rescue Route Optimization (Primary, Alternative, Multi-Destination)
- Phase 6: Emergency Resource Allocation under Budget & Capacity Constraints
- Phase 7: Rescue Strategy Comparison (Nearest vs Priority vs Budget-Aware Optimized)
- Phase 8: Active Observation Planning (High-Vulnerability / Strategy-Changing Roads)

Exports a structured JSON payload to `data/processed/member3_dashboard_payload.json`
ready for Member 4's SANJEEVANI dashboard integration.
"""

import json
import time
from pathlib import Path

from sanjeevani.config import get_cache_path, get_graph_path, get_payload_path, get_pbf_path
from sanjeevani.validate_osm_graph import load_or_cache_osm_graph, GRAPH_FILE
from sanjeevani.flood_vulnerability import (
    annotate_graph_vulnerability,
    summarize_graph_vulnerability,
)
from sanjeevani.twin import (
    simulate_rainfall,
    predict_future_scenarios,
    summarize_rainfall_simulation,
    extract_corridor_subgraph,
)
from sanjeevani.cascading_failure import (
    extract_emergency_facilities,
    analyze_cascading_failures,
    snap_facilities_to_graph,
)
from sanjeevani.decision import (
    find_shortest_safe_route,
    find_alternative_route,
    optimize_multi_destination_routes,
    allocate_emergency_resources,
    compare_rescue_strategies,
    plan_active_observations,
)


DASHBOARD_OUTPUT_FILE = get_payload_path()
PBF_FILE = get_pbf_path()


def run_member3_demo():
    t_start = time.time()
    print("=================================================================")
    print("  SANJEEVANI - MEMBER 3 DISASTER SIMULATION & RESCUE OPTIMIZATION")
    print("=================================================================", flush=True)

    # 1. Load validated Bengaluru OSM Graph
    print("\n[STEP 1] Loading validated Bengaluru OSM road graph...", flush=True)
    active_graph_path = get_graph_path()
    active_cache_path = get_cache_path()
    full_graph = load_or_cache_osm_graph(
        active_graph_path, cache_file=active_cache_path, use_cache=True
    )
    print(
        f"  Loaded full Bengaluru graph: {full_graph.number_of_nodes():,} nodes, "
        f"{full_graph.number_of_edges():,} directed edges.",
        flush=True,
    )

    # Extract Central Bengaluru Emergency Corridor (Majestic, Cubbon Park, Shivajinagar,
    # KR Market, Richmond Town, Indiranagar) for fast multi-scenario operational routing
    corridor_bbox = (77.565, 12.955, 77.625, 13.005)
    corridor_graph = extract_corridor_subgraph(full_graph, *corridor_bbox)
    print(
        f"  Extracted Central Bengaluru operational corridor "
        f"({corridor_bbox}): {corridor_graph.number_of_nodes():,} nodes, "
        f"{corridor_graph.number_of_edges():,} directed edges.",
        flush=True,
    )

    # 2. Phase 2: Flood Vulnerability Estimation
    print("\n[PHASE 2] Estimating Road-Level Flood Vulnerability...", flush=True)
    city_vuln_summary = summarize_graph_vulnerability(full_graph)
    annotate_graph_vulnerability(corridor_graph, inplace=True)
    corridor_vuln_summary = summarize_graph_vulnerability(corridor_graph)

    print(
        f"  Full City Unique OSM Road Ways : {city_vuln_summary['total_unique_road_ways']:,}"
    )
    print(
        f"  Full City Directed Edges       : {city_vuln_summary['total_directed_edges']:,}"
    )
    print(
        f"  Average Way Vulnerability Score: {city_vuln_summary['average_way_vulnerability']}"
    )
    print(
        f"  Unique Road Way Risk Categories: {city_vuln_summary['way_risk_distribution']}"
    )
    print(
        f"  Directed Edge Risk Categories  : {city_vuln_summary['edge_risk_distribution']}",
        flush=True,
    )

    # 3. Phase 3: Real Road Network Rainfall Simulation (Current, +15, +30, +60 min)
    print(
        "\n[PHASE 3] Running Real Road Network Rainfall Scenarios (0, +15, +30, +60 min)...",
        flush=True,
    )
    # Also run a full-city heavy rainfall snapshot (intensity=85)
    full_heavy_graph, _ = simulate_rainfall(full_graph, rainfall_intensity=85)
    full_heavy_summary = summarize_rainfall_simulation(
        full_heavy_graph, rainfall_intensity=85
    )
    print(
        f"  Full-City Heavy Rainfall Snapshot (Intensity=85/100):\n"
        f"    Directed Edges -> OPEN: {full_heavy_summary['directed_edge_counts']['OPEN']:,}, "
        f"AT RISK: {full_heavy_summary['directed_edge_counts']['AT RISK']:,}, "
        f"BLOCKED: {full_heavy_summary['directed_edge_counts']['BLOCKED']:,}\n"
        f"    Unique Ways    -> OPEN: {full_heavy_summary['unique_road_way_counts']['OPEN']:,}, "
        f"AT RISK: {full_heavy_summary['unique_road_way_counts']['AT RISK']:,}, "
        f"BLOCKED: {full_heavy_summary['unique_road_way_counts']['BLOCKED']:,}\n"
        f"    Blocked Tunnels (unique ways): {full_heavy_summary['blocked_tunnel_ways']}, "
        f"Blocked Bridges (unique ways): {full_heavy_summary['blocked_bridge_ways']}"
    )

    scenarios = predict_future_scenarios(
        corridor_graph,
        current_rainfall=55,
        increase_per_15_min=10,
    )
    print("\n  Central Corridor Hypothetical Progression (starting at intensity=55):")
    scenario_summaries = []
    for sc in scenarios:
        s = sc["summary"]
        scenario_summaries.append(
            {
                "time_minutes": sc["time_minutes"],
                "rainfall_intensity": sc["rainfall_intensity"],
                "directed_edge_counts": s["directed_edge_counts"],
                "unique_road_way_counts": s["unique_road_way_counts"],
                "road_length_km": s["road_length_km"],
            }
        )
        print(
            f"    +{sc['time_minutes']:2d} min (Rainfall={sc['rainfall_intensity']:5.1f}) | "
            f"Ways -> OPEN: {s['unique_road_way_counts']['OPEN']:4d}, "
            f"AT RISK: {s['unique_road_way_counts']['AT RISK']:4d}, "
            f"BLOCKED: {s['unique_road_way_counts']['BLOCKED']:4d} | "
            f"Blocked Length: {s['road_length_km']['BLOCKED']:.2f} km",
            flush=True,
        )

    # Use the +60 min severe scenario graph (rainfall=95) for cascading failure & rescue routing
    severe_corridor_graph = scenarios[-1]["updated_graph"]

    # 4. Phase 4: Cascading Failure & Deduplicated Emergency Facility Impact
    print(
        "\n[PHASE 4] Extracting Deduplicated OSM Emergency Facilities & Analyzing Cascading Impact...",
        flush=True,
    )
    active_pbf_path = get_pbf_path()
    facilities_data = extract_emergency_facilities(active_pbf_path, graph=corridor_graph)
    fac_counts = facilities_data["counts"]
    print(
        f"  Excluded non-emergency shelters (gazebos/bus/picnic): "
        f"{facilities_data['excluded_non_emergency_shelters']}"
    )
    for cat, cinfo in fac_counts.items():
        print(
            f"  {cat:18s}: {cinfo['unique_facilities']:4d} unique "
            f"(raw nodes={cinfo['raw_nodes']}, ways={cinfo['raw_ways']}, "
            f"rels={cinfo['raw_relations']}, dup_pois_removed={cinfo['duplicate_poi_nodes_removed']})"
        )

    # Filter facilities that snapped inside our Central Bengaluru operational corridor
    corridor_facilities = {
        cat: [f for f in flist if f["nearest_node"] is not None]
        for cat, flist in facilities_data["categories"].items()
    }

    # Identify dispatch hub in Central Bengaluru (e.g. Bengaluru Secretariat Fire Station or central hub)
    fire_nodes = [
        f["nearest_node"]
        for f in corridor_facilities["fire_stations"]
        if f["nearest_node"] in corridor_graph
    ]
    if fire_nodes:
        dispatch_origin = fire_nodes[0]
    else:
        dispatch_origin = max(corridor_graph.nodes(), key=lambda n: corridor_graph.degree(n))

    # Build a synthetic scenario population map for affected hospital/shelter nodes
    synthetic_pop_map = {}
    for h in corridor_facilities["hospitals"][:15]:
        if h["nearest_node"]:
            synthetic_pop_map[h["nearest_node"]] = 240
    for sh in corridor_facilities["suitable_shelters"]:
        if sh["nearest_node"]:
            synthetic_pop_map[sh["nearest_node"]] = 180

    cascading_result = analyze_cascading_failures(
        severe_corridor_graph,
        failed_roads=None,  # Uses roads blocked by the +60 min heavy rainfall scenario
        facilities_by_category=corridor_facilities,
        dispatch_nodes=[dispatch_origin],
        population_by_node=synthetic_pop_map,
        population_is_synthetic=True,
    )

    conn_imp = cascading_result["connectivity_impact"]
    print(
        f"\n  Corridor Cascading Connectivity Impact (+60 min rainfall=95):\n"
        f"    Failed Unique Road Ways       : {conn_imp['failed_unique_road_ways']}\n"
        f"    Failed Directed Edges         : {conn_imp['failed_directed_edges']}\n"
        f"    Baseline Weak Components      : {conn_imp['baseline_components']} -> "
        f"Post-Failure: {conn_imp['post_failure_components']}\n"
        f"    Newly Disconnected Road Nodes : {conn_imp['newly_disconnected_node_count']}"
    )
    for cat, fimp in cascading_result["facility_impact"].items():
        print(
            f"    Facility Impact [{cat:17s}]: evaluated={fimp['total_evaluated']:3d}, "
            f"inaccessible={fimp['inaccessible_count']:2d}, "
            f"increased_travel_time={fimp['increased_travel_time_count']:2d}, "
            f"unaffected={fimp['unaffected_count']:3d}"
        )

    # 5. Phase 5: Emergency Rescue Route Optimization
    print("\n[PHASE 5] Optimizing Emergency Rescue Routes...", flush=True)
    reachable_hospitals = [
        h
        for h in corridor_facilities["hospitals"]
        if h["nearest_node"] and h["nearest_node"] != dispatch_origin
    ]
    target_hospital = reachable_hospitals[0] if reachable_hospitals else None
    target_node = target_hospital["nearest_node"] if target_hospital else dispatch_origin

    route_comparison = find_alternative_route(
        severe_corridor_graph,
        origin=dispatch_origin,
        destination=target_node,
        optimize_for="time",
        allow_at_risk=True,
        allow_uncertain_access=True,
    )
    prim = route_comparison["primary_route"]
    alt = route_comparison["alternative_route"]

    print(
        f"  Dispatch Origin Node : {dispatch_origin}\n"
        f"  Target Hospital      : {target_hospital['name'] if target_hospital else target_node} "
        f"(Node {target_node})\n"
        f"  Primary Safe Route   : reachable={prim['reachable']}, "
        f"distance={prim['total_distance_m']} m, "
        f"est_time={prim['estimated_travel_time_sec']} s, "
        f"status={prim['route_safety_status']}\n"
        f"  Alternative Route    : reachable={alt['reachable']}, "
        f"distinct={alt['is_distinct_from_primary']}, "
        f"distance={alt['total_distance_m']} m, "
        f"est_time={alt['estimated_travel_time_sec']} s, "
        f"overlap={alt['edge_overlap_ratio']}"
    )

    multi_dest_nodes = [h["nearest_node"] for h in reachable_hospitals[:5]]
    multi_routes = optimize_multi_destination_routes(
        severe_corridor_graph,
        origin=dispatch_origin,
        destinations=multi_dest_nodes,
        optimize_for="time",
    )
    print(
        f"  Multi-Destination Dispatch (5 Hospitals): "
        f"{multi_routes['reachable_count']}/{multi_routes['destinations_count']} reachable."
    )

    # 6 & 7. Phase 6 & 7: Emergency Resource Allocation & Strategy Comparison
    print(
        "\n[PHASE 6 & 7] Running Resource Allocation & Strategy Comparison...",
        flush=True,
    )
    affected_locations = []
    for idx, h in enumerate(reachable_hospitals[:6], start=1):
        h_node = h["nearest_node"]
        r_info = find_shortest_safe_route(
            severe_corridor_graph, dispatch_origin, h_node, optimize_for="time"
        )
        dist_m = r_info["total_distance_m"] if r_info["reachable"] else 3500.0
        # Assign varying realistic priorities and synthetic demand
        prio = [9.5, 4.0, 8.5, 3.0, 10.0, 6.0][(idx - 1) % 6]
        demand = [220, 140, 180, 120, 260, 160][(idx - 1) % 6]
        affected_locations.append(
            {
                "location_id": f"ZONE_{idx}_{h['osm_id']}",
                "name": h["name"],
                "priority": prio,
                "affected_population": demand,
                "distance_m": dist_m,
                "is_synthetic_population": True,
            }
        )

    available_resources = [
        {
            "resource_id": "ALS_AMBULANCE_UNIT",
            "resource_type": "advanced_life_support_ambulance",
            "units": 4,
            "capacity_per_unit": 80,
            "cost_per_unit": 450.0,
            "speed_kmh": 32.0,
        },
        {
            "resource_id": "NDRF_RESCUE_BOAT",
            "resource_type": "inflatable_flood_rescue_boat",
            "units": 4,
            "capacity_per_unit": 110,
            "cost_per_unit": 650.0,
            "speed_kmh": 20.0,
        },
    ]

    strategy_comparison = compare_rescue_strategies(
        affected_locations=affected_locations,
        available_resources=available_resources,
        total_budget=3200.0,
    )

    for row in strategy_comparison["comparison_summary"]:
        print(
            f"  Strategy [{row['strategy']:24s}] -> "
            f"Served: {row['served_population']:4d} ({row['population_coverage_pct']:5.1f}%), "
            f"Unserved: {row['unserved_population']:4d}, "
            f"Priority-Weighted: {row['priority_weighted_served']:7.1f}, "
            f"Avg Dist: {row['average_response_distance_m']:7.1f} m, "
            f"Avg Time: {row['average_response_time_sec']:6.1f} s, "
            f"Budget Used: {row['total_budget_used']:6.1f} ({row['budget_utilization_pct']}%)"
        )
    print(f"  Recommended Strategy: {strategy_comparison['recommended_strategy']}")
    print(f"  Reason: {strategy_comparison['recommendation_reason']}", flush=True)

    # 8. Phase 8: Active Observation Planning
    print(
        "\n[PHASE 8] Planning Active Field/Sensor Observations (Top 8 Critical Roads)...",
        flush=True,
    )
    critical_route_roads = (prim.get("road_ids") or []) + (alt.get("road_ids") or [])
    facility_node_ids = [h["nearest_node"] for h in reachable_hospitals[:10]]

    observation_plan = plan_active_observations(
        severe_corridor_graph,
        top_k=8,
        critical_route_road_ids=critical_route_roads,
        facility_nodes=facility_node_ids,
        rainfall_intensity=95,
    )

    for rec in observation_plan["recommendations"]:
        print(
            f"  Rank #{rec['rank']} | Road ID: {rec['road_id']:10s} | "
            f"Highway: {rec['highway']:10s} | "
            f"Score: {rec['observation_priority_score']:.3f} "
            f"(Vuln={rec['vulnerability_score']:.2f}, Uncert={rec['uncertainty_score']:.2f}, "
            f"Crit={rec['criticality_score']:.2f}) | "
            f"Changes Strategy: {rec['could_change_rescue_strategy']}"
        )

    def _compact_route_for_dashboard(route_obj):
        edges = route_obj.get("edges", [])
        unique_road_ids = list(dict.fromkeys(route_obj.get("road_ids", [])))
        return {
            "reachable": route_obj.get("reachable"),
            "origin": route_obj.get("origin"),
            "destination": route_obj.get("destination"),
            "optimize_for": route_obj.get("optimize_for"),
            "total_distance_m": route_obj.get("total_distance_m"),
            "estimated_travel_time_sec": route_obj.get("estimated_travel_time_sec"),
            "segment_count": len(edges),
            "node_count": len(route_obj.get("nodes", [])),
            "unique_road_ids": unique_road_ids,
            "at_risk_segments_count": route_obj.get("at_risk_segments_count"),
            "uncertain_access_segments_count": route_obj.get("uncertain_access_segments_count"),
            "uncertain_access_warnings": route_obj.get("uncertain_access_warnings", []),
            "route_safety_status": route_obj.get("route_safety_status"),
            "is_distinct_from_primary": route_obj.get("is_distinct_from_primary"),
            "edge_overlap_ratio": route_obj.get("edge_overlap_ratio"),
            "sample_segments": edges[:10],
        }

    recommended_strat_name = strategy_comparison["recommended_strategy"]
    recommended_strat_data = strategy_comparison["strategies"][recommended_strat_name]

    # Save structured payload for Member 4 Dashboard integration (all 8 phases)
    dashboard_payload = {
        "metadata": {
            "module": "SANJEEVANI_Member_3_Disaster_Simulation_and_Rescue_Optimization",
            "city": "Bengaluru, Karnataka, India",
            "data_source": str(PBF_FILE),
            "execution_time_sec": round(time.time() - t_start, 2),
        },
        "phase1_network_validation": {
            "graph_file": str(GRAPH_FILE),
            "graph_type": type(full_graph).__name__,
            "is_directed": full_graph.is_directed(),
            "is_multigraph": full_graph.is_multigraph(),
            "total_nodes": full_graph.number_of_nodes(),
            "total_directed_edges": full_graph.number_of_edges(),
            "total_unique_road_ways": city_vuln_summary["total_unique_road_ways"],
            "central_corridor_nodes": corridor_graph.number_of_nodes(),
            "central_corridor_directed_edges": corridor_graph.number_of_edges(),
            "validation_status": "PASS",
        },
        "phase2_vulnerability": {
            "full_city": city_vuln_summary,
            "central_corridor": corridor_vuln_summary,
        },
        "phase3_rainfall_simulation": {
            "full_city_heavy_rainfall_85": full_heavy_summary,
            "corridor_progression_scenarios": scenario_summaries,
        },
        "phase4_cascading_and_facilities": {
            "facility_counts_citywide": fac_counts,
            "excluded_non_emergency_shelters": facilities_data[
                "excluded_non_emergency_shelters"
            ],
            "verification_disclaimer": facilities_data["verification_disclaimer"],
            "connectivity_impact": conn_imp,
            "facility_impact": {
                k: {
                    key: val
                    for key, val in v.items()
                    if key not in ("inaccessible_facilities", "increased_travel_time_facilities")
                }
                for k, v in cascading_result["facility_impact"].items()
            },
            "population_impact": cascading_result["population_impact"],
        },
        "phase5_rescue_routing": {
            "dispatch_origin_node": dispatch_origin,
            "target_hospital": target_hospital,
            "primary_route": _compact_route_for_dashboard(prim),
            "alternative_route": _compact_route_for_dashboard(alt),
            "multi_destination_summary": {
                "destinations_count": multi_routes["destinations_count"],
                "reachable_count": multi_routes["reachable_count"],
                "unreachable_count": multi_routes["unreachable_count"],
            },
        },
        "phase6_resource_allocation": {
            "strategy_used": recommended_strat_name,
            "metrics": recommended_strat_data["metrics"],
            "allocations": recommended_strat_data["allocations"],
            "location_outcomes": recommended_strat_data["location_outcomes"],
        },
        "phase7_strategy_comparison": {
            "comparison_summary": strategy_comparison["comparison_summary"],
            "recommended_strategy": recommended_strat_name,
            "recommendation_reason": strategy_comparison["recommendation_reason"],
        },
        "phase6_and_7_resource_and_strategies": {
            "comparison_summary": strategy_comparison["comparison_summary"],
            "recommended_strategy": recommended_strat_name,
            "recommendation_reason": strategy_comparison["recommendation_reason"],
            "recommended_allocations": recommended_strat_data["allocations"],
            "location_outcomes": recommended_strat_data["location_outcomes"],
        },
        "phase8_active_observation_plan": observation_plan,
    }

    output_file = get_payload_path()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(dashboard_payload, f, indent=2)

    print("\n=================================================================")
    print(f"  Demo completed in {round(time.time() - t_start, 2)}s.")
    print(f"  Dashboard payload saved to: {output_file}")
    print("=================================================================", flush=True)

    return dashboard_payload


if __name__ == "__main__":
    run_member3_demo()

