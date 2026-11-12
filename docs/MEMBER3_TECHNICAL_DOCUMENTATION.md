# SANJEEVANI – Member 3 Technical Documentation
**Responsibility:** Disaster Simulation and Rescue Optimization  
**Demonstration City:** Bengaluru, Karnataka, India

---

## 1. Architecture Overview

Member 3 provides the disaster simulation, infrastructure impact analysis, and rescue optimization engine for SANJEEVANI. It operates directly on the validated Bengaluru OpenStreetMap (OSM) directed multigraph (`437,698` nodes, `921,188` directed edges across `135,302` unique OSM road ways) and the local OSM PBF dataset (`data/raw/planet_77.46_12.907_d3d9fd17.osm.pbf`).

### Module Structure

| File | Phase(s) | Purpose |
| :--- | :--- | :--- |
| `sanjeevani/validate_osm_graph.py` | Phase 1 | Streaming C-`expat` GraphML loader, binary graph cache (`bengaluru_osm_cached.pkl`), and network validation distinguishing explicit OSM tags from defaults and unique OSM road ways from directed edges. |
| `sanjeevani/flood_vulnerability.py` | Phase 2 | Explainable road-level flood vulnerability estimation (`0.0` to `1.0`), risk categorization (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`), epistemic uncertainty scoring, and distinction between `estimated` and `observed` values. |
| `sanjeevani/twin.py` | Phase 3 | Real road network rainfall simulation (`simulate_rainfall`), multi-horizon scenario projection (`predict_future_scenarios` for `0`, `+15`, `+30`, `+60` min), and city/corridor summary statistics (`summarize_rainfall_simulation`). |
| `sanjeevani/cascading_failure.py` | Phase 4 | Single and multi-road failure simulation (`simulate_road_failures`), deduplicated OSM emergency facility extraction (`extract_emergency_facilities`), and cascading impact analysis (`analyze_cascading_failures`). |
| `sanjeevani/decision.py` | Phases 5–8 | Emergency route optimization (`find_shortest_safe_route`, `find_alternative_route`, `optimize_multi_destination_routes`), resource allocation (`allocate_emergency_resources`), strategy comparison (`compare_rescue_strategies`), and active observation planning (`plan_active_observations`). |
| `sanjeevani/member3_demo.py` | Phase 10 | End-to-end demonstration runner executing Phases 2–8 on real Bengaluru OSM data and exporting `data/processed/member3_dashboard_payload.json` for Member 4. |

---

## 2. Function Reference

### 2.1 `sanjeevani/flood_vulnerability.py` (Phase 2)
- **`estimate_edge_vulnerability(edge_data) -> dict`**
  - Computes an explainable vulnerability score in `[0.0, 1.0]` using OSM attributes (`highway`, `ford`, `tunnel`, `bridge`, `layer`, `surface`, `smoothness`, `lanes`, `width`, and `osm_tags`).
  - Respects `observed_flood_sensitivity` if provided (`value_type="observed"`, `is_estimated=False`); otherwise marks `value_type="estimated"`, `is_estimated=True`.
  - Returns `road_id`, `vulnerability_score`, `risk_category`, `contributing_factors`, `uncertainty_score`, `data_source`, `value_type`, and `is_estimated`.
- **`annotate_graph_vulnerability(graph, inplace=False, overwrite_existing_sensitivity=False) -> nx.Graph`**
  - Populates vulnerability attributes on all edges of a graph, caching by `road_id` for fast execution across `921,188` edges.
- **`summarize_graph_vulnerability(graph) -> dict`**
  - Aggregates vulnerability statistics separately for directed edges and unique OSM road ways (`road_id`).

### 2.2 `sanjeevani/twin.py` (Phase 3)
- **`simulate_rainfall(city_graph, rainfall_intensity) -> (updated_graph, road_results)`**
  - Simulates rainfall intensity in `[0, 100]` without mutating `city_graph`.
  - Uses existing `flood_sensitivity` if present on an edge, or automatically estimates it via `estimate_edge_vulnerability`.
  - Classifies roads into `OPEN` (`impact < 40`), `AT RISK` (`40 <= impact < 70`), and `BLOCKED` (`impact >= 70`, `available=False`).
- **`predict_future_scenarios(city_graph, current_rainfall, increase_per_15_min=10) -> list[dict]`**
  - Generates hypothetical scenarios at `0`, `15`, `30`, and `60` minutes with attached `summary` metrics.
- **`summarize_rainfall_simulation(updated_graph, road_results=None, rainfall_intensity=None) -> dict`**
  - Reports open, at-risk, and blocked counts for both directed edges and unique OSM road ways, affected length in km, highway breakdown, and blocked bridges/tunnels.

### 2.3 `sanjeevani/cascading_failure.py` (Phase 4)
- **`extract_emergency_facilities(pbf_path, graph=None) -> dict`**
  - Extracts and deduplicates emergency facilities from the OSM PBF into 4 strictly separate categories:
    1. `hospitals` (`amenity=hospital`, excluding `clinic`)
    2. `fire_stations` (`amenity=fire_station`)
    3. `police_stations` (`amenity=police`)
    4. `suitable_shelters` (`amenity=shelter` / `social_facility=shelter`, **excluding** `gazebo`, `public_transport` bus shelters, `picnic_shelter`, `pergola`)
  - Eliminates double-counting across relations, ways, and duplicate POI nodes, and snaps facilities to the nearest road node using a spatial grid index.
- **`simulate_road_failures(city_graph, failed_roads=None, include_blocked_condition=True) -> (degraded_graph, report)`**
  - Simulates failure of a single road (`road_id` or `(u, v)`) or multiple roads without mutating `city_graph`.
- **`analyze_cascading_failures(city_graph, failed_roads=None, facilities_by_category=None, dispatch_nodes=None, population_by_node=None, population_is_synthetic=True) -> dict`**
  - Computes component fragmentation, newly disconnected nodes, facility accessibility (separating `inaccessible_facilities` from `increased_travel_time_facilities`), and honest population impact reporting.

### 2.4 `sanjeevani/decision.py` (Phases 5, 6, 7, 8)
- **`evaluate_emergency_access(edge_data) -> dict`**
  - Evaluates passability and emergency access certainty (`verified_emergency_access`, `public_drivable_unverified`, `uncertain_emergency_access`, `prohibited`, `blocked`).
- **`find_shortest_safe_route(graph, origin, destination, optimize_for="time", allow_at_risk=True, allow_uncertain_access=True) -> dict`**
  - Computes shortest safe path avoiding blocked roads, respecting one-way directions and parallel edges in a `MultiDiGraph`.
- **`find_alternative_route(graph, origin, destination, primary_route=None, optimize_for="time", ...) -> dict`**
  - Computes a distinct backup route by penalizing primary route segments and reports overlap ratio.
- **`optimize_multi_destination_routes(graph, origin, destinations, optimize_for="time", ...) -> dict`**
  - Uses single-source Dijkstra to compute routes from a dispatch center to multiple destinations in a single pass.
- **`allocate_emergency_resources(affected_locations, available_resources, total_budget=None, strategy="budget_aware_optimized") -> dict`**
  - Allocates emergency units under capacity and budget constraints, reporting served population, unserved demand, response times, and utilization.
- **`compare_rescue_strategies(affected_locations, available_resources, total_budget=None) -> dict`**
  - Executes and compares `nearest_resource_first` (Strategy A), `highest_priority_first` (Strategy B), and `budget_aware_optimized` (Strategy C).
- **`plan_active_observations(graph, top_k=10, critical_route_road_ids=None, facility_nodes=None, rainfall_intensity=None) -> dict`**
  - Ranks road segments that should be inspected next based on vulnerability, attribute/threshold uncertainty, network criticality, and potential to change the rescue strategy.

---

## 3. Execution Instructions

### Run All Unit and Integration Tests
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_twin.py tests/test_decision.py -v
```

### Run the Complete Member 3 Demonstration
```powershell
.\venv\Scripts\python.exe -m sanjeevani.member3_demo
```

### Run the OSM Road Graph Validation
```powershell
.\venv\Scripts\python.exe -m sanjeevani.validate_osm_graph
```

---

## 4. Assumptions and Limitations

1. **Estimated Flood Vulnerability (Not Hydrological Sensor Data):**
   - OpenStreetMap does not provide digital elevation model (DEM) flood depth, stormwater pipe diameter, or real-time water-level sensor readings. Road vulnerability scores are prototype estimates derived from OSM infrastructure tags (`highway`, `tunnel`, `bridge`, `ford`, `layer`, `surface`, `smoothness`, `width`/`lanes`) and are explicitly marked with `value_type="estimated"` and `is_estimated=True`.
2. **Hypothetical Rainfall Progression Scenarios:**
   - The `0`, `+15`, `+30`, and `+60` minute scenarios in `predict_future_scenarios()` are stress-test simulations driven by user-specified intensity increments, not meteorological radar or IMD weather forecasts.
3. **Emergency Vehicle Access Uncertainty:**
   - Over `21%` of directed edges (`197,351` edges across `24,314` unique OSM road ways) carry `private` or `no` access tags, while only `12` edges carry an explicit `emergency=*` tag. The routing engine never assumes all OSM roads are accessible to emergency vehicles: `access=no` without `emergency=yes` is treated as prohibited, and `access=private`/`customers` or narrow service streets are flagged as `uncertain_emergency_access`.
4. **Unverified OSM Facility Records & Shelter Filtering:**
   - Facility locations (`1,046` unique hospitals, `19` fire stations, `125` police stations, `42` suitable shelters) are extracted from crowd-sourced OSM data and tagged `verification_status="unverified_osm_record"`. Non-emergency structures tagged `amenity=shelter` in OSM (`227` gazebos, `62` public-transport bus shelters, `3` picnic shelters/pergolas) are explicitly excluded.
5. **Population Data:**
   - OSM road graphs do not contain verified census ward population counts per node. When external census data is not passed, `analyze_cascading_failures()` reports `population_data_available=False`. When scenario population figures are used for resource allocation demonstrations, they are explicitly flagged with `is_synthetic=True`.
6. **Active Observation Planning Prototype:**
   - `plan_active_observations()` is an algorithmic prioritization tool for field inspection teams or fixed sensors and does not integrate with physical drone hardware.

---

## 5. Member 4 Dashboard Integration Guide

Running `python -m sanjeevani.member3_demo` generates a single structured JSON file at:
```text
data/processed/member3_dashboard_payload.json
```

Member 4 can either read this JSON file directly or call the Python functions from `sanjeevani.twin` and `sanjeevani.decision`:

- **`phase2_vulnerability`**: Provides `full_city` and `central_corridor` risk category distributions (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`) for both unique OSM road ways and directed edges.
- **`phase3_rainfall_simulation`**: Provides `full_city_heavy_rainfall_85` summary and `corridor_progression_scenarios` (`0`, `+15`, `+30`, `+60` min) for time-slider visualization.
- **`phase4_cascading_and_facilities`**: Provides deduplicated facility counts across the 4 separate categories (`hospitals`, `fire_stations`, `police_stations`, `suitable_shelters`), connectivity drop metrics, and facility accessibility status (`inaccessible_count` vs `increased_travel_time_count`).
- **`phase5_rescue_routing`**: Provides `primary_route` and `alternative_route` node/edge sequences, distances (`m`), travel times (`sec`), and `uncertain_access_warnings` for map polyline rendering.
- **`phase6_and_7_resource_and_strategies`**: Provides `comparison_summary` across all 3 strategies (`nearest_resource_first`, `highest_priority_first`, `budget_aware_optimized`), `recommended_strategy`, `recommended_allocations`, and `location_outcomes`.
- **`phase8_active_observation_plan`**: Provides ranked `recommendations` with `road_id`, `observation_priority_score`, `could_change_rescue_strategy`, and `inspection_reasons`.

