"""
Automated Pytest Suite for SANJEEVANI Module 1: Disaster Prediction & Infrastructure Resilience
File: tests/test_resilience.py

Scope:
    Priority 1: Verification of Synthetic City Graph Generation & Data Model Integrity.
"""

import os
import networkx as nx
import pytest
import pandas as pd

from data import (
    build_synthetic_city,
    get_nodes_by_type,
    get_city_summary,
    export_city_to_dataframes,
    save_city_to_json,
    load_city_from_json,
)


@pytest.fixture
def city_graph() -> nx.Graph:
    """Fixture providing a fresh synthetic city graph for each test."""
    return build_synthetic_city()


# -----------------------------------------------------------------------------
# PRIORITY 1: SYNTHETIC CITY GRAPH INTEGRITY TESTS
# -----------------------------------------------------------------------------

def test_city_graph_instance_and_connectivity(city_graph: nx.Graph):
    """
    Test 1: Verify graph creation, instance type, and normal-condition connectivity.
    Under pre-disaster conditions, every neighborhood must be connected to the network.
    """
    assert isinstance(city_graph, nx.Graph), "City model must be a NetworkX Graph."
    assert city_graph.number_of_nodes() == 16, "City must contain exactly 16 defined nodes."
    assert city_graph.number_of_edges() == 20, "City must contain exactly 20 defined roads/bridges."
    assert nx.is_connected(city_graph), "Baseline city network must be fully connected."


def test_node_categorization_and_attributes(city_graph: nx.Graph):
    """
    Test 2: Verify that all required node categories and attributes exist and are valid.
    """
    residential = get_nodes_by_type(city_graph, "residential")
    hospitals = get_nodes_by_type(city_graph, "hospital")
    shelters = get_nodes_by_type(city_graph, "shelter")
    stations = get_nodes_by_type(city_graph, "emergency_station")
    junctions = get_nodes_by_type(city_graph, "junction")

    # Check node counts
    assert len(residential) == 6, "Expected 6 residential areas."
    assert len(hospitals) == 2, "Expected 2 hospitals."
    assert len(shelters) == 2, "Expected 2 shelters."
    assert len(stations) == 2, "Expected 2 emergency stations."
    assert len(junctions) == 4, "Expected 4 junctions."

    # Validate residential populations
    total_pop = 0
    for node_id in residential:
        data = city_graph.nodes[node_id]
        assert data.get("population", 0) > 0, f"Zone {node_id} must have positive population."
        assert "pos" in data, f"Zone {node_id} must have map coordinates."
        assert data.get("is_synthetic") is True, f"Zone {node_id} must be labelled synthetic."
        total_pop += data["population"]
    assert total_pop == 90000, f"Expected total synthetic population 90,000, got {total_pop}."

    # Validate hospital capacities
    total_beds = 0
    for node_id in hospitals:
        data = city_graph.nodes[node_id]
        assert data.get("capacity", 0) > 0, f"Hospital {node_id} must have bed capacity."
        assert data.get("is_synthetic") is True
        total_beds += data["capacity"]
    assert total_beds == 700, f"Expected total 700 beds, got {total_beds}."

    # Validate shelter capacities
    total_shelter_cap = 0
    for node_id in shelters:
        data = city_graph.nodes[node_id]
        assert data.get("capacity", 0) > 0, f"Shelter {node_id} must have capacity."
        assert data.get("is_synthetic") is True
        total_shelter_cap += data["capacity"]
    assert total_shelter_cap == 5500, f"Expected total shelter capacity 5,500, got {total_shelter_cap}."


def test_edge_attributes_and_bridges(city_graph: nx.Graph):
    """
    Test 3: Verify road attributes, metrics, flood sensitivity, and bridge classifications.
    """
    bridge_count = 0
    for u, v, data in city_graph.edges(data=True):
        road_id = data.get("road_id")
        assert road_id is not None, f"Edge ({u}, {v}) missing road_id."
        assert data.get("distance_km", 0) > 0, f"Road {road_id} must have positive distance."
        assert data.get("travel_time_min", 0) > 0, f"Road {road_id} must have positive travel time."
        assert 0.0 <= data.get("failure_probability", -1) <= 1.0, f"Road {road_id} invalid failure probability."
        assert 0.0 <= data.get("flood_sensitivity", -1) <= 1.0, f"Road {road_id} invalid flood sensitivity."
        assert data.get("is_available") is True, f"Road {road_id} should be available by default."
        assert data.get("is_synthetic") is True, f"Road {road_id} must be flagged synthetic."

        if data.get("road_type") == "bridge":
            bridge_count += 1
            # Bridges in flood zones should have high flood sensitivity
            assert data["flood_sensitivity"] >= 0.70, f"Bridge {road_id} expected high flood sensitivity."

    assert bridge_count == 3, f"Expected 3 synthetic bridges, found {bridge_count}."


