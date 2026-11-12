import sys
from pathlib import Path

import networkx as nx
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sanjeevani.decision import (
    evaluate_emergency_access,
    estimate_edge_travel_time_sec,
    find_shortest_safe_route,
    find_alternative_route,
    optimize_multi_destination_routes,
    allocate_emergency_resources,
    compare_rescue_strategies,
    plan_active_observations,
)


def _build_sample_rescue_network():
    g = nx.MultiDiGraph()

    # Fast primary corridor: A -> B -> D (total 300m, primary 45 km/h)
    g.add_edge(
        "A", "B",
        road_id="R_PRIMARY_1",
        name="MG Road",
        highway="primary",
        length_m=150.0,
        condition="OPEN",
        available=True,
    )
    g.add_edge(
        "B", "D",
        road_id="R_PRIMARY_2",
        name="Brigade Link",
        highway="primary",
        length_m=150.0,
        condition="OPEN",
        available=True,
    )

    # Alternative secondary corridor: A -> C -> D (total 450m, secondary)
    g.add_edge(
        "A", "C",
        road_id="R_ALT_1",
        name="Residency Road",
        highway="secondary",
        length_m=220.0,
        condition="OPEN",
        available=True,
    )
    g.add_edge(
        "C", "D",
        road_id="R_ALT_2",
        name="Museum Cross",
        highway="secondary",
        length_m=230.0,
        condition="OPEN",
        available=True,
    )

    # One-way reverse road: D -> E only (cannot go E -> D)
    g.add_edge(
        "D", "E",
        road_id="R_ONEWAY",
        highway="tertiary",
        oneway="forward",
        length_m=120.0,
        condition="OPEN",
        available=True,
    )

    # Disconnected node Z
    g.add_node("Z", x=77.65, y=12.99)

    return g


def test_normal_routing_and_parallel_edges():
    g = _build_sample_rescue_network()

    # Add a slower parallel service road between A and B
    g.add_edge(
        "A", "B",
        road_id="R_PARALLEL_SLOW",
        highway="service",
        access="private",
        length_m=300.0,
        condition="OPEN",
        available=True,
    )

    route = find_shortest_safe_route(g, "A", "D", optimize_for="time")
    assert route["reachable"] is True
    assert route["nodes"] == ["A", "B", "D"]
    assert route["road_ids"] == ["R_PRIMARY_1", "R_PRIMARY_2"]
    assert route["total_distance_m"] == 300.0
    assert route["route_safety_status"] == "SAFE_OPEN"


def test_avoid_blocked_roads_and_alternative_route():
    g = _build_sample_rescue_network()

    # Generate primary + alternative when both corridors are open
    both = find_alternative_route(g, "A", "D", optimize_for="time")
    assert both["primary_route"]["nodes"] == ["A", "B", "D"]
    assert both["alternative_route"]["reachable"] is True
    assert both["alternative_route"]["is_distinct_from_primary"] is True
    assert both["alternative_route"]["nodes"] == ["A", "C", "D"]

    # Block B -> D due to heavy flooding
    g["B"]["D"][0]["condition"] = "BLOCKED"
    g["B"]["D"][0]["available"] = False

    rerouted = find_shortest_safe_route(g, "A", "D", optimize_for="time")
    assert rerouted["reachable"] is True
    assert rerouted["nodes"] == ["A", "C", "D"]
    assert "R_PRIMARY_2" not in rerouted["road_ids"]


def test_oneway_and_disconnected_no_route():
    g = _build_sample_rescue_network()

    # D -> E is allowed
    forward_route = find_shortest_safe_route(g, "D", "E")
    assert forward_route["reachable"] is True
    assert forward_route["nodes"] == ["D", "E"]

    # E -> D violates one-way direction -> no route
    reverse_route = find_shortest_safe_route(g, "E", "D")
    assert reverse_route["reachable"] is False
    assert reverse_route["route_safety_status"] == "NO_SAFE_ROUTE"

    # Disconnected node Z -> no route
    disc_route = find_shortest_safe_route(g, "A", "Z")
    assert disc_route["reachable"] is False
    assert disc_route["total_distance_m"] is None


def test_emergency_access_restrictions_and_uncertainty():
    # Prohibited road (access=no without emergency=yes)
    prohibited = evaluate_emergency_access({"highway": "residential", "access": "no"})
    assert prohibited["passable"] is False

    # Verified emergency override on access=no road
    verified = evaluate_emergency_access(
        {"highway": "service", "access": "no", "emergency": "yes"}
    )
    assert verified["passable"] is True
    assert verified["uncertain"] is False

    # Private gated road is flagged as uncertain emergency access
    uncertain = evaluate_emergency_access({"highway": "residential", "access": "private"})
    assert uncertain["passable"] is True
    assert uncertain["uncertain"] is True

    g = nx.MultiDiGraph()
    g.add_edge(
        "X", "Y",
        road_id="R_PRIVATE",
        highway="residential",
        access="private",
        length_m=100.0,
        condition="OPEN",
        available=True,
    )

    # Allowed with warning when allow_uncertain_access=True
    r_allowed = find_shortest_safe_route(g, "X", "Y", allow_uncertain_access=True)
    assert r_allowed["reachable"] is True
    assert r_allowed["uncertain_access_segments_count"] == 1

    # Rejected when strict verified/public access is required
    r_strict = find_shortest_safe_route(g, "X", "Y", allow_uncertain_access=False)
    assert r_strict["reachable"] is False


