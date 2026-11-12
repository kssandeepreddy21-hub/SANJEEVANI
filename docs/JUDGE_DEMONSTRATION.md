# SANJEEVANI — 5 to 7-Minute Hackathon Judge Demonstration Script
## Module 1: Disaster Prediction & Infrastructure Resilience

> **Presenter:** Member 1  
> **Target Audience:** Hackathon Technical Judges & Evaluation Panel  
> **Total Time:** 5 to 7 Minutes  
> **Key Objective:** Deliver a structured, technically sound, and honest presentation of the infrastructure resilience module, demonstrating live code execution, mathematical models, and seamless team integration.

---

## Stage-by-Stage Demonstration Guide

### STAGE 1: Introduce the Problem & Mission (0:00 – 0:45)
- **What to Show on Screen:** Title slide or the open terminal in VS Code / Antigravity showing the project directory `SANJIVANI`.
- **What to Say to Judges:**
  > *"Respected judges, during catastrophic floods and storms, casualties often do not happen solely from water levels—they happen because **critical lifelines fail**. When a road or bridge collapses, neighborhoods are severed from trauma centers, and ambulances are trapped on the wrong side of the river.*
  >
  > *I am Member 1 of project **SANJEEVANI**. Our tagline is: **Predict the failure. Protect the connection. Save the response time.**
  >
  > *Our module is the physical infrastructure and vulnerability backbone of SANJEEVANI. We model the city as a connected graph, calculate single points of failure, simulate road collapses, measure human life impact, and recommend where ambulances, boats, and emergency supplies must be pre-positioned **before** disaster strikes."*

---

