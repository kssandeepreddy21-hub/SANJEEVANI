# 🛡️ SANJEEVANI — Human-Centric Disaster Intelligence & Infrastructure Resilience

> **Full Title:** Human-Centric Disaster Intelligence, Infrastructure Resilience & Autonomous Emergency Response Network  
> **Tagline:** *"Predict the failure. Protect the connection. Save the response time."*

---

## 1. Project Introduction & Closed-Loop Workflow

**SANJEEVANI** is an explainable disaster-management and Emergency Operations Centre (EOC) decision-support platform designed to assist municipal and emergency authorities in anticipating infrastructure failures, evaluating civilian isolation, verifying incoming emergency reports, simulating rainfall progression, pre-positioning life-saving resources, and optimizing autonomous emergency routing before and during extreme disasters.

The system follows a continuous six-stage operational feedback loop:

```text
1. OBSERVE  →  2. ESTIMATE  →  3. SIMULATE  →  4. OPTIMIZE  →  5. VERIFY  →  6. REPEAT
```

$$\text{OBSERVE} \longrightarrow \text{ESTIMATE} \longrightarrow \text{SIMULATE} \longrightarrow \text{OPTIMIZE} \longrightarrow \text{VERIFY} \longrightarrow \text{REPEAT}$$

> [!IMPORTANT]
> **Scientific, Prototype & Decision-Support Disclaimer:**  
> All geographical data, road networks, rainfall projections, populations, failure probabilities, incident streams, and resource recommendations in this repository are **synthetic prototype data** (`SYNTHETIC_PROTOTYPE`) built for decision-support simulation, stress-testing, and benchmarking. They are designed to support human decision-making and do not claim to replace calibrated civil engineering structural surveys, meteorological physics forecasts, or official government emergency command protocols.

---

## 2. How the Modules Fit into the Overall SANJEEVANI Architecture

SANJEEVANI is organized as a modular four-member team architecture where the analytical backend engines and the interactive command dashboard operate together across the closed-loop workflow:

- **Member 1 — Disaster Prediction & Infrastructure Resilience (`data.py`, `resilience.py`, `main.py`, `sanjeevani/resilience.py`):** Owns the foundational physical infrastructure and graph resilience layer (`OBSERVE → ESTIMATE`), modeling topological fragility, cut-edges, human isolation, multi-criteria road criticality ranking, pre-disaster resource staging, and generating the 14 structured JSON/CSV/PNG deliverables in `outputs/`.
- **Member 2 — Emergency Report Analysis & Evidence Intelligence (`sanjeevani/evidence.py`):** Owns incoming citizen and field report ingestion (`OBSERVE → VERIFY`), HTML/XSS input sanitization, synthetic evidence confidence scoring, and duplicate/recycled media detection.
- **Member 3 — Digital Twin Simulation & Autonomous Rescue Routing (`sanjeevani/twin.py`, `sanjeevani/decision.py`):** Owns the `T+0 / T+15m / T+30m / T+60m` rainfall projection engine (`SIMULATE`) and two-leg (`Rescue Unit → Incident → Reachable Hospital`) `NetworkX` shortest-path optimization (`OPTIMIZE`) comparing Strategy A, Strategy B, and Strategy C.
- **Member 4 — Six-Section Streamlit EOC Dashboard, Benchmarking & SHA-256 Audit (`app.py`, `sanjeevani/benchmark.py`, `sanjeevani/audit.py`):** Owns the unified six-section Streamlit command-and-control interface, interactive Folium GIS mapping, Plotly telemetry visualizations, side-by-side strategy performance benchmarking, and the tamper-evident SHA-256 hash-chained operational audit log (`VERIFY → REPEAT`).

---

## 3. Member 1 Module: Disaster Prediction & Infrastructure Resilience

As Member 1 of the four-member hackathon team, this module provides the standalone analytical pipeline (`main.py`, `data.py`, `resilience.py`) and foundational physical resilience layer:

- **Synthetic City Road Network:** 16 nodes (residential wards `R1`–`R6`, hospitals `H1`–`H2`, shelters `S1`–`S2`, emergency stations `E1`–`E2`, junctions `J1`–`J4`) and 20 roads/bridges (`RD01`–`RD20`).
- **Topological Fragility Analysis:** Edge betweenness centrality and biconnected component cut-edges.
- **Non-Destructive Failure Simulation:** Scenarios for single cut-edges (`RD04`) and arterial bridges (`RD11`).
- **Human Impact Estimation:** Non-double-counted population isolation and emergency medical travel delay quantification.
- **Critical Road Ranking:** Multi-criteria three-dimensional prioritization (MCDA Peak-Blend formula).
- **Pre-Disaster Resource Positioning:** Staging recommendations for ambulances, boats, rescue teams, and supplies.
- **Structured Artifact Generation:** 14 deliverables (9 JSON/CSV files + 5 PNG network maps saved to `outputs/`).

### Integration Contract for Team Members
- **Member 2 (Evidence Intelligence):** Map incoming citizen reports to standardized `node_id` (`R1`–`R6`, `H1`, `H2`, `S1`, `S2`, `E1`, `E2`, `J1`–`J4`) and `road_id` (`RD01`–`RD20`).
- **Member 3 (Simulation & Rescue Routing):** Call `build_synthetic_city()` and `simulate_multiple_failures()` to obtain active routing graphs during dynamic flooding.
- **Member 4 (Streamlit Dashboard):** Load ready-to-display CSV tables with `pd.read_csv("outputs/critical_road_ranking.csv")` and display visual maps using `st.image("outputs/viz_city_network.png")`, or interact dynamically via `sanjeevani/resilience.py`.

See `docs/TEAM_INTEGRATION_CONTRACT.md` for complete code examples.

---

## 4. Member 4 Module: Six-Section Streamlit EOC Dashboard

The interactive Streamlit Emergency Operations Centre (`app.py`) integrates all six operational sections using **Python**, **Streamlit**, **NetworkX**, **Folium**, and **Plotly**:

1. **Section 1 — Overview:** Executive EOC command view with 6 equal-height KPI cards, interactive dark-themed Folium GIS map, priority alerts, road failure probability chart, and live SHA-256 session activity stream.
2. **Section 2 — Resilience Lab (`sanjeevani/resilience.py`):** Interactive `NetworkX` city graph (`6` junctions, `8` road corridors, `3` hospital hubs), single/multi-road failure stress simulator, sector-to-hospital accessibility table, and criticality rankings.
3. **Section 3 — Live Response (`sanjeevani/evidence.py`):** Incoming emergency report queue with urgency/verification filters, HTML-sanitized report intake form, synthetic evidence confidence scoring, duplicate-image detection warnings, and disaster-specific field precautions.
4. **Section 4 — Future Intelligence (`sanjeevani/twin.py`):** Digital Twin rainfall intensity simulator (`0–150 mm/hr`), `T+0` (Current), `T+15m`, `T+30m`, and `T+60m` horizon projections, cached 7-step rainfall sensitivity curve, cascading infrastructure impacts, and active sensor/drone observation recommendations.
5. **Section 5 — Rescue Planning (`sanjeevani/decision.py`):** Autonomous two-leg (`Rescue Unit → Incident → Reachable Hospital`) `NetworkX` routing comparing **Strategy A (Shortest Distance)**, **Strategy B (Fastest Response)**, and **Strategy C (SANJEEVANI Risk-Aware Response)** while strictly excluding `BLOCKED` corridors.
6. **Section 6 — Benchmark & Audit (`sanjeevani/benchmark.py`, `sanjeevani/audit.py`):** Side-by-side strategy performance benchmarking on identical graph/incident inputs, plus a tamper-evident **SHA-256 hash-chained operational audit log** with interactive integrity verification and tamper detection demo.

---

## 5. Combined Project Directory Structure

