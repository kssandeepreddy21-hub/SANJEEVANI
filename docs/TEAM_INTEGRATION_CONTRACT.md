# SANJEEVANI — Team Integration Contract
## Module 1 Hand-Off Guide for Members 2, 3, and 4

> **Author:** Member 1 (Disaster Prediction & Infrastructure Resilience)  
> **Status:** Final & Integration-Ready (Priority 8)  
> **Purpose:** Allows Members 2, 3, and 4 to consume all Module 1 models, scenario reports, rankings, and cartographic maps without needing to inspect internal implementation code.

---

## 1. Ownership & Interface Boundaries

| Member | Primary Responsibility | Interface with Member 1 |
| :--- | :--- | :--- |
| **Member 1** (Us) | Disaster Prediction & Infrastructure Resilience | Produces city network graph, road vulnerability rankings, failure scenario reports, and pre-disaster resource staging plans. |
| **Member 2** | Emergency Report Analysis & Evidence Intelligence | Maps incoming citizen distress text and damage images to specific `node_id` or `road_id` targets. |
| **Member 3** | Disaster Simulation & Rescue Optimization | Uses Member 1's baseline network and road failure scenarios as ground truth to simulate rising floodwaters and compute optimal rescue boat routes. |
| **Member 4** | Dashboard & Integration | Consumes Member 1's CSV tables, JSON metrics, and PNG maps to render the Streamlit executive dashboard. |

> [!WARNING]
> **Data Stability Contract:**  
> The node schema (`id`, `name`, `type`, `pos`, `population`, `capacity`) and edge schema (`road_id`, `source`, `destination`, `distance_km`, `travel_time_min`, `failure_probability`, `flood_sensitivity`, `road_type`, `is_available`) are **frozen and stable**. Member 1 will never silently alter or delete these attributes.

---

## 2. Integration Guide for Member 2 (Emergency Report Analysis)

Member 2 extracts distress reports, incident severity, and evidence photos from the public. To link your reports to physical municipal infrastructure, use Member 1's standardized identifiers:

> [!IMPORTANT]
> **Coordinate Semantics Notice for Member 2:**  
> All node positions `(x, y)` and tabular coordinates `pos_x, pos_y` are **synthetic 2D integer Cartesian grid coordinates** on an arbitrary 100×100 layout canvas for schematic/graph rendering.  
> - They are **NOT** geographic GPS coordinates (latitude/longitude) or projected spatial GIS coordinates.  
> - Do **NOT** attempt geocoding via external APIs (e.g. Google Maps or Nominatim).  
> - Do **NOT** use spherical Haversine distance formulas or geographic map tiles.  
> - **Action Required for Member 2:** Match incoming citizen reports directly to Member 1's standardized `node_id` (`R1`–`R6`, `H1`, `H2`, `S1`, `S2`, `E1`, `E2`, `J1`–`J4`) or `road_id` (`RD01`–`RD20`).

### Available Incident Mapping Targets
Every incident report can be linked to either a **Node ID** (neighborhood/landmark) or a **Road ID** (transit segment):

```python
# Member 2 Example: Tagging an incoming citizen distress report
incident_report = {
    "report_id": "REP_2026_0891",
    "timestamp": "2026-11-11T18:00:00Z",
    "urgency": "CRITICAL",
    "extracted_location": "Riverside Colony near Grand River Bridge",
    # Link directly to Member 1 Identifiers:
    "matched_node_id": "R1",          # Riverside Colony (Synthetic Grid: x=15, y=40)
    "matched_road_id": "RD11",        # Grand River Bridge (Connects J1 <-> J2)
    "evidence_confidence": 0.88,
}
```

