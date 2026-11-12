import sys
from pathlib import Path

import networkx as nx
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sanjeevani.twin import (
    simulate_rainfall,
    predict_future_scenarios,
    summarize_rainfall_simulation,
    estimate_edge_vulnerability,
    annotate_graph_vulnerability,
    summarize_graph_vulnerability,
    simulate_road_failures,
    analyze_cascading_failures,
)


def test_rainfall_simulation():

    # Create a sample city network
    city = nx.Graph()

    # Add roads with different flood sensitivities
    city.add_edge("A", "B", road_id="R1", flood_sensitivity=0.20)

    city.add_edge("B", "C", road_id="R2", flood_sensitivity=0.40)

    city.add_edge("C", "D", road_id="R3", flood_sensitivity=0.60)

    city.add_edge("D", "E", road_id="R4", flood_sensitivity=0.80)

    city.add_edge("E", "F", road_id="R5", flood_sensitivity=0.95)

    # Simulate heavy rainfall
    updated_city, results = simulate_rainfall(city, 80)

    # Check road conditions
    assert results[0]["condition"] == "OPEN"

    assert results[2]["condition"] == "AT RISK"

    assert results[4]["condition"] == "BLOCKED"

    # Check that the original graph was not modified
    assert "condition" not in city["A"]["B"]

    # Check that the updated graph contains the new information
    assert updated_city["E"]["F"]["available"] is False


def test_future_scenario_prediction():

    # Create a sample city
    city = nx.Graph()

    city.add_edge(
        "A", "B",
        road_id="R1",
        flood_sensitivity=0.50
    )

    city.add_edge(
        "B", "C",
        road_id="R2",
        flood_sensitivity=0.90
    )

    # Predict future conditions
    scenarios = predict_future_scenarios(
        city,
        current_rainfall=30,
        increase_per_15_min=10
    )

    # Check the number of scenarios
    assert len(scenarios) == 4

    # Check the time intervals
    assert [s["time_minutes"] for s in scenarios] == [
        0, 15, 30, 60
    ]

    # Check rainfall calculations
    assert scenarios[0]["rainfall_intensity"] == 30
    assert scenarios[1]["rainfall_intensity"] == 40
    assert scenarios[2]["rainfall_intensity"] == 50
    assert scenarios[3]["rainfall_intensity"] == 70

    # Check that the original city is unchanged
    assert "condition" not in city["A"]["B"]


def test_flood_vulnerability_estimation_and_observed_distinction():

    # Elevated bridge on primary road -> LOW risk
    bridge_est = estimate_edge_vulnerability({
        "road_id": "W_BRIDGE",
        "highway": "primary",
        "bridge": "yes",
        "layer": "1",
        "surface": "asphalt",
        "smoothness": "good",
    })
    assert bridge_est["value_type"] == "estimated"
    assert bridge_est["is_estimated"] is True
    assert bridge_est["vulnerability_score"] < 0.25
    assert bridge_est["risk_category"] == "LOW"

    # Underpass tunnel with negative layer -> CRITICAL risk
    tunnel_est = estimate_edge_vulnerability({
        "road_id": "W_TUNNEL",
        "highway": "secondary",
        "tunnel": "yes",
        "layer": "-1",
        "surface": "unpaved",
    })
    assert tunnel_est["vulnerability_score"] >= 0.85
    assert tunnel_est["risk_category"] == "CRITICAL"

    # Observed measurement is preserved as "observed"
    obs_est = estimate_edge_vulnerability({
        "road_id": "W_OBS",
        "highway": "residential",
        "observed_flood_sensitivity": 0.62,
    })
    assert obs_est["value_type"] == "observed"
    assert obs_est["is_estimated"] is False
    assert obs_est["vulnerability_score"] == 0.62