```text
sanjeevni/
├── .venv/                                       # Python Virtual Environment
├── pytest.ini                                   # Pytest configuration (pythonpath = .)
├── requirements.txt                             # Python package dependencies
├── README.md                                    # Unified Master Project README
│
├── app.py                                       # Member 4: Main Streamlit 6-section EOC Dashboard UI
├── data.py                                      # Member 1: 16-node / 20-road graph generator & data models
├── resilience.py                                # Member 1: Analytical engine & heuristic algorithms
├── main.py                                      # Member 1: Master pipeline & visualization runner
│
├── data/
│   ├── synthetic_city.json                      # Member 1: Serialized baseline synthetic city
│   └── sample_data.csv                          # Member 4: Sample synthetic emergency incident dataset
│
├── sanjeevani/                                  # Member 4 Integrated Dashboard Backend Package
│   ├── __init__.py                              # Core package initializer
│   ├── data.py                                  # Synthetic scenarios, NetworkX road graph & baseline telemetry
│   ├── resilience.py                            # Member 1 Dashboard Interface: Road failure stress testing
│   ├── evidence.py                              # Member 2 Dashboard Interface: Report scoring, XSS sanitization & filtering
│   ├── twin.py                                  # Member 3 (Part A): Digital Twin T+0/T+15/T+30/T+60 projections
│   ├── decision.py                              # Member 3 (Part B): Two-leg NetworkX rescue routing (Strategies A/B/C)
│   ├── benchmark.py                             # Member 4 (Part A): Comparative strategy benchmarking engine
│   └── audit.py                                 # Member 4 (Part B): SHA-256 hash-chained operational audit log
│
├── docs/                                        # Member 1 Comprehensive Technical Documentation
│   ├── MEMBER_1_TECHNICAL_DOCUMENTATION.md      # Deep technical reference & mathematical models
│   ├── TEAM_INTEGRATION_CONTRACT.md             # Hand-off guides for Members 2, 3, and 4
│   ├── FUNCTION_REFERENCE.md                    # Complete API documentation for all functions
│   ├── JUDGE_DEMONSTRATION.md                   # 5 to 7-minute pitch script & Q&A defense
│   └── DEMO_CHECKLIST.md                        # Pre-presentation readiness checklist
│
├── tests/
│   ├── test_resilience.py                       # Member 1 Pytest Suite (42 tests for standalone resilience engine)
│   └── test_core.py                             # Member 4 Unittest Suite (21 unit, edge-case & 6-section smoke tests)
│
└── outputs/                                     # Member 1 Structured Deliverables (14 files)
    ├── city_summary.json                        # Baseline citywide summary metrics
    ├── baseline_city_network.json               # Full graph serialized (nodes, pos, roads)
    ├── rd04_failure_scenario.json               # Scenario A: RD04 cut-edge isolation
    ├── rd11_failure_scenario.json               # Scenario B: RD11 bridge closure & detours
    ├── human_impact_results.csv                 # Disconnected vs delayed pop across 20 roads
    ├── critical_road_ranking.csv                # 19-column multi-criteria ranked road table
    ├── critical_road_ranking.json               # Structured ranked roads with methodology
    ├── resource_positioning_plan.csv            # Staging recommendations table
    ├── resource_positioning_plan.json           # Grouped node allocations & inventories
    ├── viz_city_network.png                     # Visual Map 1: Baseline City Network (150 DPI)
    ├── viz_critical_roads.png                   # Visual Map 2: Critical Roads by Risk Color (150 DPI)
    ├── viz_rd04_failure.png                     # Visual Map 3: Scenario A Isolation Map (150 DPI)
    ├── viz_rd11_failure.png                     # Visual Map 4: Scenario B Detour Map (150 DPI)
    └── viz_resource_plan.png                    # Visual Map 5: Resource Staging Map (150 DPI)
```

---

## 6. System Requirements & Installation Instructions

- **Operating System:** Windows 11 / Windows 10 (or Linux/macOS)
- **Python Version:** Python 3.10+ (Python 3.12 / 3.14 supported)
- **Core Python Libraries:**
  - `streamlit`
  - `networkx` ($\ge 3.4$)
  - `pandas` ($\ge 2.2$)
  - `numpy` ($\ge 2.0$)
  - `plotly`
  - `folium`
  - `streamlit-folium`
  - `matplotlib` ($\ge 3.9$)
  - `pytest` ($\ge 9.0$)

### Option A: Using the Existing Configured `.venv` (Recommended)
Activate the virtual environment in Windows PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell execution policy blocks script activation, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

### Option B: Fresh Setup from Scratch
```powershell
# 1. Create a virtual environment
python -m venv .venv

# 2. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Install dashboard & analytical dependencies
pip install -r requirements.txt
pip install matplotlib pytest
```

---