def test_city_summary_structure(city_graph: nx.Graph):
    """
    Test 4: Verify that get_city_summary() returns the expected dictionary structure.
    """
    summary = get_city_summary(city_graph)
    assert summary["is_synthetic"] is True
    assert summary["total_nodes"] == 16
    assert summary["total_edges"] == 20
    assert summary["residential_zones_count"] == 6
    assert summary["total_population"] == 90000
    assert summary["hospitals_count"] == 2
    assert summary["total_hospital_beds"] == 700
    assert summary["shelters_count"] == 2
    assert summary["total_shelter_capacity"] == 5500
    assert summary["bridges_count"] == 3
    assert summary["is_fully_connected_initially"] is True


def test_dataframe_and_json_serialization(city_graph: nx.Graph, tmp_path):
    """
    Test 5: Verify tabular export (DataFrames) and file serialization (JSON)
    for seamless integration with Member 3 and Member 4.
    """
    # 1. Pandas DataFrame Export
    nodes_df, edges_df = export_city_to_dataframes(city_graph)
    assert len(nodes_df) == 16, "Nodes DataFrame must contain 16 rows."
    assert len(edges_df) == 20, "Edges DataFrame must contain 20 rows."
    assert "population" in nodes_df.columns
    assert "pos_x" in nodes_df.columns
    assert "road_id" in edges_df.columns

    # 2. JSON Export & Re-import
    json_path = os.path.join(tmp_path, "test_city.json")
    save_city_to_json(city_graph, json_path)
    assert os.path.exists(json_path), "JSON export file must exist on disk."

    reloaded_graph = load_city_from_json(json_path)
    assert reloaded_graph.number_of_nodes() == city_graph.number_of_nodes()
    assert reloaded_graph.number_of_edges() == city_graph.number_of_edges()
    assert nx.is_connected(reloaded_graph)


# -----------------------------------------------------------------------------
# PRIORITY 2: INFRASTRUCTURE VULNERABILITY ANALYSIS TESTS
# -----------------------------------------------------------------------------

from resilience import (
    calculate_edge_centrality,
    identify_critical_bridges,
    analyze_road_vulnerability,
    rank_critical_roads,
)


def test_calculate_edge_centrality(city_graph: nx.Graph):
    """
    Test 6: Verify Edge Betweenness Centrality computation.
    - All 20 roads must have a calculated centrality score.
    - Scores must fall within [0.0, 1.0].
    - Major transit bottlenecks (like Grand River Bridge RD11) should have high centrality.
    """
    centrality_map = calculate_edge_centrality(city_graph)
    assert len(centrality_map) == 20, "All 20 roads must have a centrality value."

    for road_id, score in centrality_map.items():
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0, f"Centrality for {road_id} must be bounded between 0 and 1."

    # Grand River Bridge RD11 (J1 <-> J2) is the primary east-west spine
    assert centrality_map["RD11"] > 0.20, "Grand River Bridge must have high centrality."


def test_identify_critical_bridges_distinction(city_graph: nx.Graph):
    """
    Test 7: Verify identification and distinction between graph-theoretic cut edges
    and physical structural bridges.
    """
    # 1. Test cut-edge return list
    cut_edges = identify_critical_bridges(city_graph, return_classification=False)
    assert isinstance(cut_edges, list)
    # RD04 (J4 <-> R3) is the sole access road to Hilltop Suburb, making it a graph cut-edge
    assert "RD04" in cut_edges, "RD04 must be detected as a graph-theoretic cut edge."

    # 2. Test detailed classification
    details = identify_critical_bridges(city_graph, return_classification=True)
    assert "graph_theoretic_bridges" in details
    assert "structural_bridges" in details
    assert "both_structural_and_cut_edge" in details

    assert "RD04" in details["graph_theoretic_bridges"]
    # Physical bridges across water: RD11, RD14, RD19
    for b_id in ["RD11", "RD14", "RD19"]:
        assert b_id in details["structural_bridges"], f"{b_id} must be classified as a structural bridge."


def test_analyze_road_vulnerability(city_graph: nx.Graph):
    """
    Test 8: Verify comprehensive vulnerability dataframe generation.
    """
    df = analyze_road_vulnerability(city_graph)
    assert len(df) == 20, "Vulnerability table must evaluate all 20 roads."
    
    required_columns = {
        "road_id",
        "name",
        "source",
        "destination",
        "road_type",
        "distance_km",
        "travel_time_min",
        "failure_probability",
        "flood_sensitivity",
        "edge_betweenness",
        "is_structural_bridge",
        "is_graph_bridge",
        "explanation",
    }
    assert required_columns.issubset(set(df.columns)), "Missing required vulnerability metrics."
    assert df["is_structural_bridge"].sum() == 3, "Expected 3 structural bridges in DataFrame."
    assert df["is_graph_bridge"].sum() == 1, "Expected 1 graph cut edge (RD04) in DataFrame."