### Complete List of Stable Node Identifiers for Incident Mapping (Synthetic Grid Coordinates)
| Node ID | Landmark Name | Node Type | Coordinates `(x, y)` | Notes |
| :---: | :--- | :--- | :---: | :--- |
| `R1` | Riverside Colony | `residential` | `(15, 40)` | High flood exposure, 14,000 residents |
| `R2` | Downtown Heights | `residential` | `(45, 60)` | Urban core, 28,000 residents |
| `R3` | Hilltop Suburb | `residential` | `(20, 85)` | Elevated, 9,500 residents (single access road) |
| `R4` | East End Ward | `residential` | `(85, 45)` | Eastern sector, 18,000 residents |
| `R5` | Old Town Quarter | `residential` | `(60, 25)` | Historic riverbank, 12,500 residents |
| `R6` | Lakeside Enclave | `residential` | `(30, 15)` | Waterfront, 8,000 residents |
| `H1` | City General Hospital | `hospital` | `(50, 75)` | 450 inpatient beds |
| `H2` | Apex Trauma Center | `hospital` | `(80, 20)` | 250 trauma beds |
| `S1` | North Community Stadium | `shelter` | `(35, 90)` | 3,500 evacuee capacity |
| `S2` | East High School Camp | `shelter` | `(70, 70)` | 2,000 evacuee capacity |
| `E1` | Central Fire & EMS Hub | `emergency_station` | `(40, 50)` | Fleet dispatch base (20 units) |
| `E2` | Westside Rescue Depot | `emergency_station` | `(10, 60)` | Riverfront depot (15 units) |
| `J1`–`J4` | Junctions 1 through 4 | `junction` | Various | Major road intersections |

---

## 3. Integration Guide for Member 3 (Simulation & Rescue Routing)

Member 3 simulates rainfall inundation and computes dynamic rescue boat and vehicle paths.

> [!NOTE]
> **Scenario Graph Hand-off Clarification:**  
> When using direct Python calls (`simulate_road_failure` or `simulate_multiple_failures`), Member 1 returns an independent cloned `nx.Graph` under the key `"scenario_graph"`. The original baseline graph `G` remains strictly unmodified (`is_original_graph_unchanged == True`).  
> **On-Disk JSON Difference:** The saved files in `outputs/` (`rd04_failure_scenario.json`, `rd11_failure_scenario.json`) contain tabular metrics and impact figures but omit the `scenario_graph` key because NetworkX graph instances are not directly JSON-serializable. For interactive routing, use Option A (direct Python API) or load the baseline graph via `data.load_city_from_json()` and remove the road.

### Option A: Direct Python API Imports (Recommended for Dynamic Simulation)
You can import Member 1's graph builder and simulation functions directly into your scripts:
```python
from data import build_synthetic_city
from resilience import simulate_road_failure, simulate_multiple_failures, get_disconnected_zones

# 1. Obtain the baseline city network (Undirected NetworkX Graph)
city_graph = build_synthetic_city()

# 2. Simulate floodwaters submerging multiple roads simultaneously
# Pass a list of road IDs that your hydrological simulation predicts will flood:
flooded_roads = ["RD11", "RD19"]  # Grand River Bridge & South Causeway
scenario_report = simulate_multiple_failures(city_graph, flooded_roads)

# 3. Inspect affected zones
print("Connected components:", scenario_report["connected_component_count"])
print("Disconnected residential zones:", scenario_report["disconnected_residential_zones"])
print("Isolated hospitals:", scenario_report["isolated_hospitals"])

# 4. Use the cloned scenario graph for your rescue routing algorithms
# (Guaranteed that your pathfinding algorithms ignore the flooded roads!)
active_routing_graph = scenario_report["scenario_graph"]
```

