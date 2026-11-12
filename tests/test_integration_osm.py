"""End-to-end backend integration tests linking Member 2, Incident Bridge, and Member 3."""

import builtins
import sys
import networkx as nx
import pandas as pd

from sanjeevani import dashboard_evidence
from sanjeevani.decision import allocate_emergency_resources, compare_rescue_strategies, find_shortest_safe_route
from sanjeevani.incident_bridge import incident_to_osm_node, incidents_to_affected_locations
from sanjeevani.twin import predict_future_scenarios, simulate_rainfall


def _build_mini_bengaluru_multidigraph():
    G = nx.MultiDiGraph()
    G.add_node("N_HUB", x=77.5900, y=12.9700)
    G.add_node("N_MID", x=77.5950, y=12.9730)
    G.add_node("N_CRIT", x=77.6000, y=12.9760)
    G.add_node("N_BYPASS", x=77.5940, y=12.9680)

    common = {"oneway": "no", "surface": "asphalt", "bridge": "no", "tunnel": "no"}
    G.add_edge("N_HUB", "N_MID", road_id="1001", highway="primary", length_m=600.0, **common)
    G.add_edge("N_MID", "N_CRIT", road_id="1002", highway="residential", length_m=550.0, flood_sensitivity=0.85, **common)
    G.add_edge("N_HUB", "N_BYPASS", road_id="1003", highway="primary", length_m=700.0, flood_sensitivity=0.20, **common)
    G.add_edge("N_BYPASS", "N_CRIT", road_id="1004", highway="secondary", length_m=750.0, flood_sensitivity=0.30, **common)
    return G


def test_member2_incident_to_osm_route_and_allocation():
    G = _build_mini_bengaluru_multidigraph()
    G_orig_edges = G.number_of_edges()

    inc_valid = dashboard_evidence.score_emergency_report(
        title="Flooding near junction",
        sector="Central Riverfront",
        disaster_type="Flash Flood Entrapment",
        urgency="CRITICAL",
        simulate_duplicate=False,
    )
    inc_valid["lat"] = 12.9761
    inc_valid["lon"] = 77.6001

    inc_dup = dashboard_evidence.score_emergency_report(
        title="Recycled clip",
        sector="East Basin",
        disaster_type="Flash Flood Entrapment",
        urgency="WARNING",
        simulate_duplicate=True,
    )

    bridge_out = incidents_to_affected_locations([inc_valid, inc_dup], G, require_verified=True)
    assert len(bridge_out["affected_locations"]) == 1
    assert len(bridge_out["held_incidents"]) == 1
    assert bridge_out["is_population_synthetic"] is True

    sim_graph, _ = simulate_rainfall(G, rainfall_intensity=90)
    target_node = bridge_out["affected_locations"][0]["node"]
    assert target_node == "N_CRIT"

    route = find_shortest_safe_route(sim_graph, origin="N_HUB", destination=target_node, optimize_for="time")
    assert route["reachable"] is True
    assert route["route_safety_status"] == "SAFE_OPEN"
    # N_MID -> N_CRIT has 90 * 0.85 = 76.5 >= 70 (BLOCKED), so route must go via N_BYPASS
    assert "N_BYPASS" in route["nodes"]

    resources = [
        {"resource_id": "AMB-1", "resource_type": "ambulance", "units": 3, "capacity_per_unit": 500, "cost_per_unit": 200.0}
    ]
    alloc = allocate_emergency_resources(bridge_out["affected_locations"], resources, total_budget=1000.0)
    assert alloc["metrics"]["population_coverage_pct"] == 100.0
    assert G.number_of_edges() == G_orig_edges  # Original graph unmutated


def test_incident_bridge_dataframe_and_missing_coords():
    G = _build_mini_bengaluru_multidigraph()
    df = pd.DataFrame(
        [
            {"incident_id": "INC-1", "title": "Valid", "lat": 12.9701, "lon": 77.5901, "urgency": "CRITICAL", "confidence": 0.9, "verified": True, "duplicate_warning": "Clear"},
            {"incident_id": "INC-2", "title": "No coords", "lat": None, "lon": None, "urgency": "WARNING", "confidence": 0.8, "verified": True, "duplicate_warning": "Clear"},
        ]
    )
    out = incidents_to_affected_locations(df, G)
    assert len(out["affected_locations"]) == 1
    assert out["affected_locations"][0]["node"] == "N_HUB"
    assert len(out["unmapped_incidents"]) == 1


def test_incident_to_osm_node_single():
    G = _build_mini_bengaluru_multidigraph()
    snapped = incident_to_osm_node(
        {"incident_id": "INC-X", "lat": 12.9731, "lon": 77.5951, "urgency": "WARNING", "verified": True},
        G,
    )
    assert snapped["node"] == "N_MID"
    assert snapped["snap_distance_m"] < 50.0


def test_future_scenarios_preserve_graph_and_compare_strategies():
    G = _build_mini_bengaluru_multidigraph()
    horizons = predict_future_scenarios(G, current_rainfall=40, increase_per_15_min=15)
    assert [h["time_minutes"] for h in horizons] == [0, 15, 30, 60]

    locs = [{"location_id": "L1", "node": "N_CRIT", "priority": 3.0, "affected_population": 1000, "distance_m": 1200.0}]
    res = [{"resource_id": "RES-1", "units": 2, "capacity_per_unit": 600, "cost_per_unit": 150.0}]
    cmp_out = compare_rescue_strategies(locs, res, total_budget=500.0)
    assert "recommended_strategy" in cmp_out


def test_sanjeevani_twin_imports_without_osmium(monkeypatch):
    monkeypatch.setitem(sys.modules, "osmium", None)
    real_import = builtins.__import__

    def _guarded_import(name, *args, **kwargs):
        if name == "osmium":
            raise ImportError("Simulated missing osmium")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _guarded_import)
    for mod in ("sanjeevani.twin", "sanjeevani.twin_member3", "sanjeevani.cascading_failure"):
        sys.modules.pop(mod, None)

    import sanjeevani.twin as reimported_twin
    assert hasattr(reimported_twin, "simulate_rainfall")
    assert hasattr(reimported_twin, "simulate_all_horizons")