def test_rank_critical_roads_and_graph_preservation(city_graph: nx.Graph):
    """
    Test 9: Verify critical road ranking, scoring transparency, and original graph preservation.
    """
    initial_node_count = city_graph.number_of_nodes()
    initial_edge_count = city_graph.number_of_edges()

    df_ranked = rank_critical_roads(city_graph)
    assert len(df_ranked) == 20

    # Ensure ranking is sorted descending
    scores = df_ranked["criticality_score"].tolist()
    assert scores == sorted(scores, reverse=True), "Roads must be ordered by criticality_score descending."

    # Ensure critical levels are valid
    valid_levels = {"CRITICAL", "HIGH", "MODERATE", "LOW"}
    assert set(df_ranked["criticality_level"]).issubset(valid_levels)

    # Highly vulnerable river bridges should be at the top of the criticality ranking
    top_road_ids = df_ranked.head(3)["road_id"].tolist()
    assert any(rid in ["RD11", "RD14", "RD19"] for rid in top_road_ids), "River bridges must rank among top critical roads."

    # Verify original graph was NOT modified during analysis
    assert city_graph.number_of_nodes() == initial_node_count, "Original graph nodes must not change."
    assert city_graph.number_of_edges() == initial_edge_count, "Original graph edges must not change."


# -----------------------------------------------------------------------------
# PRIORITY 3: ROAD FAILURE SIMULATION TESTS
# -----------------------------------------------------------------------------

from resilience import (
    simulate_road_failure,
    simulate_multiple_failures,
    get_disconnected_zones,
    get_isolated_facilities,
)


def test_simulate_road_failure_valid(city_graph: nx.Graph):
    """
    Test 10: Valid single road failure simulation.
    Simulating failure on cut-edge RD04 (Hilltop Access Road) must partition the graph.
    """
    report = simulate_road_failure(city_graph, "RD04")

    assert report["scenario_id"] == "SCENARIO_SINGLE_FAIL_RD04"
    assert report["failed_road_ids"] == ["RD04"]
    assert report["original_edge_count"] == 20
    assert report["scenario_edge_count"] == 19
    assert report["connected_component_count"] == 2
    assert "R3" in report["disconnected_residential_zones"]
    assert "R3" in report["no_hospital_access_zones"]
    assert "R3" in report["no_shelter_access_zones"]
    assert report["is_original_graph_unchanged"] is True


def test_simulate_road_failure_invalid_id(city_graph: nx.Graph):
    """
    Test 11: Invalid road ID handling.
    Simulating failure on a non-existent road ID must raise a ValueError.
    """
    with pytest.raises(ValueError, match="not found in the city network"):
        simulate_road_failure(city_graph, "INVALID_ROAD_999")


def test_simulate_multiple_failures_and_deduplication(city_graph: nx.Graph):
    """
    Test 12: Multiple simultaneous road failures.
    Simulating failure on both access roads to Riverside (RD01 & RD02) with duplicate IDs.
    """
    # Passing duplicate 'RD01' to verify robust deduplication
    report = simulate_multiple_failures(city_graph, ["RD01", "RD02", "RD01"])

    assert report["failed_road_ids"] == ["RD01", "RD02"]
    assert report["original_edge_count"] == 20
    assert report["scenario_edge_count"] == 18
    assert report["connected_component_count"] >= 2
    assert "R1" in report["disconnected_residential_zones"]
    assert "R1" in report["no_hospital_access_zones"]
    assert "R1" in report["no_shelter_access_zones"]
    assert report["is_original_graph_unchanged"] is True

    # Test ignore_invalid=True parameter
    lenient_report = simulate_multiple_failures(
        city_graph, ["RD01", "NON_EXISTENT_ID"], ignore_invalid=True
    )
    assert lenient_report["failed_road_ids"] == ["RD01"]
    assert "NON_EXISTENT_ID" in lenient_report["invalid_road_ids"]


def test_original_graph_preservation(city_graph: nx.Graph):
    """
    Test 13: Strict preservation of the baseline city graph across multiple simulations.
    """
    nodes_before = city_graph.number_of_nodes()
    edges_before = city_graph.number_of_edges()

    # Run three severe failure simulations sequentially
    _ = simulate_road_failure(city_graph, "RD04")
    _ = simulate_road_failure(city_graph, "RD11")
    _ = simulate_multiple_failures(city_graph, ["RD01", "RD02", "RD14", "RD19"])

    # Ensure baseline graph G was never modified
    assert city_graph.number_of_nodes() == nodes_before == 16
    assert city_graph.number_of_edges() == edges_before == 20
    assert nx.is_connected(city_graph) is True