## 7. Execution Commands

### A. Launch the Member 4 Six-Section Streamlit EOC Dashboard
```powershell
streamlit run app.py
```

### B. Execute the Member 1 Master Resilience Pipeline
To run the standalone end-to-end resilience analysis workflow, print formatted summary tables, and regenerate all 14 artifacts in `outputs/`:
```powershell
.\.venv\Scripts\python.exe main.py
```

---

## 8. Testing Commands (Separate Member 1 & Member 4 Test Suites)

The repository maintains **two separate automated test suites** for the standalone Member 1 engine and the integrated Member 4 dashboard package:

### Suite 1 — Member 1 Standalone Resilience Pytest Suite (`42` Tests)
Validates the 16-node / 20-road infrastructure resilience engine (`data.py`, `resilience.py`, `main.py`, and `tests/test_resilience.py`):
```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_resilience.py -v
```

### Suite 2 — Member 4 Dashboard & Six-Section Unittest Suite (`21` Tests)
Validates the six-section Streamlit dashboard backend (`sanjeevani/*`), SHA-256 hash-chained audit log, edge cases, and independent timeout-guarded section smoke tests (`tests/test_core.py`):
```powershell
# Compile all dashboard & core modules
.\.venv\Scripts\python.exe -m compileall app.py sanjeevani tests

# Run the 21 automated unittest tests in tests/test_core.py
.\.venv\Scripts\python.exe -m unittest tests/test_core.py -v
```

---

## 9. Member 1 Deliverables & Outputs Registry (`outputs/`)

All generated data and cartographic maps from `main.py` are saved in `outputs/`:
1. **`city_summary.json`:** High-level summary (population: 90,000; hospital beds: 700; shelters: 5,500).
2. **`baseline_city_network.json`:** Full graph structure with coordinates, capacities, and flood exposure.
3. **`rd04_failure_scenario.json`:** Scenario A results isolating 9,500 residents in `R3: Hilltop Suburb`.
4. **`rd11_failure_scenario.json`:** Scenario B results for Grand River Bridge showing active bypass detours.
5. **`human_impact_results.csv`:** Single-failure impact across all 20 roads.
6. **`critical_road_ranking.csv` & `.json`:** Comprehensive three-dimensional road prioritization table.
7. **`resource_positioning_plan.csv` & `.json`:** Pre-disaster asset staging plan across 10 strategic nodes.
8. **5 Visual PNG Network Maps:** Publication-grade visual diagrams (150 DPI) illustrating baseline topology, critical roads, failure scenarios, and staged emergency assets (`viz_city_network.png`, `viz_critical_roads.png`, `viz_rd04_failure.png`, `viz_rd11_failure.png`, `viz_resource_plan.png`).

---

## 10. Limitations & Scientific Honesty

- **Synthetic Data & Coordinates:**
  - In the **Member 1 standalone pipeline (`data.py`, `resilience.py`)**, municipal landmarks and road coordinates `(x, y)` are synthetic 2D integer Cartesian grid coordinates on a 100×100 layout plane designed for schematic network visualization (not GPS latitude/longitude).
  - In the **Member 4 interactive dashboard (`app.py`, `sanjeevani/*`)**, junctions (`J1`–`J6`), roads (`RD-101`–`RD-108`), hospitals (`HOSP-01`–`HOSP-03`), rescue teams, rainfall curves, and incident streams use synthetic urban coordinates (`SYNTHETIC_PROTOTYPE`) for Leaflet/Folium visualization—not live GIS, meteorological, or government feeds.
- **Probability & Evidence Scores:** Road failure probabilities, flood sensitivities ($[0.0, 1.0]$), and emergency report confidence/duplicate flags are deterministic prototype heuristics rather than calibrated hydraulic physics models or trained computer-vision models.
- **In-Memory Session Audit Log (Not a Blockchain):** The SHA-256 hash chain in `sanjeevani/audit.py` provides tamper-evident cryptographic verification within `st.session_state` for the active dashboard session; it is not a distributed blockchain or persistent external database.
- **Water Access:** Rescue boat staging assumes shoreline readiness for inflatable flood rescue craft.
- **Decision Support Only:** Designed to assist human disaster commanders and emergency authorities, not replace government crisis response protocols.