### Option B: Consuming Pre-Computed Deliverables from `outputs/`
If you prefer reading pre-computed JSON and CSV artifacts:
```python
import json
import pandas as pd

# Load Scenario A: RD04 Cut-Edge Failure
with open("outputs/rd04_failure_scenario.json", "r") as f:
    scen_a = json.load(f)
print("Scenario A Disconnected Zones:", scen_a["disconnected_residential_zones"])  # ['R3']

# Load Scenario B: RD11 Bridge Failure
with open("outputs/rd11_failure_scenario.json", "r") as f:
    scen_b = json.load(f)
print("Scenario B Components:", scen_b["connected_component_count"])  # 1 (Connected via detours)

# Load Pre-Disaster Resource Positioning Plan to see where boats are staged
df_resources = pd.read_csv("outputs/resource_positioning_plan.csv")
boats_staged = df_resources[df_resources["resource_type"] == "boats"]
print("Boats staged at nodes:", boats_staged["recommended_node_id"].tolist())  # ['E2', 'R1', 'R6']
```

---

## 4. Integration Guide for Member 4 (Streamlit Dashboard & Visualization)

Member 4 builds the interactive Streamlit user interface. Member 1 provides ready-to-display DataFrames, summary metric cards, and 5 high-resolution cartographic maps.

### 1. Dashboard Header Cards (from `outputs/city_summary.json`)
```python
import json
import streamlit as st

with open("outputs/city_summary.json", "r") as f:
    metrics = json.load(f)

col1, col2, col3, col4 = st.columns(4)
col1.metric("City Population", f"{metrics['total_population']:,}")
col2.metric("Hospital Beds", f"{metrics['total_hospital_beds']:,}")
col3.metric("Shelter Capacity", f"{metrics['total_shelter_capacity']:,}")
col4.metric("Active Bridges", f"{metrics['bridges_count']}")
```

### 2. Critical Road Risk Table (from `outputs/critical_road_ranking.csv`)
```python
import pandas as pd
import streamlit as st

df_critical = pd.read_csv("outputs/critical_road_ranking.csv")

# Filter and display high-priority critical roads
st.subheader("Critical Infrastructure Prioritization")
display_cols = [
    "road_id", "road_name", "road_type", "criticality_level",
    "comprehensive_criticality_score", "unique_population_losing_access",
    "population_with_delayed_hospital_access", "max_hospital_delay_min"
]
st.dataframe(df_critical[display_cols])
```

### 3. Pre-Disaster Staging Table (from `outputs/resource_positioning_plan.csv`)
```python
df_staging = pd.read_csv("outputs/resource_positioning_plan.csv")
st.subheader("Pre-Disaster Emergency Asset Deployment")
st.table(df_staging[["resource_type", "recommended_node_id", "recommended_location_name", "relevant_population"]])
```

### 4. High-Resolution Visual Network Maps (PNGs in `outputs/`)
Member 1 has pre-rendered 5 publication-grade maps at 150 DPI. In Streamlit, display them with a single line:
```python
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "City Topology", "Critical Roads", "RD04 Cut-Edge Failure", "RD11 Bridge Failure", "Resource Plan"
])

with tab1:
    st.image("outputs/viz_city_network.png", caption="Baseline City Infrastructure Network")
with tab2:
    st.image("outputs/viz_critical_roads.png", caption="Multi-Criteria Critical Road Ranking")
with tab3:
    st.image("outputs/viz_rd04_failure.png", caption="Scenario A: Cut-Edge Collapse Isolating Hilltop Suburb R3")
with tab4:
    st.image("outputs/viz_rd11_failure.png", caption="Scenario B: Grand River Bridge Closure & Detours")
with tab5:
    st.image("outputs/viz_resource_plan.png", caption="Pre-Disaster Emergency Resource Staging Map")
```

---

## 5. Artifact Manifest & Exact File Schemas