def test_get_disconnected_zones_service_distinction(city_graph: nx.Graph):
    """
    Test 14: Verifies that component partitioning is not confused with service isolation
    when independent services exist in both components.
    """
    # Case 1: Failure of Grand River Bridge RD11 alone does NOT disconnect any zones from services
    report_rd11 = simulate_road_failure(city_graph, "RD11")
    assert report_rd11["connected_component_count"] == 1  # Alternative routes keep city connected
    assert len(report_rd11["no_hospital_access_zones"]) == 0
    assert len(report_rd11["no_shelter_access_zones"]) == 0

    # Case 2: Partitioning East and West (RD11, RD17, RD19 fail)
    report_split = simulate_multiple_failures(city_graph, ["RD11", "RD17", "RD19"])
    assert report_split["connected_component_count"] == 2
    # West component has H1 and S1. East component has H2 and S2.
    # Therefore, no residential zone is without hospital or shelter access!
    assert len(report_split["no_hospital_access_zones"]) == 0
    assert len(report_split["no_shelter_access_zones"]) == 0


def test_facility_isolation_detection(city_graph: nx.Graph):
    """
    Test 15: Detection of stranded or isolated hospitals, shelters, and stations.
    """
    # Sever all access roads connecting to Hospital H2 (RD13: R5-H2 and RD20: R4-H2)
    report = simulate_multiple_failures(city_graph, ["RD13", "RD20"])
    assert "H2" in report["isolated_hospitals"], "H2 must be detected as an isolated hospital."


# -----------------------------------------------------------------------------
# PRIORITY 4: HUMAN IMPACT ESTIMATION TESTS
# -----------------------------------------------------------------------------

from resilience import (
    calculate_baseline_travel_times,
    estimate_human_impact,
    evaluate_all_roads_human_impact,
)


def test_calculate_baseline_travel_times(city_graph: nx.Graph):
    """
    Test 16: Verify baseline pre-disaster travel times calculation.
    """
    baselines = calculate_baseline_travel_times(city_graph)
    assert len(baselines) == 6, "All 6 residential zones must have baseline travel times."

    for zone_id, times in baselines.items():
        assert times["hospital_time_min"] is not None
        assert times["shelter_time_min"] is not None
        assert times["hospital_time_min"] > 0
        assert times["shelter_time_min"] > 0

    # R2 (Downtown Heights) connects directly to H1 via RD10 (3.5 min)
    assert baselines["R2"]["hospital_time_min"] == 3.5


def test_estimate_human_impact_single_cut_edge(city_graph: nx.Graph):
    """
    Test 17: Human impact calculation on RD04 (Hilltop Suburb cut edge).
    Verifies exact population figures and strict non-double-counting.
    """
    impact = estimate_human_impact(city_graph, "RD04")

    # Hilltop Suburb population = 9,500
    assert impact["population_no_hospital_access"] == 9500
    assert impact["population_no_shelter_access"] == 9500

    # STRICT NON-DOUBLE-COUNTING ASSERTION:
    # Population losing hospital OR shelter must be 9,500, NOT (9,500 + 9,500 = 19,000)
    assert impact["unique_population_lost_critical_service"] == 9500

    # Risk Score = Failure Probability (0.10) * Human Impact (9,500) = 950.0
    assert impact["failure_probability"] == 0.10
    assert impact["risk_score"] == 950.0
    assert "scientific_disclaimer" in impact


def test_estimate_human_impact_compound_disaster(city_graph: nx.Graph):
    """
    Test 18: Human impact under compound failure (RD01 & RD02 both fail).
    Isolates R1 (Riverside Colony, 14,000 residents).
    """
    impact = estimate_human_impact(city_graph, ["RD01", "RD02"])

    assert impact["population_no_hospital_access"] == 14000
    assert impact["population_no_shelter_access"] == 14000
    assert impact["unique_population_lost_critical_service"] == 14000
    # Effective failure probability is max(0.65, 0.70) = 0.70
    assert impact["failure_probability"] == 0.70
    assert impact["risk_score"] == round(0.70 * 14000, 2)


def test_estimate_human_impact_hospital_delays(city_graph: nx.Graph):
    """
    Test 19: Detour & travel time delay quantification when RD10 fails.
    """
    impact = estimate_human_impact(city_graph, "RD10")

    # Zero citizens lose complete hospital access because alternative routes exist
    assert impact["unique_population_lost_critical_service"] == 0

    # However, R2 (Downtown Heights, 28,000) and R1 (14,000) experience detours!
    assert impact["population_with_delayed_hospital_access"] == 42000
    r2_delay = impact["delays_by_zone"]["R2"]["hospital_delay_min"]
    assert r2_delay > 10.0, "R2 must experience significant hospital delay when RD10 fails."


