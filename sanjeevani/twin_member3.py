import networkx as nx

from sanjeevani.flood_vulnerability import (
    estimate_edge_vulnerability,
    annotate_graph_vulnerability,
    summarize_graph_vulnerability,
)
from sanjeevani.cascading_failure import (
    extract_emergency_facilities,
    simulate_road_failures,
    analyze_cascading_failures,
    snap_facilities_to_graph,
)


def simulate_rainfall(city_graph, rainfall_intensity):
    """
    Simulate how rainfall affects roads in a city.

    rainfall_intensity: Value between 0 and 100.
    flood_sensitivity: Value between 0 and 1. If not already present on an edge,
    it is automatically estimated using the explainable OSM infrastructure
    vulnerability model (`estimate_edge_vulnerability`).

    The original `city_graph` is never modified.
    """

    # Step 1: Validate rainfall intensity
    if not isinstance(rainfall_intensity, (int, float)) or not 0 <= rainfall_intensity <= 100:
        raise ValueError("Rainfall intensity must be between 0 and 100.")

    # Step 2: Create a copy of the original city graph
    updated_graph = city_graph.copy()

    # Step 3: Store the results of each road
    road_results = []
    way_vulnerability_cache = {}

    # Step 4: Check every road in the city
    for u, v, data in updated_graph.edges(data=True):

        # Read the road's flood sensitivity, or estimate from OSM infrastructure tags
        if "flood_sensitivity" in data and data["flood_sensitivity"] is not None:
            sensitivity = data["flood_sensitivity"]
            if not isinstance(sensitivity, (int, float)) or isinstance(sensitivity, bool) or not 0 <= sensitivity <= 1:
                raise ValueError(
                    f"Invalid flood sensitivity for road {u}-{v}."
                )
            value_type = data.get("vulnerability_value_type", "provided")
        else:
            road_key = data.get("road_id")
            if road_key and road_key in way_vulnerability_cache:
                est = way_vulnerability_cache[road_key]
            else:
                est = estimate_edge_vulnerability(data)
                if road_key:
                    way_vulnerability_cache[road_key] = est

            sensitivity = est["vulnerability_score"]
            value_type = est["value_type"]
            data["flood_sensitivity"] = sensitivity
            data["vulnerability_score"] = sensitivity
            data["risk_category"] = est["risk_category"]
            data["uncertainty_score"] = est["uncertainty_score"]
            data["vulnerability_value_type"] = value_type

        # Step 5: Calculate flood impact
        impact_score = rainfall_intensity * sensitivity

        # Step 6: Identify road condition
        if impact_score >= 70:
            condition = "BLOCKED"
            available = False

        elif impact_score >= 40:
            condition = "AT RISK"
            available = True

        else:
            condition = "OPEN"
            available = True

        # Step 7: Update road information
        data["flood_impact"] = round(impact_score, 2)
        data["condition"] = condition
        data["available"] = available

        # Step 8: Store road results
        road_results.append({
            "road": data.get("road_id", f"{u}-{v}"),
            "start": u,
            "end": v,
            "flood_sensitivity": round(float(sensitivity), 4),
            "value_type": value_type,
            "impact_score": round(impact_score, 2),
            "condition": condition,
            "available": available
        })

    # Step 9: Return the updated network and results
    return updated_graph, road_results