def test_osm_multidigraph_rainfall_and_summary():

    g = nx.MultiDiGraph()
    # Bridge road way (2 directed edges sharing road_id="100")
    g.add_edge("1", "2", road_id="100", highway="primary", bridge="yes", layer="1", length_m=200.0)
    g.add_edge("2", "1", road_id="100", highway="primary", bridge="yes", layer="1", length_m=200.0)
    # Underpass tunnel road way (1 directed edge, road_id="200")
    g.add_edge("2", "3", road_id="200", highway="secondary", tunnel="yes", layer="-1", length_m=150.0)

    updated, results = simulate_rainfall(g, 80)
    summary = summarize_rainfall_simulation(updated, results, rainfall_intensity=80)

    assert summary["total_directed_edges"] == 3
    assert summary["total_unique_road_ways"] == 2
    assert summary["directed_edge_counts"]["OPEN"] == 2
    assert summary["directed_edge_counts"]["BLOCKED"] == 1
    assert summary["unique_road_way_counts"]["OPEN"] == 1
    assert summary["unique_road_way_counts"]["BLOCKED"] == 1
    assert summary["blocked_tunnel_ways"] == 1
    assert summary["blocked_bridge_ways"] == 0


def test_invalid_inputs_rainfall():

    g = nx.Graph()
    g.add_edge("A", "B", road_id="R1", flood_sensitivity=0.5)

    with pytest.raises(ValueError):
        simulate_rainfall(g, -10)

    with pytest.raises(ValueError):
        simulate_rainfall(g, 120)

    g_bad = nx.Graph()
    g_bad.add_edge("A", "B", road_id="R1", flood_sensitivity=1.5)
    with pytest.raises(ValueError):
        simulate_rainfall(g_bad, 50)

    with pytest.raises(ValueError):
        predict_future_scenarios(g, current_rainfall=40, increase_per_15_min=-5)


def test_cascading_failures_and_facility_accessibility():

    g = nx.MultiDiGraph()
    # Main corridor: N1 -> N2 -> N3 -> N4
    g.add_edge("N1", "N2", road_id="R_MAIN_1", length_m=100.0)
    g.add_edge("N2", "N3", road_id="R_BRIDGE", length_m=100.0)
    g.add_edge("N3", "N4", road_id="R_ISOLATED_LINK", length_m=100.0)
    # Detour around R_BRIDGE: N2 -> N5 -> N3 (longer: 400m vs 100m)
    g.add_edge("N2", "N5", road_id="R_DETOUR_1", length_m=200.0)
    g.add_edge("N5", "N3", road_id="R_DETOUR_2", length_m=200.0)

    facilities = {
        "hospitals": [
            {"facility_id": "H1", "name": "Detour Hospital", "nearest_node": "N3"},
            {"facility_id": "H2", "name": "Cut-off Hospital", "nearest_node": "N4"},
        ],
        "fire_stations": [
            {"facility_id": "F1", "name": "Central Fire", "nearest_node": "N1"},
        ],
    }

    # Fail both R_BRIDGE (causing detour to N3) and R_ISOLATED_LINK (disconnecting N4)
    analysis = analyze_cascading_failures(
        g,
        failed_roads=["R_BRIDGE", "R_ISOLATED_LINK"],
        facilities_by_category=facilities,
        dispatch_nodes=["N1"],
        population_by_node={"N3": 300, "N4": 150},
        population_is_synthetic=True,
    )

    conn = analysis["connectivity_impact"]
    assert conn["failed_unique_road_ways"] == 2
    assert "N4" in conn["newly_disconnected_nodes"]

    hosp_impact = analysis["facility_impact"]["hospitals"]
    assert hosp_impact["inaccessible_count"] == 1
    assert hosp_impact["inaccessible_facilities"][0]["facility_id"] == "H2"

    assert hosp_impact["increased_travel_time_count"] == 1
    assert hosp_impact["increased_travel_time_facilities"][0]["facility_id"] == "H1"
    assert hosp_impact["increased_travel_time_facilities"][0]["detour_increase_m"] == 300.0

    pop_impact = analysis["population_impact"]
    assert pop_impact["is_synthetic"] is True
    assert pop_impact["disconnected_population"] == 150
    assert pop_impact["delayed_access_population"] == 300
    assert pop_impact["total_affected_population"] == 450