def test_evaluate_all_roads_human_impact_table(city_graph: nx.Graph):
    """
    Test 20: Comprehensive tabular evaluation of human impact across all roads.
    """
    df = evaluate_all_roads_human_impact(city_graph)
    assert len(df) == 20, "All 20 roads must be evaluated."
    assert "risk_score" in df.columns
    assert "unique_pop_lost_service" in df.columns
    assert "pop_hospital_delay" in df.columns
    # Ensure sorted primarily by risk_score
    assert df.iloc[0]["road_id"] == "RD04", "RD04 must have highest single-road risk score."


# -----------------------------------------------------------------------------
# PRIORITY 5: CRITICAL ROAD RANKING TESTS
# -----------------------------------------------------------------------------

import json
from resilience import (
    generate_critical_road_ranking,
    export_critical_road_ranking,
)


def test_generate_critical_road_ranking_structure(city_graph: nx.Graph):
    """
    Test 21: Verify unified critical road ranking dataframe structure and sorting.
    """
    df = generate_critical_road_ranking(city_graph)
    assert len(df) == 20, "All 20 roads must be ranked."

    required_columns = [
        "road_id",
        "name",
        "road_type",
        "failure_probability",
        "population_affected",
        "population_disconnected",
        "population_delayed",
        "risk_score",
        "criticality_score",
        "criticality_level",
        "explanation",
    ]
    for col in required_columns:
        assert col in df.columns, f"Missing required column: {col}"

    # Ensure sorted descending
    scores = df["criticality_score"].tolist()
    assert scores == sorted(scores, reverse=True), "Must be sorted by criticality_score descending."

    # Validate that both cut edge (RD04) and major river bridge (RD11) are recognized as CRITICAL
    critical_roads = df[df["criticality_level"] == "CRITICAL"]["road_id"].tolist()
    assert "RD04" in critical_roads, "RD04 must be marked CRITICAL due to complete population isolation."
    assert "RD11" in critical_roads, "RD11 must be marked CRITICAL due to river crossing vulnerability and centrality."


def test_population_affected_arithmetic(city_graph: nx.Graph):
    """
    Test 22: Asserts that total affected population is the exact sum of disconnected and delayed citizens.
    """
    df = generate_critical_road_ranking(city_graph)
    for _, row in df.iterrows():
        expected_affected = row["population_disconnected"] + row["population_delayed"]
        assert row["population_affected"] == expected_affected, "Affected population arithmetic mismatch."


def test_export_critical_road_ranking_disk_files(city_graph: nx.Graph, tmp_path):
    """
    Test 23: Verifies serialization to JSON and CSV files on disk.
    """
    json_file = str(tmp_path / "test_ranking.json")
    csv_file = str(tmp_path / "test_ranking.csv")

    df = export_critical_road_ranking(city_graph, json_path=json_file, csv_path=csv_file)
    assert os.path.exists(json_file)
    assert os.path.exists(csv_file)

    # Check JSON structure
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["is_synthetic"] is True
    assert data["total_ranked_roads"] == 20
    assert len(data["roads"]) == 20



# -----------------------------------------------------------------------------
# PRIORITY 5: COMPREHENSIVE CRITICAL ROAD RANKING TESTS
# -----------------------------------------------------------------------------

from resilience import (
    rank_critical_roads_comprehensive,
    export_comprehensive_ranking,
)


def test_comprehensive_ranking_columns_and_sorting(city_graph: nx.Graph):
    """
    Test 24: Verifies that rank_critical_roads_comprehensive contains all 19 required columns
    and is strictly sorted descending by comprehensive_criticality_score.
    """
    df = rank_critical_roads_comprehensive(city_graph)
    assert len(df) == 20, "Must rank all 20 roads."

    expected_columns = [
        "road_id",
        "road_name",
        "road_type",
        "failure_probability",
        "flood_sensitivity",
        "edge_betweenness",
        "is_structural_bridge",
        "is_graph_bridge",
        "population_no_hospital_access",
        "population_no_shelter_access",
        "unique_population_losing_access",
        "population_with_delayed_hospital_access",
        "max_hospital_delay_min",
        "access_loss_risk_score",
        "delay_impact_score",
        "infrastructure_vulnerability_score",
        "comprehensive_criticality_score",
        "criticality_level",
        "explanation",
    ]
    for col in expected_columns:
        assert col in df.columns, f"Missing required column: {col}"

    # Verify descending sort
    scores = df["comprehensive_criticality_score"].tolist()
    assert scores == sorted(scores, reverse=True), "Must be sorted descending by comprehensive_criticality_score."