```text
outputs/
├── city_summary.json               # Baseline citywide summary
├── baseline_city_network.json      # Full graph serialized (nodes, pos, roads)
├── rd04_failure_scenario.json      # Scenario A: RD04 cut-edge isolation
├── rd11_failure_scenario.json      # Scenario B: RD11 bridge closure & detours
├── human_impact_results.csv        # Disconnected vs. delayed pop across 20 roads
├── critical_road_ranking.csv       # 19-column multi-criteria ranked road table
├── critical_road_ranking.json      # Structured ranked roads with methodology
├── resource_positioning_plan.csv   # Staging recommendations table
├── resource_positioning_plan.json  # Grouped node allocations & inventories
├── viz_city_network.png            # Visual Map 1 (150 DPI)
├── viz_critical_roads.png          # Visual Map 2 (150 DPI)
├── viz_rd04_failure.png            # Visual Map 3 (150 DPI)
├── viz_rd11_failure.png            # Visual Map 4 (150 DPI)
└── viz_resource_plan.png           # Visual Map 5 (150 DPI)
```

### Sample JSON Structure (`rd04_failure_scenario.json`)
```json
{
  "scenario_id": "SCENARIO_SINGLE_FAIL_RD04",
  "failed_road_ids": ["RD04"],
  "failed_road_names": ["Hilltop Access Road"],
  "original_node_count": 16,
  "original_edge_count": 20,
  "scenario_node_count": 16,
  "scenario_edge_count": 19,
  "connected_component_count": 2,
  "disconnected_residential_zones": ["R3"],
  "no_hospital_access_zones": ["R3"],
  "no_shelter_access_zones": ["R3"],
  "isolated_hospitals": [],
  "isolated_shelters": [],
  "isolated_emergency_stations": [],
  "is_original_graph_unchanged": true,
  "human_impact": {
    "unique_population_lost_critical_service": 9500,
    "risk_score": 950.0
  }
}
```

---

## 6. How Teammates Can Verify Integration Locally

To run the pipeline and refresh all artifacts:
```powershell
.\.venv\Scripts\python.exe main.py
```
To run the complete automated test suite:
```powershell
.\.venv\Scripts\pytest -v
```
All 42 tests will pass, confirming that your environment is fully integrated!

---

## 7. Integration Assumptions Requiring Team Confirmation

To guarantee zero integration friction during the team merge, the following assumptions should be explicitly confirmed with teammates:

### A. Assumptions for Member 2 (Emergency Report Analysis)
1. **Identifier Matching vs. Geocoding:** Member 2's NLP and computer vision extraction models must map incident reports directly to Member 1's standardized `node_id` (`R1`–`R6`, `H1`, `H2`, `S1`, `S2`, `E1`, `E2`, `J1`–`J4`) or `road_id` (`RD01`–`RD20`). Member 2 will **not** attempt external GPS geocoding, reverse geocoding, or spherical Haversine formulas on synthetic `(x, y)` coordinates.
2. **Confidence Scores:** Member 2's reported confidence scores are expected as floats in $[0.0, 1.0]$.

### B. Assumptions for Member 3 (Disaster Simulation & Rescue Routing)
1. **Input Schema for Inundations:** Member 3's hydrological flood simulation will output inundated segments as a Python `List[str]` of road IDs (e.g. `["RD11", "RD19"]`) to pass into `simulate_multiple_failures(city_graph, flooded_roads)`.
2. **In-Memory vs. File Hand-Off:** Confirm that Member 3 prefers in-memory Python API calls (`scenario_report["scenario_graph"]`) for dynamic rescue routing, rather than attempting to deserialize the on-disk scenario JSONs which omit graph objects.
3. **Watercraft Staging:** Confirm that Member 3's boat pathfinding starts from Member 1's designated boat staging nodes (`E2`, `R1`, `R6`).

### C. Assumptions for Member 4 (Streamlit Dashboard & Visualization)
1. **Tabular Column Schema:** Confirm Member 4 uses column `road_name` (not `name`) when querying `outputs/critical_road_ranking.csv`.
2. **Map Display Strategy:** Confirm Member 4 displays Member 1's pre-rendered 150 DPI PNG maps (`viz_city_network.png`, `viz_critical_roads.png`, `viz_rd04_failure.png`, `viz_rd11_failure.png`, `viz_resource_plan.png`) via `st.image()` for instant, publication-grade visualization.

