# SANJEEVANI — Human-Centric Disaster Intelligence & Infrastructure Resilience

> **Full Title:** Human-Centric Disaster Intelligence, Infrastructure Resilience & Autonomous Emergency Response Network  
> **Tagline:** *Predict the failure. Protect the connection. Save the response time.*  
> **Module 1 Owner:** Disaster Prediction & Infrastructure Resilience  

---

## 1. Project Introduction

**SANJEEVANI** is an explainable disaster-management decision-support platform designed to assist municipal and emergency authorities in anticipating infrastructure failures, evaluating civilian isolation, and pre-positioning life-saving resources before extreme disasters occur.

The system follows a continuous operational feedback loop:
$$\text{OBSERVE} \longrightarrow \text{ESTIMATE} \longrightarrow \text{SIMULATE} \longrightarrow \text{OPTIMIZE} \longrightarrow \text{VERIFY} \longrightarrow \text{REPEAT}$$

> [!IMPORTANT]
> **Scientific & Prototype Disclaimer:**  
> All geographical data, populations, failure probabilities, and resource recommendations generated in this module are **synthetic prototypes** built for decision-support testing. They support human decision-making and do not claim to replace calibrated civil engineering structural surveys or official government emergency command protocols.

---

## 2. Member 1 Module Responsibilities

As Member 1 of a four-member hackathon team, this module owns the foundational infrastructure and physical resilience layer:
- **Synthetic City Road Network:** 16 nodes (residential wards, hospitals, shelters, emergency stations, junctions) and 20 roads/bridges.
- **Topological Fragility Analysis:** Edge betweenness centrality and biconnected component cut-edges.
- **Non-Destructive Failure Simulation:** Scenarios for single cut-edges (`RD04`) and arterial bridges (`RD11`).
- **Human Impact Estimation:** Non-double-counted population isolation and emergency medical travel delay quantification.
- **Critical Road Ranking:** Multi-criteria three-dimensional prioritization (MCDA Peak-Blend formula).
- **Pre-Disaster Resource Positioning:** Staging recommendations for ambulances, boats, rescue teams, and supplies.
- **Structured Artifact Generation:** 14 deliverables (9 JSON/CSV files + 5 PNG network maps).

---

## 3. System Requirements & Environment

- **Operating System:** Windows 11 / Windows 10 (or Linux/macOS)
- **Python Version:** Python 3.12 (64-bit) recommended (compatible with Python 3.10+)
- **Core Python Libraries:**
  - `networkx` ($\ge 3.4$)
  - `pandas` ($\ge 2.2$)
  - `numpy` ($\ge 2.0$)
  - `matplotlib` ($\ge 3.9$)
  - `pytest` ($\ge 9.0$)

---

## 4. Virtual Environment Activation & Installation

### Option A: Using the Existing Configured `.venv` (Recommended)
The workspace already contains a pre-configured Python virtual environment (`.venv`) with all dependencies installed.

Activate the virtual environment in Windows PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell execution policy blocks script activation, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

Alternatively, call the virtual environment's Python executable directly:
```powershell
.\.venv\Scripts\python.exe <script_name>.py
```

### Option B: Fresh Setup from Scratch (If Recreating Environment)
```powershell
# 1. Create a virtual environment using Python 3.12
python -m venv .venv

# 2. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Install core dependencies
pip install networkx pandas numpy matplotlib pytest
```

---

## 5. Execution Commands

### Execute Master Demonstration Pipeline
To run the full end-to-end resilience analysis workflow, print formatted summary tables, and regenerate all 14 artifacts in `outputs/`:
```powershell
.\.venv\Scripts\python.exe main.py
```

### Execute Automated Pytest Test Suite
To run all 42 automated tests and view verbose test-by-test validation:
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

---

## 6. Project Directory Structure