def test_comprehensive_ranking_rd04_and_rd10_evaluation(city_graph: nx.Graph):
    """
    Test 25: Validates both distinct risk archetypes:
    1. RD04: Acute access-loss isolation (9,500 residents cut off).
    2. RD10: Severe medical delay impact (42,000 residents delayed by +14.9m).
    Neither road must be classified as harmless/low-risk. Both must be CRITICAL.
    """
    df = rank_critical_roads_comprehensive(city_graph)
    row_rd04 = df[df["road_id"] == "RD04"].iloc[0]
    row_rd10 = df[df["road_id"] == "RD10"].iloc[0]

    # RD04 validation
    assert row_rd04["unique_population_losing_access"] == 9500
    assert row_rd04["access_loss_risk_score"] == 1.0
    assert row_rd04["criticality_level"] == "CRITICAL"
    assert "single point of failure" in row_rd04["explanation"]

    # RD10 validation: Must NOT be treated as harmless!
    assert row_rd10["unique_population_losing_access"] == 0
    assert row_rd10["population_with_delayed_hospital_access"] == 42000
    assert row_rd10["max_hospital_delay_min"] >= 14.0
    assert row_rd10["delay_impact_score"] > 0.90
    assert row_rd10["criticality_level"] == "CRITICAL"
    assert "medical lifeline" in row_rd10["explanation"]


def test_comprehensive_ranking_score_normalization(city_graph: nx.Graph):
    """
    Test 26: Validates that every individual sub-score and the composite score
    are properly normalized strictly between 0.0 and 1.0 without dimension distortion.
    """
    df = rank_critical_roads_comprehensive(city_graph)

    score_columns = [
        "access_loss_risk_score",
        "delay_impact_score",
        "infrastructure_vulnerability_score",
        "comprehensive_criticality_score",
    ]
    for col in score_columns:
        for val in df[col]:
            assert 0.0 <= val <= 1.0, f"Score {col} value {val} out of bounds [0.0, 1.0]."

    valid_levels = {"CRITICAL", "HIGH", "MODERATE", "LOW"}
    assert set(df["criticality_level"]).issubset(valid_levels)


def test_comprehensive_ranking_export_files(city_graph: nx.Graph, tmp_path):
    """
    Test 27: Validates that CSV and JSON exports match schema requirements.
    """
    csv_file = str(tmp_path / "critical_road_ranking.csv")
    json_file = str(tmp_path / "critical_road_ranking.json")

    df = export_comprehensive_ranking(city_graph, csv_path=csv_file, json_path=json_file)
    assert os.path.exists(csv_file)
    assert os.path.exists(json_file)

    # Validate JSON content
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["is_synthetic"] is True
    assert data["total_ranked_roads"] == 20
    assert "scoring_methodology" in data
    assert len(data["roads"]) == 20



# -----------------------------------------------------------------------------
# PRIORITY 6: EMERGENCY RESOURCE POSITIONING TESTS
# -----------------------------------------------------------------------------

from resilience import (
    identify_candidate_locations,
    recommend_ambulance_positions,
    recommend_boat_positions,
    recommend_rescue_team_positions,
    recommend_supply_positions,
    generate_resource_plan,
    export_resource_plan,
)


def test_candidate_location_identification(city_graph: nx.Graph):
    """
    Test 28: Verifies filtering and suitability criteria across all 4 resource types.
    """
    amb_cands = identify_candidate_locations(city_graph, "ambulances")
    boat_cands = identify_candidate_locations(city_graph, "boats")
    team_cands = identify_candidate_locations(city_graph, "rescue_teams")
    sup_cands = identify_candidate_locations(city_graph, "emergency_supplies")

    assert len(amb_cands) >= 3, "Expected multiple ambulance candidate hubs."
    assert any(c["node_id"] == "E1" for c in amb_cands), "E1 must be an ambulance candidate."

    # Boats must target high flood exposure zones (R1, R6, R5) or river bases (E2)
    assert any(c["node_id"] == "R1" for c in boat_cands)
    assert any(c["node_id"] == "E2" for c in boat_cands)

    # Supplies must include isolated community R3 (Hilltop Suburb) and shelters S1, S2
    assert any(c["node_id"] == "R3" for c in sup_cands), "R3 must be an emergency supply candidate due to cut-edge isolation."
    assert any(c["node_id"] == "S1" for c in sup_cands)


def test_invalid_resource_type_handling(city_graph: nx.Graph):
    """
    Test 29: Verifies that invalid resource types raise ValueError.
    """
    with pytest.raises(ValueError, match="Invalid resource_type"):
        identify_candidate_locations(city_graph, "helicopters")

    with pytest.raises(ValueError, match="Invalid resource_type"):
        identify_candidate_locations(city_graph, "submarines")


def test_ambulance_recommendations_and_configurability(city_graph: nx.Graph):
    """
    Test 30: Validates ambulance recommendations and configurable count parameter.
    """
    recs_default = recommend_ambulance_positions(city_graph, count=4)
    assert len(recs_default) == 4, "Must return exactly 4 recommendations."

    # Configurable count test
    recs_custom = recommend_ambulance_positions(city_graph, count=2)
    assert len(recs_custom) == 2, "Configurable count parameter must be respected."

    # Top recommendation should be Central Hub E1
    assert recs_default[0]["recommended_node_id"] == "E1"
    assert recs_default[0]["confidence_or_suitability_score"] >= 0.80
    assert "ambulances" == recs_default[0]["resource_type"]