def test_multi_destination_routing():
    g = _build_sample_rescue_network()
    multi = optimize_multi_destination_routes(g, "A", ["B", "D", "E", "Z"])

    assert multi["destinations_count"] == 4
    assert multi["reachable_count"] == 3
    assert multi["unreachable_count"] == 1
    assert multi["routes"]["E"]["reachable"] is True
    assert multi["routes"]["Z"]["reachable"] is False


def test_resource_allocation_budget_and_insufficient_resources():
    locations = [
        {
            "location_id": "LOC_NEAR_LOW",
            "name": "Low Priority Nearby",
            "priority": 2.0,
            "affected_population": 100,
            "distance_m": 500.0,
        },
        {
            "location_id": "LOC_CRITICAL_HOSP",
            "name": "Critical Flooded Hospital Zone",
            "priority": 10.0,
            "affected_population": 250,
            "distance_m": 2500.0,
        },
        {
            "location_id": "LOC_FAR_MED",
            "name": "Medium Priority Ward",
            "priority": 5.0,
            "affected_population": 200,
            "distance_m": 4000.0,
        },
    ]

    resources = [
        {
            "resource_id": "BOAT_TEAM",
            "resource_type": "rescue_boat",
            "units": 3,
            "capacity_per_unit": 100,
            "cost_per_unit": 500.0,
            "speed_kmh": 25.0,
        }
    ]

    # Tight budget of 1000 allows only 2 units (200 capacity total against 550 demand)
    alloc = allocate_emergency_resources(
        locations,
        resources,
        total_budget=1000.0,
        strategy="budget_aware_optimized",
    )

    m = alloc["metrics"]
    assert m["total_units_deployed"] == 2
    assert m["total_budget_used"] == 1000.0
    assert m["budget_utilization_pct"] == 100.0
    assert m["total_served_population"] == 200
    assert m["total_unserved_population"] == 350

    # Critical location (priority 10) must receive the 2 budget-constrained units
    crit_outcome = next(
        x for x in alloc["location_outcomes"] if x["location_id"] == "LOC_CRITICAL_HOSP"
    )
    assert crit_outcome["served_population"] == 200
    assert crit_outcome["unserved_population"] == 50
    assert crit_outcome["status"] == "PARTIALLY_SERVED"


def test_strategy_comparison():
    locations = [
        {
            "location_id": "L_NEAR",
            "name": "Nearby Low Priority",
            "priority": 1.0,
            "affected_population": 100,
            "distance_m": 400.0,
        },
        {
            "location_id": "L_HIGH",
            "name": "High Priority Shelter",
            "priority": 9.0,
            "affected_population": 100,
            "distance_m": 3000.0,
        },
    ]

    resources = [
        {
            "resource_id": "AMB_1",
            "resource_type": "ambulance_fleet",
            "units": 1,
            "capacity_per_unit": 100,
            "cost_per_unit": 300.0,
        }
    ]

    comp = compare_rescue_strategies(locations, resources, total_budget=500.0)
    assert set(comp["strategies"].keys()) == {
        "nearest_resource_first",
        "highest_priority_first",
        "budget_aware_optimized",
    }

    # Nearest strategy picks L_NEAR (400m); Priority & Optimized pick L_HIGH (priority 9)
    near_alloc = comp["strategies"]["nearest_resource_first"]["allocations"][0]
    prio_alloc = comp["strategies"]["highest_priority_first"]["allocations"][0]
    assert near_alloc["location_id"] == "L_NEAR"
    assert prio_alloc["location_id"] == "L_HIGH"
    assert comp["recommended_strategy"] in ("highest_priority_first", "budget_aware_optimized")


def test_active_observation_planning():
    g = nx.MultiDiGraph()
    # Critical rescue route underpass near threshold
    g.add_edge(
        "1", "2",
        road_id="R_CRIT_UNDERPASS",
        name="KR Circle Underpass",
        highway="primary",
        tunnel="yes",
        layer="-1",
        length_m=180.0,
    )
    # Ordinary low-risk bridge
    g.add_edge(
        "2", "3",
        road_id="R_SAFE_FLYOVER",
        name="Hebbal Flyover",
        highway="trunk",
        bridge="yes",
        layer="1",
        surface="asphalt",
        smoothness="good",
        lanes="3",
        length_m=400.0,
    )

    obs = plan_active_observations(
        g,
        top_k=2,
        critical_route_road_ids=["R_CRIT_UNDERPASS"],
        facility_nodes=["2"],
        rainfall_intensity=75,
    )

    assert obs["recommended_observations_count"] == 2
    top_rec = obs["recommendations"][0]
    assert top_rec["road_id"] == "R_CRIT_UNDERPASS"
    assert top_rec["could_change_rescue_strategy"] is True
    assert top_rec["observation_priority_score"] > obs["recommendations"][1]["observation_priority_score"]


def test_decision_invalid_inputs():
    g = _build_sample_rescue_network()

    with pytest.raises(ValueError):
        find_shortest_safe_route(g, "MISSING_NODE", "D")

    with pytest.raises(ValueError):
        find_shortest_safe_route(g, "A", "D", optimize_for="invalid_metric")

    with pytest.raises(ValueError):
        allocate_emergency_resources([], [], total_budget=-100)

    with pytest.raises(ValueError):
        allocate_emergency_resources([], [], strategy="non_existent_strategy")

    with pytest.raises(ValueError):
        plan_active_observations(g, top_k=0)