### STAGE 2: Show the Synthetic City Network (0:45 – 1:30)
- **What to Show on Screen:** Open [`outputs/viz_city_network.png`](file:///c:/Users/dell/Desktop/SANJIVANI/outputs/viz_city_network.png).
- **Exact File:** `outputs/viz_city_network.png` (or run `python -c "import main; main.plot_city_network(...)"`).
- **What to Say to Judges:**
  > *"Here is our municipal network model. We modeled a synthetic municipality with 16 landmarks and 20 transit corridors:*
  > - ***6 Residential Wards (Blue circles):** Home to 90,000 citizens, sized by population density.
  > - ***2 Critical Hospitals (Crimson red):** City General Hospital (`H1`, 450 beds) in the west and Apex Trauma Center (`H2`, 250 beds) in the east.
  > - ***2 Evacuation Shelters (Emerald green):** North Stadium (`S1`, 3,500 capacity) and Civic High Camp (`S2`, 2,000 capacity).
  > - ***2 Emergency Response Bases (Amber orange):** Central Hub `E1` and Westside Depot `E2`.
  > - ***3 Physical Bridges (Thick purple lines):** Spanning the central river divider.*
  >
  > *Every road carries distance in kilometers, travel time in minutes, physical failure probability, and flood sensitivity."*
- **Potential Judge Question:**
  - *"Why did you model the city as an undirected graph rather than directed?"*
- **Your Answer:**
  - *"Under normal and emergency conditions, two-way municipal roads allow emergency vehicles and evacuations to flow in either direction. Directional lane reversals during active evacuations can be layered on top by Member 3 as directed subgraphs."*

---

### STAGE 3: Explain How the System Identifies Critical Roads (1:30 – 2:15)
- **What to Show on Screen:** Open [`outputs/viz_critical_roads.png`](file:///c:/Users/dell/Desktop/SANJIVANI/outputs/viz_critical_roads.png).
- **What to Say to Judges:**
  > *"To identify critical infrastructure without using opaque black boxes, we use explainable graph theory:*
  > 1. ***Edge Betweenness Centrality:** Using travel time (`travel_time_min`) as edge weights across shortest paths, we compute how many fastest routes cross each road. Grand River Bridge `RD11` has the city's highest centrality at **0.3500**—over 35% of all fastest trips rely on it.
  > 2. ***Graph-Theoretic Cut-Edges:** We detect single points of failure—edges whose loss strictly increases the number of connected components. In our city, road `RD04` is a cut-edge that solely connects Hilltop Suburb `R3`.
  >
  > *In this map, our algorithm color-codes every road: Crimson Red for CRITICAL, Deep Orange for HIGH, Amber for MODERATE, and Grey for LOW."*
- **Potential Judge Question:**
  - *"What is the difference between a physical bridge and a graph cut-edge?"*
- **Your Answer:**
  - *"A physical bridge is a civil engineering structure spanning water—like `RD11`. A cut-edge is a topological bottleneck—like `RD04`. `RD11` is exposed to floods, but alternative detours exist across the river. `RD04` is an asphalt road, but its loss completely severs 9,500 citizens with zero alternative paths."*

---

### STAGE 4: Demonstrate Scenario A — RD04 Failure and R3 Isolation (2:15 – 3:00)
- **What to Show on Screen:** Open [`outputs/viz_rd04_failure.png`](file:///c:/Users/dell/Desktop/SANJIVANI/outputs/viz_rd04_failure.png) and terminal showing:
  ```powershell
  .\.venv\Scripts\python.exe -c "import resilience, data; G=data.build_synthetic_city(); r=resilience.simulate_road_failure(G, 'RD04'); print(r['scenario_id'], 'Isolated:', r['disconnected_residential_zones'])"
  ```
- **What to Say to Judges:**
  > *"Now let's simulate a failure. When road `RD04` collapses:
  > - The red dashed line shows the severed road.
  > - The glowing red warning halo highlights **Hilltop Suburb `R3`**.
  > - Connected components increase from 1 to 2.
  > - **9,500 citizens in `R3` lose 100% of access to all hospitals and shelters**.
  > - Notice that our engine strictly avoided double-counting: even though they lost both hospital and shelter access, the affected population is counted as 9,500, not 19,000."*
- **Potential Judge Question:**
  - *"Did this simulation mutate your baseline city graph?"*
- **Your Answer:**
  - *"No. All simulations run on independent graph clones. Our automated tests assert that the original city graph maintains all 16 nodes and 20 edges before and after every simulation."*

---

### STAGE 5: Demonstrate Scenario B — RD11 Failure and Alternative Detours (3:00 – 3:45)
- **What to Show on Screen:** Open [`outputs/viz_rd11_failure.png`](file:///c:/Users/dell/Desktop/SANJIVANI/outputs/viz_rd11_failure.png).
- **What to Say to Judges:**
  > *"Next, let's observe Scenario B: Grand River Bridge `RD11` collapses under floodwaters.
  > - Notice that unlike Scenario A, **no residential zone turns red**.
  > - Why? Because our graph algorithms verified that alternative routes exist via `RD18/RD19` (South Bank Causeway) and `RD17` (Civic Overpass).
  > - However, citizens experience **emergency travel time delays**. Cross-river ambulance transit from Riverside `R1` to Apex Trauma Center increases from **18.4 to 22.0 minutes** (+3.6 min detour)."*
- **Potential Judge Question:**
  - *"What if both RD11 and the southern causeway RD19 fail at the same time?"*
- **Your Answer:**
  - *"Our function `simulate_multiple_failures()` handles compound closures. If both fail, traffic routes across the northern overpass `RD17`. If `RD17` also fails, the city partitions into East and West components, but each half retains access to its local hospital (`H1` in the west, `H2` in the east)."*

---

### STAGE 6: Human Impact & Comprehensive Road Ranking (3:45 – 4:30)
- **What to Show on Screen:** Open [`outputs/critical_road_ranking.csv`](file:///c:/Users/dell/Desktop/SANJIVANI/outputs/critical_road_ranking.csv) in a table viewer or terminal print:
  ```powershell
  .\.venv\Scripts\python.exe -c "import pandas as pd; df=pd.read_csv('outputs/critical_road_ranking.csv'); print(df[['road_id', 'road_name', 'criticality_level', 'comprehensive_criticality_score', 'unique_population_losing_access', 'population_with_delayed_hospital_access']].head(5).to_string(index=False))"
  ```
- **What to Say to Judges:**
  > *"Here is our core innovation: **The Three-Dimensional Critical Road Ranking**.
  > Standard disaster models often suffer from the **'Harmless Delay Trap'**—they assign zero risk to a road if residents aren't 100% cut off.
  > Look at row 2: `RD10 (Downtown Hospital Expressway)`. Zero citizens lose 100% access, but **42,000 citizens experience a +14.9-minute hospital delay**.
  > Our Peak-Blend Multi-Criteria model evaluates:
  > - Dimension A: Acute Access Loss
  > - Dimension B: Medical Response Delay
  > - Dimension C: Physical Hazard & Betweenness
  > Because `RD10` has a severe delay score of 0.9970, our formula elevates it to **CRITICAL** alongside `RD04`."*
- **Potential Judge Question:**
  - *"How do you combine population, probabilities, and delay minutes without distorting dimensions?"*
- **Your Answer:**
  - *"Every dimension is independently normalized to a $[0.0, 1.0]$ scale using municipal threshold benchmarks (such as a 15-minute emergency response delay surge) before applying our Peak-Blend formulation."*

---

### STAGE 7: Pre-Disaster Emergency Resource Positioning (4:30 – 5:15)
- **What to Show on Screen:** Open [`outputs/viz_resource_plan.png`](file:///c:/Users/dell/Desktop/SANJIVANI/outputs/viz_resource_plan.png).
- **What to Say to Judges:**
  > *"Before the storm arrives, authorities must pre-position emergency assets. Here is our pre-disaster staging plan across 4 asset classes:
  > 1. ***Ambulances:** Staged at Central Hub `E1`, hospitals `H1` and `H2`, and dense core `R2` to cover 50,000 citizens within 8 minutes.
  > 2. ***Rescue Boats:** Staged at riverbank depot `E2` and flood-prone waterfront wards `R1` and `R6`.
  > 3. ***Rescue Teams:** Staged across emergency bases `E1`, `E2` and evacuation shelters `S1`, `S2`.
  > 4. ***Emergency Supplies:** Look at our #1 recommendation: **Hilltop Suburb `R3`**. Why? Because `R3` relies on cut-edge `RD04`. Emergency food, water, and generators **must be pre-positioned inside `R3` before the road fails**, because supply trucks cannot enter afterwards."*
- **Potential Judge Question:**
  - *"Is this resource allocation mathematically optimal?"*
- **Your Answer:**
  - *"No, and we explicitly document that. It is an explainable demand-capacity greedy heuristic designed to provide immediate decision support for human commanders, rather than claiming to solve an NP-hard facility location problem in real time."*

---

### STAGE 8: Generated Outputs & Team Integration (5:15 – 6:00)
- **What to Show on Screen:** Open [`outputs/`](file:///c:/Users/dell/Desktop/SANJIVANI/outputs/) showing all 14 files, then run pytest:
  ```powershell
  .\.venv\Scripts\pytest -v
  ```
- **What to Say to Judges:**
  > *"Our entire pipeline runs in seconds via `main.py` and exports 14 structured artifacts:
  > - ***Member 2** links citizen distress reports to our standardized `node_id` and `road_id` targets.
  > - ***Member 3** imports our scenario graphs to simulate hydrological flood levels and calculate dynamic rescue boat paths.
  > - ***Member 4** connects our CSV tables and 5 high-resolution maps directly into our Streamlit executive dashboard.
  >
  > *As you can see on screen, all **42 automated Pytest tests pass with a 100% success rate**, verifying graph non-mutation, mathematical bounds, and data schema integrity."*

---

### STAGE 9 & 10: Limitations, Future Scope & Conclusion (6:00 – 6:45)
- **What to Say to Judges:**
  > *"In the spirit of scientific honesty:
  > 1. All geographical data is synthetic.
  > 2. Failure probabilities are normalized prototype scores rather than calibrated civil engineering sensor feeds.
  > 3. Boat staging assumes verified shoreline launch ramps.
  >
  > *In the future, we plan to ingest OpenStreetMap geospatial GeoJSON and municipal IoT water-level sensor feeds.
  >
  > *SANJEEVANI Module 1 proves that with explainable graph intelligence, we can predict infrastructure failure, protect community connectivity, and save critical response time.
  >
  > *Thank you, judges! We welcome your questions."*