def test_boat_recommendations_and_assumptions(city_graph: nx.Graph):
    """
    Test 31: Validates boat positioning in flood zones and explicit assumption labeling.
    """
    recs = recommend_boat_positions(city_graph, count=3)
    assert len(recs) == 3

    staged_nodes = [r["recommended_node_id"] for r in recs]
    # Westside river depot E2 and Riverside R1 must be in top boat staging locations
    assert "E2" in staged_nodes
    assert "R1" in staged_nodes

    # Explicit scientific assumption verification
    for r in recs:
        assert "Assumption:" in r["assumptions"], "Boats must explicitly declare water access assumptions."
        assert 0.0 <= r["confidence_or_suitability_score"] <= 1.0


def test_rescue_team_recommendations(city_graph: nx.Graph):
    """
    Test 32: Validates rescue team positioning across stations and shelters.
    """
    recs = recommend_rescue_team_positions(city_graph, count=4)
    assert len(recs) == 4

    staged_nodes = [r["recommended_node_id"] for r in recs]
    assert "E1" in staged_nodes
    assert "E2" in staged_nodes
    assert "S1" in staged_nodes


def test_supply_recommendations_prioritizes_isolated_r3(city_graph: nx.Graph):
    """
    Test 33: Validates that Hilltop Suburb (R3) receives highest priority for pre-stockpiling
    food/water due to single-point-of-failure cut edge RD04.
    """
    recs = recommend_supply_positions(city_graph, count=4)
    assert len(recs) == 4

    # R3 must be the #1 recommendation for supplies
    top_supply = recs[0]
    assert top_supply["recommended_node_id"] == "R3", "R3 must be the highest priority for emergency supplies."
    assert "cut-edge" in top_supply["reason"] or "RD04" in top_supply["reason"]


def test_unreachable_node_handling(city_graph: nx.Graph):
    """
    Test 34: Verifies that an isolated/unreachable node (degree 0) is never recommended.
    """
    G_isolated = city_graph.copy()
    G_isolated.add_node("ISLAND_99", type="residential", population=5000, flood_exposure="high")
    assert G_isolated.degree("ISLAND_99") == 0

    boat_cands = identify_candidate_locations(G_isolated, "boats")
    assert not any(c["node_id"] == "ISLAND_99" for c in boat_cands), "Unreachable node must be screened out."


def test_generate_resource_plan_and_export(city_graph: nx.Graph, tmp_path):
    """
    Test 35: Verifies end-to-end plan generation, original graph preservation, and export to CSV/JSON.
    """
    nodes_before = city_graph.number_of_nodes()
    edges_before = city_graph.number_of_edges()

    custom_inventory = {
        "ambulances": 3,
        "boats": 2,
        "rescue_teams": 3,
        "emergency_supplies": 3,
    }
    plan = generate_resource_plan(city_graph, inventory=custom_inventory)
    assert plan["total_resources_allocated"] == 11
    assert len(plan["recommendations"]) == 11
    assert "summary_by_node" in plan

    # File export test
    csv_file = str(tmp_path / "test_resources.csv")
    json_file = str(tmp_path / "test_resources.json")
    df, exported_plan = export_resource_plan(city_graph, inventory=custom_inventory, json_path=json_file, csv_path=csv_file)

    assert os.path.exists(csv_file)
    assert os.path.exists(json_file)
    assert len(df) == 11

    # Strict non-mutation check
    assert city_graph.number_of_nodes() == nodes_before == 16
    assert city_graph.number_of_edges() == edges_before == 20



# -----------------------------------------------------------------------------
# PRIORITY 7: UNIFIED INTEGRATION PIPELINE & STRUCTURED OUTPUTS TESTS
# -----------------------------------------------------------------------------

from main import run_pipeline


def test_pipeline_execution_and_manifest(tmp_path):
    """
    Test 36: Verifies master pipeline execution, status, and manifest completeness.
    """
    out_dir = str(tmp_path / "test_pipeline_outputs")
    manifest = run_pipeline(output_dir=out_dir)

    assert manifest["status"] == "SUCCESS"
    assert manifest["is_original_graph_unchanged"] is True
    assert manifest["total_files_generated"] == 14
    assert len(manifest["generated_files"]) == 14