```text
SANJIVANI/
├── .venv/                              # Python 3.12 Virtual Environment
├── pytest.ini                          # Pytest configuration (pythonpath = .)
├── data.py                             # Graph network generator & data models
├── resilience.py                       # Analytical engine & heuristic algorithms
├── main.py                             # Master pipeline & visualization runner
├── README.md                           # Master Project Readme
│
├── data/
│   └── synthetic_city.json             # Serialized baseline synthetic city
│
├── docs/                               # Comprehensive Technical Documentation (Priority 8)
│   ├── MEMBER_1_TECHNICAL_DOCUMENTATION.md  # Deep technical reference & mathematical models
│   ├── TEAM_INTEGRATION_CONTRACT.md         # Hand-off guides for Members 2, 3, and 4
│   ├── FUNCTION_REFERENCE.md                # Complete API documentation for all functions
│   ├── JUDGE_DEMONSTRATION.md               # 5 to 7-minute pitch script & Q&A defense
│   └── DEMO_CHECKLIST.md                    # Pre-presentation readiness checklist
│
├── tests/
│   └── test_resilience.py              # Automated test suite (42 tests, 100% pass rate)
│
└── outputs/                            # Structured Deliverables (Priority 7 & 8)
    ├── city_summary.json               # Baseline citywide summary metrics
    ├── baseline_city_network.json      # Full graph serialized (nodes, pos, roads)
    ├── rd04_failure_scenario.json      # Scenario A: RD04 cut-edge isolation
    ├── rd11_failure_scenario.json      # Scenario B: RD11 bridge closure & detours
    ├── human_impact_results.csv        # Disconnected vs delayed pop across 20 roads
    ├── critical_road_ranking.csv       # 19-column multi-criteria ranked road table
    ├── critical_road_ranking.json      # Structured ranked roads with methodology
    ├── resource_positioning_plan.csv   # Staging recommendations table
    ├── resource_positioning_plan.json  # Grouped node allocations & inventories
    ├── viz_city_network.png            # Visual Map 1: Baseline City Network (150 DPI)
    ├── viz_critical_roads.png          # Visual Map 2: Critical Roads by Risk Color (150 DPI)
    ├── viz_rd04_failure.png            # Visual Map 3: Scenario A Isolation Map (150 DPI)
    ├── viz_rd11_failure.png            # Visual Map 4: Scenario B Detour Map (150 DPI)
    └── viz_resource_plan.png           # Visual Map 5: Resource Staging Map (150 DPI)
```

---

## 7. Deliverables & Outputs Registry (`outputs/`)

All generated data and cartographic maps are saved in [`outputs/`](file:///c:/Users/dell/Desktop/SANJIVANI/outputs/):
1. **`city_summary.json`:** High-level summary (population: 90,000; hospital beds: 700; shelters: 5,500).
2. **`baseline_city_network.json`:** Full graph structure with coordinates, capacities, and flood exposure.
3. **`rd04_failure_scenario.json`:** Scenario A results isolating 9,500 residents in `R3: Hilltop Suburb`.
4. **`rd11_failure_scenario.json`:** Scenario B results for Grand River Bridge showing active bypass detours.
5. **`human_impact_results.csv`:** Single-failure impact across all 20 roads.
6. **`critical_road_ranking.csv` & `.json`:** Comprehensive three-dimensional road prioritization table.
7. **`resource_positioning_plan.csv` & `.json`:** Pre-disaster asset staging plan across 10 strategic nodes.
8. **5 Visual PNG Network Maps:** Publication-grade visual diagrams (150 DPI) illustrating baseline topology, critical roads, failure scenarios, and staged emergency assets.

---

## 8. Integration for Other Team Members

- **Member 2 (Evidence Intelligence):** Map incoming citizen reports to standardized `node_id` (`R1`–`R6`, `H1`, `H2`, `S1`, `S2`, `E1`, `E2`, `J1`–`J4`) and `road_id` (`RD01`–`RD20`).
- **Member 3 (Simulation & Rescue Routing):** Call `build_synthetic_city()` and `simulate_multiple_failures()` to obtain active routing graphs during dynamic flooding.
- **Member 4 (Streamlit Dashboard):** Load ready-to-display CSV tables with `pd.read_csv("outputs/critical_road_ranking.csv")` and display visual maps using `st.image("outputs/viz_city_network.png")`.

See [`docs/TEAM_INTEGRATION_CONTRACT.md`](file:///c:/Users/dell/Desktop/SANJIVANI/docs/TEAM_INTEGRATION_CONTRACT.md) for complete code examples.

---

## 9. Limitations & Scientific Honesty

- **Synthetic Data & Coordinates:** Municipal landmarks and road coordinates `(x, y)` are synthetic 2D integer Cartesian grid coordinates on a 100×100 layout plane designed for schematic network visualization. They are not geographic GPS coordinates (latitude/longitude), and cannot be resolved with external geocoding or measured with spherical Haversine formulas.
- **Probability Scores:** Road failure probabilities and flood sensitivities are normalized heuristic indicators ($[0.0, 1.0]$), not calibrated outputs of hydraulic hydrological physics models.
- **Water Access:** Rescue boat staging assumes shoreline readiness for inflatable flood rescue craft.
- **Decision Support:** Designed to assist human disaster commanders and emergency authorities, not replace government crisis response protocols.
