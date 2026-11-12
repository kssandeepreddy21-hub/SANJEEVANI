"""
sanjeevani/resilience.py
------------------------
Member 1 Interface: Disaster Prediction & Infrastructure Resilience.
Provides clean, modular functions for evaluating road network vulnerability,
NetworkX passable graph construction, hospital accessibility, and single-road
failure stress testing for Section 2 (Resilience Lab).
"""

import pandas as pd

from sanjeevani.data import (
    build_city_road_graph,
    evaluate_network_resilience,
    get_synthetic_roads,
)


def assess_road_network_resilience(
    scenario_name: str,
    manual_failed_roads: set[str] | None = None,
    roads_override: list[dict] | None = None,
) -> dict:
    """
    Evaluate the current road network resilience, NetworkX passable graph,
    sector-to-hospital accessibility, and critical road rankings.
    """
    roads_list = (
        roads_override
        if roads_override is not None
        else get_synthetic_roads(scenario_name, manual_failed_roads=manual_failed_roads)
    )
    df_roads = pd.DataFrame(roads_list)
    resilience_eval = evaluate_network_resilience(
        scenario_name,
        manual_failed_roads=manual_failed_roads,
    )
    G_passable = build_city_road_graph(
        scenario_name,
        manual_failed_roads=manual_failed_roads,
        include_blocked=False,
    )

    df_ranking = df_roads.sort_values("critical_rank")[
        [
            "critical_rank",
            "road_id",
            "name",
            "status",
            "vulnerability_score",
            "failure_prob",
            "population_impact",
            "preposition_Zone",
        ]
    ].rename(
        columns={
            "critical_rank": "Rank",
            "road_id": "Road ID",
            "name": "Corridor Name",
            "status": "Status",
            "vulnerability_score": "Vuln Score",
            "failure_prob": "Failure Prob",
            "population_impact": "Pop. Impact",
            "preposition_Zone": "Recommended Pre-Positioning",
        }
    )

    return {
        "roads_list": roads_list,
        "roads_df": df_roads,
        "resilience_eval": resilience_eval,
        "passable_graph": G_passable,
        "critical_rankings_df": df_ranking,
        "total_nodes": G_passable.number_of_nodes(),
        "total_roads": len(roads_list),
        "passable_edges": G_passable.number_of_edges(),
        "blocked_edges": len(roads_list) - G_passable.number_of_edges(),
    }


def simulate_single_road_failure(
    scenario_name: str,
    road_id: str,
    existing_failed_roads: set[str] | None = None,
) -> dict:
    """
    Stress-test a single road failure on top of existing road closures and
    return before/after connectivity and hospital reachability metrics.
    """
    base_failed = set(existing_failed_roads) if existing_failed_roads else set()
    baseline = evaluate_network_resilience(
        scenario_name,
        manual_failed_roads=base_failed,
    )

    updated_failed = base_failed | {road_id}
    post_failure = evaluate_network_resilience(
        scenario_name,
        manual_failed_roads=updated_failed,
    )

    return {
        "road_id": road_id,
        "updated_failed_roads": updated_failed,
        "baseline_access_pct": baseline["hospital_access_pct"],
        "post_failure_access_pct": post_failure["hospital_access_pct"],
        "access_drop_pct": round(
            baseline["hospital_access_pct"] - post_failure["hospital_access_pct"], 1
        ),
        "isolated_population": post_failure["isolated_population"],
        "connected_population": post_failure["connected_population"],
        "is_fully_connected": post_failure["is_fully_connected"],
        "num_connected_components": post_failure["num_connected_components"],
        "sector_df": post_failure["sector_df"],
    }
