# SANJEEVANI – Member 3 Dashboard Integration Guide (For Member 4)

This guide explains how Member 4's dashboard can consume Member 3's **Disaster Simulation and Rescue Optimization** outputs either via the pre-generated JSON payload or by calling Member 3's Python API directly.

---

## Option A: Consume the Pre-Generated JSON Payload (Fastest)

Running `.\venv\Scripts\python.exe -m sanjeevani.member3_demo` generates a compact, validated JSON file at:

```text
data/processed/member3_dashboard_payload.json
```

### Loading in Python (Streamlit / Flask / FastAPI / Dash)
```python
import json
from pathlib import Path

payload_path = Path("data/processed/member3_dashboard_payload.json")
with open(payload_path, "r", encoding="utf-8") as f:
    member3_data = json.load(f)
```

### Top-Level JSON Keys (All 8 Phases)

| JSON Key | Dashboard Panel / Widget | Key Fields Available |
| :--- | :--- | :--- |
| `phase1_network_validation` | Network Status Card | `total_nodes` (`437,698`), `total_directed_edges` (`921,188`), `total_unique_road_ways` (`135,302`), `validation_status` (`"PASS"`) |
| `phase2_vulnerability` | Vulnerability Risk Breakdown | `full_city` and `central_corridor` (`way_risk_distribution`, `edge_risk_distribution`, `average_way_vulnerability`, `estimated_edges`, `methodology_note`) |
| `phase3_rainfall_simulation` | Rainfall Time-Slider (`0, +15, +30, +60 min`) | `full_city_heavy_rainfall_85` and `corridor_progression_scenarios` (`unique_road_way_counts`, `directed_edge_counts`, `road_length_km`) |
| `phase4_cascading_and_facilities` | Facility Impact & Connectivity Alert | `facility_counts_citywide` (`hospitals`, `fire_stations`, `police_stations`, `suitable_shelters`), `excluded_non_emergency_shelters`, `connectivity_impact`, `facility_impact` (`inaccessible_count`, `increased_travel_time_count`), `population_impact` |
| `phase5_rescue_routing` | Primary vs Alternative Route Panel | `dispatch_origin_node`, `target_hospital`, `primary_route`, `alternative_route` (`total_distance_m`, `estimated_travel_time_sec`, `unique_road_ids`, `route_safety_status`, `uncertain_access_warnings`), `multi_destination_summary` |
| `phase6_resource_allocation` | Resource Deployment Table | `strategy_used`, `metrics` (`population_coverage_pct`, `resource_utilization_pct`, `budget_utilization_pct`), `allocations`, `location_outcomes` |
| `phase7_strategy_comparison` | Strategy Comparison Chart (A vs B vs C) | `comparison_summary` (`nearest_resource_first`, `highest_priority_first`, `budget_aware_optimized`), `recommended_strategy`, `recommendation_reason` |
| `phase8_active_observation_plan` | Field/Sensor Inspection Priority Table | `recommendations` (`rank`, `road_id`, `highway`, `observation_priority_score`, `could_change_rescue_strategy`, `inspection_reasons`), `prototype_disclaimer` |

---

## Option B: Call Member 3 Python Functions Directly (Interactive Dashboard Controls)

If the dashboard allows users to change rainfall intensity, budget, or origin/destination interactively:

### 1. Load the Cached Road Network (Loads in ~5s from Binary Cache)
```python
from sanjeevani.validate_osm_graph import load_or_cache_osm_graph
from sanjeevani.twin import extract_corridor_subgraph

full_graph = load_or_cache_osm_graph()  # Uses data/processed/bengaluru_osm_cached.pkl
corridor_graph = extract_corridor_subgraph(full_graph, 77.565, 12.955, 77.625, 13.005)
```

### 2. Run Rainfall Simulation & Future Scenarios (Phases 2 & 3)
```python
from sanjeevani.twin import (
    simulate_rainfall,
    predict_future_scenarios,
    summarize_rainfall_simulation,
)

updated_graph, road_results = simulate_rainfall(corridor_graph, rainfall_intensity=80)
summary = summarize_rainfall_simulation(updated_graph, road_results, rainfall_intensity=80)

scenarios = predict_future_scenarios(corridor_graph, current_rainfall=55, increase_per_15_min=10)
```

### 3. Run Cascading Failure & Facility Accessibility Analysis (Phase 4)
```python
from sanjeevani.cascading_failure import (
    extract_emergency_facilities,
    analyze_cascading_failures,
)

facilities = extract_emergency_facilities(graph=corridor_graph)
cascading = analyze_cascading_failures(
    updated_graph,
    facilities_by_category=facilities["categories"],
    dispatch_nodes=["13455267145"],
)
```

### 4. Compute Primary, Alternative, and Multi-Destination Rescue Routes (Phase 5)
```python
from sanjeevani.decision import (
    find_shortest_safe_route,
    find_alternative_route,
    optimize_multi_destination_routes,
)

routes = find_alternative_route(
    updated_graph,
    origin="13455267145",
    destination="10060540200",
    optimize_for="time",
)
primary_route = routes["primary_route"]
alternative_route = routes["alternative_route"]
```

### 5. Allocate Emergency Resources & Compare Strategies (Phases 6 & 7)
```python
from sanjeevani.decision import (
    allocate_emergency_resources,
    compare_rescue_strategies,
)

comparison = compare_rescue_strategies(
    affected_locations=affected_locations_list,
    available_resources=available_resources_list,
    total_budget=3200.0,
)
recommended_strategy = comparison["recommended_strategy"]
```

### 6. Generate Active Observation Recommendations (Phase 8)
```python
from sanjeevani.decision import plan_active_observations

observations = plan_active_observations(
    updated_graph,
    top_k=8,
    critical_route_road_ids=primary_route["road_ids"],
    rainfall_intensity=80,
)
```

---

## Important Data Labels to Display in the Dashboard UI

To maintain scientific and engineering transparency, display these labels in the UI:
1. **Flood Vulnerability Scores**: Label as *"Estimated from OSM Infrastructure Tags"* (`value_type: "estimated"`), not direct flood-depth sensor readings.
2. **Rainfall Progression (`0, +15, +30, +60 min`)**: Label as *"Hypothetical Stress-Test Scenarios"*, not IMD weather radar forecasts.
3. **Emergency Facilities**: Label as *"Unverified OpenStreetMap Records"* (`verification_status: "unverified_osm_record"`). Non-emergency shelters (`292` gazebos, bus-stop canopies, and picnic shelters) have already been filtered out.
4. **Population Figures**: When using scenario demand values, display the badge *"Synthetic Scenario Assumption"* (`is_synthetic: true`).
5. **Active Observation Planner**: Label as *"Field/Sensor Inspection Priority Prototype"* (`prototype_disclaimer`).