def test_pipeline_output_files_existence(tmp_path):
    """
    Test 37: Verifies that all 14 required files are written to disk.
    """
    out_dir = str(tmp_path / "test_files_outputs")
    manifest = run_pipeline(output_dir=out_dir)

    expected_basenames = [
        "city_summary.json",
        "baseline_city_network.json",
        "rd04_failure_scenario.json",
        "rd11_failure_scenario.json",
        "human_impact_results.csv",
        "critical_road_ranking.csv",
        "critical_road_ranking.json",
        "resource_positioning_plan.csv",
        "resource_positioning_plan.json",
        "viz_city_network.png",
        "viz_critical_roads.png",
        "viz_rd04_failure.png",
        "viz_rd11_failure.png",
        "viz_resource_plan.png",
    ]
    for bname in expected_basenames:
        fpath = os.path.join(out_dir, bname)
        assert os.path.exists(fpath), f"Required pipeline output file missing: {bname}"
        assert os.path.getsize(fpath) > 0, f"Output file is empty: {bname}"


def test_pipeline_valid_json_outputs(tmp_path):
    """
    Test 38: Verifies that all JSON outputs are parseable and conform to required structure.
    """
    out_dir = str(tmp_path / "test_json_outputs")
    run_pipeline(output_dir=out_dir)

    json_files = [
        "city_summary.json",
        "baseline_city_network.json",
        "rd04_failure_scenario.json",
        "rd11_failure_scenario.json",
        "critical_road_ranking.json",
        "resource_positioning_plan.json",
    ]
    for jfile in json_files:
        fpath = os.path.join(out_dir, jfile)
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict), f"{jfile} must contain a JSON root object."


def test_pipeline_non_empty_csv_outputs(tmp_path):
    """
    Test 39: Verifies that CSV files are readable by pandas and contain expected row counts.
    """
    out_dir = str(tmp_path / "test_csv_outputs")
    run_pipeline(output_dir=out_dir)

    df_crit = pd.read_csv(os.path.join(out_dir, "critical_road_ranking.csv"))
    assert len(df_crit) == 20, "critical_road_ranking.csv must contain 20 rows."
    assert "comprehensive_criticality_score" in df_crit.columns

    df_human = pd.read_csv(os.path.join(out_dir, "human_impact_results.csv"))
    assert len(df_human) == 20, "human_impact_results.csv must contain 20 rows."

    df_res = pd.read_csv(os.path.join(out_dir, "resource_positioning_plan.csv"))
    assert len(df_res) >= 10, "resource_positioning_plan.csv must contain recommendations."
    assert "resource_type" in df_res.columns


def test_pipeline_scenario_separation(tmp_path):
    """
    Test 40: Verifies that Scenario A (RD04) and Scenario B (RD11) are distinctly recorded.
    """
    out_dir = str(tmp_path / "test_scenario_outputs")
    run_pipeline(output_dir=out_dir)

    with open(os.path.join(out_dir, "rd04_failure_scenario.json"), "r", encoding="utf-8") as f:
        data_rd04 = json.load(f)
    with open(os.path.join(out_dir, "rd11_failure_scenario.json"), "r", encoding="utf-8") as f:
        data_rd11 = json.load(f)

    # Scenario A (RD04) partitions the city
    assert data_rd04["failed_road_ids"] == ["RD04"]
    assert data_rd04["connected_component_count"] == 2
    assert "R3" in data_rd04["disconnected_residential_zones"]
    assert data_rd04["human_impact"]["unique_population_lost_critical_service"] == 9500

    # Scenario B (RD11) does NOT partition the city due to alternative routes
    assert data_rd11["failed_road_ids"] == ["RD11"]
    assert data_rd11["connected_component_count"] == 1
    assert len(data_rd11["disconnected_residential_zones"]) == 0
    assert data_rd11["human_impact"]["unique_population_lost_critical_service"] == 0


def test_pipeline_visualizations_generation(tmp_path):
    """
    Test 41: Verifies that all 5 PNG visual maps are generated and have valid image sizes.
    """
    out_dir = str(tmp_path / "test_viz_outputs")
    run_pipeline(output_dir=out_dir)

    png_files = [
        "viz_city_network.png",
        "viz_critical_roads.png",
        "viz_rd04_failure.png",
        "viz_rd11_failure.png",
        "viz_resource_plan.png",
    ]
    for png in png_files:
        fpath = os.path.join(out_dir, png)
        assert os.path.exists(fpath)
        # Check that PNG file is non-trivial in size (at least 50 KB)
        assert os.path.getsize(fpath) > 50000, f"{png} image size too small."


def test_pipeline_idempotency_and_preservation(tmp_path):
    """
    Test 42: Verifies that running the pipeline repeatedly is completely idempotent
    and never mutates the underlying baseline graph.
    """
    out_dir = str(tmp_path / "test_repeat_outputs")
    run1 = run_pipeline(output_dir=out_dir)
    run2 = run_pipeline(output_dir=out_dir)

    assert run1["status"] == run2["status"] == "SUCCESS"
    assert run1["total_files_generated"] == run2["total_files_generated"] == 14