def summarize_rainfall_simulation(updated_graph, road_results=None, rainfall_intensity=None):
    """
    Generate summary statistics from a rainfall simulation run on a road network.
    Distinguishes directed edges from unique OSM road ways (`road_id`).
    """

    edge_conditions = {"OPEN": 0, "AT RISK": 0, "BLOCKED": 0}
    edge_lengths_m = {"OPEN": 0.0, "AT RISK": 0.0, "BLOCKED": 0.0}
    way_worst_condition = {}
    condition_rank = {"OPEN": 0, "AT RISK": 1, "BLOCKED": 2}
    rank_to_cond = {0: "OPEN", 1: "AT RISK", 2: "BLOCKED"}

    blocked_by_highway = {}
    at_risk_by_highway = {}
    blocked_bridges_ways = set()
    blocked_tunnels_ways = set()

    total_edges = 0

    for u, v, data in updated_graph.edges(data=True):
        total_edges += 1
        cond = data.get("condition", "OPEN")
        length_m = float(data.get("length_m", 0.0))
        road_id = str(data.get("road_id", f"{u}-{v}"))
        highway = str(data.get("highway", "unknown"))

        edge_conditions[cond] = edge_conditions.get(cond, 0) + 1
        edge_lengths_m[cond] = edge_lengths_m.get(cond, 0.0) + length_m

        r = condition_rank.get(cond, 0)
        if road_id not in way_worst_condition or r > way_worst_condition[road_id]:
            way_worst_condition[road_id] = r

        if cond == "BLOCKED":
            blocked_by_highway[highway] = blocked_by_highway.get(highway, 0) + 1
            if str(data.get("bridge", "no")).lower() not in ("no", "unknown", ""):
                blocked_bridges_ways.add(road_id)
            if str(data.get("tunnel", "no")).lower() not in ("no", "unknown", ""):
                blocked_tunnels_ways.add(road_id)
        elif cond == "AT RISK":
            at_risk_by_highway[highway] = at_risk_by_highway.get(highway, 0) + 1

    way_conditions = {"OPEN": 0, "AT RISK": 0, "BLOCKED": 0}
    for r in way_worst_condition.values():
        way_conditions[rank_to_cond[r]] += 1

    total_ways = len(way_worst_condition)

    return {
        "rainfall_intensity": rainfall_intensity,
        "is_hypothetical_scenario": True,
        "total_directed_edges": total_edges,
        "total_unique_road_ways": total_ways,
        "directed_edge_counts": edge_conditions,
        "unique_road_way_counts": way_conditions,
        "road_length_km": {
            k: round(val / 1000.0, 3) for k, val in edge_lengths_m.items()
        },
        "blocked_edges_by_highway": blocked_by_highway,
        "at_risk_edges_by_highway": at_risk_by_highway,
        "blocked_bridge_ways": len(blocked_bridges_ways),
        "blocked_tunnel_ways": len(blocked_tunnels_ways),
    }


def predict_future_scenarios(
    city_graph,
    current_rainfall,
    increase_per_15_min=10
):
    """
    Simulate possible road conditions at different future times.

    These are hypothetical scenarios, not real weather forecasts.
    """

    # Validate current rainfall
    if not isinstance(current_rainfall, (int, float)) or not 0 <= current_rainfall <= 100:
        raise ValueError("Current rainfall must be between 0 and 100.")

    # Validate rainfall increase
    if not isinstance(increase_per_15_min, (int, float)) or increase_per_15_min < 0:
        raise ValueError("Rainfall increase cannot be negative.")

    # Define future time intervals
    future_times = [0, 15, 30, 60]

    # Store all future scenarios
    scenarios = []

    # Simulate each time interval
    for minutes in future_times:

        # Calculate assumed future rainfall
        rainfall = min(
            100,
            current_rainfall + (increase_per_15_min * minutes / 15)
        )

        # Run the existing rainfall simulation
        updated_graph, road_results = simulate_rainfall(
            city_graph,
            rainfall
        )

        summary = summarize_rainfall_simulation(
            updated_graph,
            road_results=road_results,
            rainfall_intensity=rainfall,
        )

        # Store the scenario
        scenario = {
            "time_minutes": minutes,
            "rainfall_intensity": rainfall,
            "road_results": road_results,
            "updated_graph": updated_graph,
            "summary": summary,
            "scenario_disclaimer": "Hypothetical rainfall projection, not a meteorological forecast.",
        }

        scenarios.append(scenario)

    return scenarios


def extract_corridor_subgraph(graph, min_lon, min_lat, max_lon, max_lat):
    """
    Extract a geographic bounding-box subgraph (copy) from the Bengaluru road
    graph without modifying the original graph.
    """

    selected_nodes = [
        n
        for n, d in graph.nodes(data=True)
        if min_lon <= float(d.get("x", d.get("lon", 0.0))) <= max_lon
        and min_lat <= float(d.get("y", d.get("lat", 0.0))) <= max_lat
    ]
    return graph.subgraph(selected_nodes).copy()
