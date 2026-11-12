# SANJEEVANI — Public Function Reference Guide
## Module 1: Disaster Prediction & Infrastructure Resilience

> **Author:** Member 1  
> **Source Files:** [`data.py`](file:///c:/Users/dell/Desktop/SANJIVANI/data.py), [`resilience.py`](file:///c:/Users/dell/Desktop/SANJIVANI/resilience.py), [`main.py`](file:///c:/Users/dell/Desktop/SANJIVANI/main.py)  
> **Testing Suite:** [`tests/test_resilience.py`](file:///c:/Users/dell/Desktop/SANJIVANI/tests/test_resilience.py) (42 tests, 100% pass rate)

---

## Part 1: Data Model & Graph Construction (`data.py`)

### Coordinate System Semantics
> [!IMPORTANT]
> **Synthetic Grid Coordinates (Not GPS / Not Geocoded):**  
> All node positions `pos: (x, y)` and tabular columns `pos_x`, `pos_y` are **synthetic 2D integer Cartesian grid coordinates** on an arbitrary 100×100 layout plane designed solely for diagrammatic network visualization with NetworkX and Matplotlib.  
> They are **NOT** geographic latitude/longitude (GPS coordinates), **NOT** projected GIS spatial coordinates (e.g. UTM meters), and cannot be resolved by geocoding services (such as Nominatim or Google Maps) or measured using spherical Haversine formulas.

### 1. `build_synthetic_city()`
- **Purpose:** Constructs and returns the baseline synthetic municipal road network as an undirected NetworkX Graph.
- **Parameters:** None.
- **Return Type:** `nx.Graph`
- **Modifies Original Graph:** N/A (creates a new instance).
- **Node Attributes:** `name` (`str`), `type` (`str`: `'residential'`, `'hospital'`, `'shelter'`, `'emergency_station'`, `'junction'`), `pos` (`Tuple[int, int]`: synthetic 2D grid coordinates), `is_synthetic` (`bool`), plus optional `population`, `capacity`, `flood_exposure`.
- **Edge Attributes:** `road_id` (`str`), `name` (`str`), `distance_km` (`float`), `travel_time_min` (`float`), `failure_probability` (`float` in $[0.0, 1.0]$), `flood_sensitivity` (`float` in $[0.0, 1.0]$), `road_type` (`str`: `'bridge'`, `'highway'`, `'arterial'`, `'local'`), `is_available` (`bool`), `is_synthetic` (`bool`).
- **Example Usage:**
  ```python
  from data import build_synthetic_city
  G = build_synthetic_city()
  print("Nodes:", G.number_of_nodes())  # 16
  print("Edges:", G.number_of_edges())  # 20
  ```
- **Limitations:** Data is synthetic and tagged with `is_synthetic = True`.

---

### 2. `get_nodes_by_type(graph, node_type)`
- **Purpose:** Filters and retrieves node IDs matching a specified facility or zone type.
- **Parameters:**
  - `graph` (`nx.Graph`): City network graph.
  - `node_type` (`str`): One of `'residential'`, `'hospital'`, `'shelter'`, `'emergency_station'`, `'junction'`.
- **Return Type:** `List[str]`
- **Modifies Original Graph:** No.
- **Example Usage:**
  ```python
  from data import build_synthetic_city, get_nodes_by_type
  G = build_synthetic_city()
  hospitals = get_nodes_by_type(G, "hospital")      # ['H1', 'H2']
  shelters = get_nodes_by_type(G, "shelter")        # ['S1', 'S2']
  residential = get_nodes_by_type(G, "residential") # ['R1', 'R2', 'R3', 'R4', 'R5', 'R6']
  ```

---

### 3. `get_city_summary(graph)`
- **Purpose:** Generates a high-level statistical summary dictionary of city assets and baseline connectivity.
- **Parameters:**
  - `graph` (`nx.Graph`): City network graph.
- **Return Type:** `Dict[str, Any]`
- **Modifies Original Graph:** No.
- **Example Usage:**
  ```python
  from data import build_synthetic_city, get_city_summary
  G = build_synthetic_city()
  summary = get_city_summary(G)
  print("Population:", summary["total_population"])       # 90,000
  print("Hospital Beds:", summary["total_hospital_beds"]) # 700
  ```

---

### 4. `export_city_to_dataframes(graph)`
- **Purpose:** Converts graph nodes and edges into two clean Pandas DataFrames for tabular analysis.
- **Parameters:**
  - `graph` (`nx.Graph`): City network graph.
- **Return Type:** `Tuple[pd.DataFrame, pd.DataFrame]` $\rightarrow$ `(nodes_df, edges_df)`
- **Modifies Original Graph:** No.
- **Example Usage:**
  ```python
  from data import build_synthetic_city, export_city_to_dataframes
  G = build_synthetic_city()
  nodes_df, edges_df = export_city_to_dataframes(G)
  ```

---

### 5. `save_city_to_json(graph, filepath)` & `load_city_from_json(filepath)`
- **Purpose:** Serializes a graph to disk in JSON format and deserializes a JSON file back into a full `nx.Graph`.
- **Parameters:**
  - `graph` (`nx.Graph`): City network graph.
  - `filepath` (`str`): File path to save/load.
- **Return Type:** `None` (for save), `nx.Graph` (for load).
- **Modifies Original Graph:** No.

---

## Part 2: Vulnerability & Failure Simulation Engine (`resilience.py`)

### 6. `calculate_edge_centrality(G)`
- **Purpose:** Computes weighted Edge Betweenness Centrality for all roads using `travel_time_min` as edge weights. Centrality measures how frequently an edge appears on fastest (shortest) weighted paths between all node pairs in the network.
- **Scientific Terminology:** Weighted edge betweenness centrality across weighted shortest paths (do not refer to this as "Dijkstra edge betweenness").
- **Parameters:**
  - `G` (`nx.Graph`): City network graph (not modified).
- **Return Type:** `Dict[str, float]` mapping `road_id` $\rightarrow$ normalized score in $[0.0, 1.0]$ rounded to 4 decimals.
- **Modifies Original Graph:** No.
- **Example Usage:**
  ```python
  from resilience import calculate_edge_centrality
  ebc = calculate_edge_centrality(G)
  print("Grand River Bridge Centrality:", ebc["RD11"])  # 0.3500
  ```

---

### 7. `identify_critical_bridges(G, return_classification=False)`
- **Purpose:** Identifies graph-theoretic cut-edges (topological single points of failure).
- **Parameters:**
  - `G` (`nx.Graph`): City network graph (not modified).
  - `return_classification` (`bool`, default: `False`): If `True`, returns a detailed dictionary categorizing graph bridges vs physical bridges.
- **Return Type:** `List[str]` (cut-edge road IDs) or `Dict[str, List[str]]`.
- **Modifies Original Graph:** No.
- **Example Usage:**
  ```python
  from resilience import identify_critical_bridges
  cut_edges = identify_critical_bridges(G)  # ['RD04']
  ```

---

### 8. `simulate_road_failure(G, road_id)`
- **Purpose:** Simulates the closure/collapse of a single road or bridge on an independent graph copy.
- **Parameters:**
  - `G` (`nx.Graph`): Baseline city network graph (never modified).
  - `road_id` (`str`): Identifier of the road to close (e.g. `'RD04'`).
- **Return Type:** `Dict[str, Any]` containing 16 exact keys:
  - `"scenario_id"` (`str`): Unique scenario identifier (e.g. `'SCENARIO_SINGLE_FAIL_RD04'`)
  - `"failed_road_ids"` (`List[str]`): List containing the closed road ID
  - `"failed_road_names"` (`List[str]`): List of human-readable road names closed
  - `"original_node_count"` (`int`): Node count of baseline graph (16)
  - `"original_edge_count"` (`int`): Edge count of baseline graph (20)
  - `"scenario_node_count"` (`int`): Node count of scenario graph (16)
  - `"scenario_edge_count"` (`int`): Edge count of scenario graph after failure (19)
  - `"connected_component_count"` (`int`): Number of disconnected graph components
  - `"disconnected_residential_zones"` (`List[str]`): Residential zone IDs losing hospital OR shelter access
  - `"no_hospital_access_zones"` (`List[str]`): Residential zone IDs with zero reachable hospitals
  - `"no_shelter_access_zones"` (`List[str]`): Residential zone IDs with zero reachable shelters
  - `"isolated_hospitals"` (`List[str]`): Hospital IDs unreachable by any residential zone
  - `"isolated_shelters"` (`List[str]`): Shelter IDs unreachable by any residential zone
  - `"isolated_emergency_stations"` (`List[str]`): Station IDs unreachable by any residential zone
  - `"is_original_graph_unchanged"` (`bool`): Assertion proving baseline $G$ was not mutated (`True`)
  - `"scenario_graph"` (`nx.Graph`): Cloned, independent `nx.Graph` copy with failed road removed
  - `"zone_accessibility_details"` (`Dict[str, Dict[str, Any]]`): Per-residential-zone accessibility report
- **Scenario Graph Hand-off:** The returned `scenario_graph` is an independent cloned `nx.Graph` copy (`G.copy()`). Downstream routing or pathfinding algorithms run on this graph without affecting the original $G$. Note: In saved JSON scenario files on disk (`outputs/rd04_failure_scenario.json`), `scenario_graph` is omitted because NetworkX graphs cannot be JSON-serialized directly.
- **Modifies Original Graph:** **Strictly No (never mutates original graph).**
- **Common Errors:** Raises `ValueError` if `road_id` does not exist in the graph.
- **Example Usage:**
  ```python
  from resilience import simulate_road_failure
  report = simulate_road_failure(G, "RD04")
  print("Components:", report["connected_component_count"])          # 2
  print("Isolated:", report["disconnected_residential_zones"])       # ['R3']
  scenario_net = report["scenario_graph"]                            # Cloned nx.Graph
  ```

---

### 9. `simulate_multiple_failures(G, road_ids, ignore_invalid=False)`
- **Purpose:** Simulates simultaneous compound road closures (e.g. multi-point flash flooding).
- **Parameters:**
  - `G` (`nx.Graph`): Baseline city network graph (not modified).
  - `road_ids` (`List[str]`): List of road IDs to close simultaneously.
  - `ignore_invalid` (`bool`, default: `False`): If `True`, safely bypasses unrecognised IDs.
- **Return Type:** `Dict[str, Any]` containing all keys from `simulate_road_failure()` plus:
  - `"invalid_road_ids"` (`List[str]`): List of road IDs not found in the city network.
  - `"scenario_graph"` (`nx.Graph`): Cloned independent copy with all valid roads removed.
- **Modifies Original Graph:** **Strictly No.**
- **Common Errors:** Raises `ValueError` if any ID is invalid and `ignore_invalid=False`. Automatically deduplicates duplicate IDs.

---

### 10. `get_disconnected_zones(G)`
- **Purpose:** Evaluates residential zones for complete loss of access to hospitals and shelters.
- **Parameters:**
  - `G` (`nx.Graph`): City network graph (scenario or baseline).
- **Return Type:** `Dict[str, Any]` containing `'no_hospital_access'`, `'no_shelter_access'`, `'disconnected_residential_zones'`, and per-zone travel times.
- **Modifies Original Graph:** No.
- **Key Logic:** Distinguishes component partitioning from service loss.

---

### 11. `estimate_human_impact(G, scenario_input, failure_probability=None)`
- **Purpose:** Translates network disconnections and detours into human life metrics with strict non-double-counting.
- **Parameters:**
  - `G` (`nx.Graph`): Baseline city network graph.
  - `scenario_input`: Road ID string, list of road IDs, or scenario dictionary.
  - `failure_probability` (`Optional[float]`): Override failure probability.
- **Return Type:** `Dict[str, Any]`
- **Modifies Original Graph:** No.
- **Example Usage:**
  ```python
  from resilience import estimate_human_impact
  impact = estimate_human_impact(G, "RD04")
  print("Unique pop lost access:", impact["unique_population_lost_critical_service"])  # 9,500
  print("Prototype Risk Score:", impact["risk_score"])                                # 950.0
  ```

---

### 12. `rank_critical_roads_comprehensive(G)`
- **Purpose:** Computes the master 19-column three-dimensional multi-criteria critical road ranking, addressing the "Harmless Delay Trap" by evaluating access-loss impact, medical travel delays, and physical vulnerability independently.
- **Parameters:**
  - `G` (`nx.Graph`): Baseline city network graph (not modified).
- **Return Type:** `pd.DataFrame` containing exact 19 columns, sorted descending by `comprehensive_criticality_score`:
  1. `road_id` (`str`): Unique road identifier (e.g. `'RD01'`)
  2. `road_name` (`str`): Human-readable road name
  3. `road_type` (`str`): Categorization (`'bridge'`, `'highway'`, `'arterial'`, `'local'`)
  4. `failure_probability` (`float`): Normalized failure probability $[0.0, 1.0]$
  5. `flood_sensitivity` (`float`): Normalized flood susceptibility $[0.0, 1.0]$
  6. `edge_betweenness` (`float`): Weighted betweenness centrality across travel-time shortest paths
  7. `is_structural_bridge` (`bool`): Physical bridge structure over water (`True`/`False`)
  8. `is_graph_bridge` (`bool`): Topological single point of failure / cut-edge (`True`/`False`)
  9. `population_no_hospital_access` (`int`): Exact civilian headcount losing all hospital reachability
  10. `population_no_shelter_access` (`int`): Exact civilian headcount losing all shelter reachability
  11. `unique_population_losing_access` (`int`): Non-double-counted set-union headcount losing hospital OR shelter
  12. `population_with_delayed_hospital_access` (`int`): Civilian headcount experiencing hospital transit detours
  13. `max_hospital_delay_min` (`float`): Maximum observed hospital transit delay in minutes
  14. `access_loss_risk_score` (`float`): Dimension A score $[0.0, 1.0]$: $\min(\text{unique\_pop} / 9500.0, 1.0)$
  15. `delay_impact_score` (`float`): Dimension B score $[0.0, 1.0]$: $0.55 \cdot \text{pop\_norm} + 0.45 \cdot \text{delay\_sev\_norm}$
  16. `infrastructure_vulnerability_score` (`float`): Dimension C score $[0.0, 1.0]$: physical & topological risk
  17. `comprehensive_criticality_score` (`float`): Peak-blend synthesis score $[0.0, 1.0]$: $0.60 \cdot \text{Peak} + 0.40 \cdot \text{Average}$
  18. `criticality_level` (`str`): Categorical rating: `'CRITICAL'` ($\ge 0.55$ or cut-edge), `'HIGH'` ($\ge 0.40$), `'MODERATE'` ($\ge 0.25$), `'LOW'` ($< 0.25$)
  19. `explanation` (`str`): Transparent, explainable natural-language justification notes
- **Modifies Original Graph:** No.
- **Example Usage:**
  ```python
  from resilience import rank_critical_roads_comprehensive
  df_ranked = rank_critical_roads_comprehensive(G)
  print(df_ranked[["road_id", "road_name", "criticality_level", "comprehensive_criticality_score"]].head(3))
  ```

---

### 13. `export_comprehensive_ranking(G, csv_path, json_path)`
- **Purpose:** Computes and exports the comprehensive road ranking to disk in both CSV and JSON formats.
- **Parameters:**
  - `G` (`nx.Graph`): City network graph.
  - `csv_path` (`str`): Target CSV path (default: `'outputs/critical_road_ranking.csv'`).
  - `json_path` (`str`): Target JSON path (default: `'outputs/critical_road_ranking.json'`).
- **Return Type:** `pd.DataFrame`
- **Modifies Original Graph:** No.

---

## Part 3: Resource Positioning Engine (`resilience.py`)

### 14. `identify_candidate_locations(G, resource_type)`
- **Purpose:** Filters suitable candidate nodes for staging a specific emergency resource class.
- **Parameters:**
  - `G` (`nx.Graph`): City network graph.
  - `resource_type` (`str`): One of `'ambulances'`, `'boats'`, `'rescue_teams'`, `'emergency_supplies'`.
- **Return Type:** `List[Dict[str, Any]]`
- **Modifies Original Graph:** No.
- **Common Errors:** Raises `ValueError` if `resource_type` is unrecognised. Automatically screens out unreachable nodes (degree 0).

---

### 15. `recommend_ambulance_positions(G, count=4)`
- **Purpose:** Recommends ambulance staging positions based on population reach within 8 minutes, existing dispatch bases, and hospital delay minimization.
- **Parameters:**
  - `G` (`nx.Graph`): City network graph.
  - `count` (`int`, default: 4): Number of locations to recommend.
- **Return Type:** `List[Dict[str, Any]]`

---

### 16. `recommend_boat_positions(G, count=3)`
- **Purpose:** Recommends rescue boat staging positions targeting high-flood communities and riverbank bases.
- **Parameters:**
  - `G` (`nx.Graph`): City network graph.
  - `count` (`int`, default: 3): Number of locations to recommend.
- **Return Type:** `List[Dict[str, Any]]`
- **Assumptions:** Explicitly includes water-access assumption in return payload.

---

### 17. `recommend_rescue_team_positions(G, count=4)`
- **Purpose:** Recommends staging locations for first-responder evacuation and triage teams across dual quadrants.
- **Parameters:**
  - `G` (`nx.Graph`): City network graph.
  - `count` (`int`, default: 4): Number of locations to recommend.
- **Return Type:** `List[Dict[str, Any]]`

---

### 18. `recommend_supply_positions(G, count=4)`
- **Purpose:** Recommends pre-stockpiling locations for emergency food and potable water. Prioritizes cut-edge isolated communities (e.g. `R3`) and evacuation shelters (`S1`, `S2`).
- **Parameters:**
  - `G` (`nx.Graph`): City network graph.
  - `count` (`int`, default: 4): Number of locations to recommend.
- **Return Type:** `List[Dict[str, Any]]`

---

### 19. `generate_resource_plan(G, inventory=None)`
- **Purpose:** Combines recommendations across all 4 resource types into a unified operational staging plan.
- **Parameters:**
  - `G` (`nx.Graph`): City network graph.
  - `inventory` (`Optional[Dict[str, int]]`): Custom resource counts (default: `{'ambulances': 4, 'boats': 3, 'rescue_teams': 4, 'emergency_supplies': 4}`).
- **Return Type:** `Dict[str, Any]` containing exact keys:
  - `"dataset_name"` (`str`): `'SANJEEVANI_Pre_Disaster_Resource_Positioning_Plan'`
  - `"is_synthetic"` (`bool`): `True`
  - `"algorithm"` (`str`): `'Heuristic Multi-Criteria Demand-Capacity Positioning (Non-Optimal Decision Support)'`
  - `"scientific_disclaimer"` (`str`): Explicit disclaimer that heuristics support human decision-making and do not claim mathematical optimality
  - `"total_resources_allocated"` (`int`): Total count of staged assets (default: 15)
  - `"inventory_requested"` (`Dict[str, int]`): Asset inventory requested
  - `"recommendations"` (`List[Dict[str, Any]]`): List of 15 staging recommendation dictionaries, each with:
    - `"resource_type"` (`str`): `'ambulances'`, `'boats'`, `'rescue_teams'`, `'emergency_supplies'`
    - `"recommended_node_id"` (`str`): Staging node ID
    - `"recommended_location_name"` (`str`): Location name
    - `"reason"` (`str`): Justification narrative
    - `"relevant_population"` (`int`): Target population served
    - `"relevant_critical_roads"` (`List[str]`): Incident critical road IDs
    - `"accessibility_information"` (`str`): Ingress/egress access notes
    - `"confidence_or_suitability_score"` (`float`): Prototype suitability score $[0.0, 1.0]$
    - `"assumptions"` (`str`): Documented operational assumptions
  - `"summary_by_node"` (`Dict[str, Dict[str, Any]]`): Aggregated asset counts grouped by `node_id`, each containing:
    - `"node_id"` (`str`), `"location_name"` (`str`), `"ambulances"` (`int`), `"boats"` (`int`), `"rescue_teams"` (`int`), `"emergency_supplies"` (`int`), `"total_staged_assets"` (`int`)
- **Modifies Original Graph:** No.

---

### 20. `export_resource_plan(G, inventory=None, json_path=..., csv_path=...)`
- **Purpose:** Computes and exports the resource plan to disk in JSON and CSV formats.
- **Return Type:** `Tuple[pd.DataFrame, Dict[str, Any]]`

---

## Part 4: Demonstration & Pipeline Runner (`main.py`)

### 21. `run_pipeline(output_dir="outputs")`
- **Purpose:** Master integration runner. Sequentially executes network generation, statistics, cut-edge analysis, RD04/RD11 failure scenarios, human impact tables, critical rankings, resource plans, and 5 PNG maps.
- **Parameters:**
  - `output_dir` (`str`, default: `'outputs'`): Destination folder for deliverables.
- **Return Type:** `Dict[str, Any]` execution manifest.
- **Modifies Original Graph:** Strictly No (verified by internal assertion).
- **Example Usage:**
  ```python
  from main import run_pipeline
  manifest = run_pipeline("outputs")
  print("Status:", manifest["status"])  # SUCCESS
  print("Total Files:", manifest["total_files_generated"])  # 14
  ```

