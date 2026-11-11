# 🛡️ SANJEEVANI

**Human-Centric Disaster Intelligence, Infrastructure Resilience & Autonomous Emergency Response Network**

> *"Predict the failure. Protect the connection. Save the response time."*

---

## 1. Overview & Closed-Loop Workflow

**SANJEEVANI** is an Emergency Operations Centre (EOC) decision-support prototype built with **Python**, **Streamlit**, **NetworkX**, **Folium**, and **Plotly**. It models urban flood and severe weather impacts on road infrastructure, hospital reachability, incoming emergency reports, and autonomous ambulance routing across a closed-loop operational cycle:

```text
1. OBSERVE  →  2. ESTIMATE  →  3. SIMULATE  →  4. OPTIMIZE  →  5. VERIFY  →  6. REPEAT
```

> **Note:** All datasets, road networks, rainfall projections, and incident streams in this repository are **synthetic prototype data** (`SYNTHETIC_PROTOTYPE`) designed for decision-support simulation and benchmarking.

---

## 2. Six-Section Dashboard Architecture

1. **Section 1 — Overview:** Executive EOC command view with 6 equal-height KPI cards, interactive dark-themed Folium GIS map, priority alerts, road failure probability chart, and live SHA-256 session activity stream.
2. **Section 2 — Resilience Lab (`sanjeevani/resilience.py`):** Interactive `NetworkX` city graph (`6` junctions, `8` road corridors, `3` hospital hubs), single/multi-road failure stress simulator, sector-to-hospital accessibility table, and criticality rankings.
3. **Section 3 — Live Response (`sanjeevani/evidence.py`):** Incoming emergency report queue with urgency/verification filters, HTML-sanitized report intake form, synthetic evidence confidence scoring, duplicate-image detection warnings, and disaster-specific field precautions.
4. **Section 4 — Future Intelligence (`sanjeevani/twin.py`):** Digital Twin rainfall intensity simulator (`0–150 mm/hr`), `T+0` (Current), `T+15m`, `T+30m`, and `T+60m` horizon projections, cached 7-step rainfall sensitivity curve, cascading infrastructure impacts, and active sensor/drone observation recommendations.
5. **Section 5 — Rescue Planning (`sanjeevani/decision.py`):** Autonomous two-leg (`Rescue Unit → Incident → Reachable Hospital`) `NetworkX` routing comparing **Strategy A (Shortest Distance)**, **Strategy B (Fastest Response)**, and **Strategy C (SANJEEVANI Risk-Aware Response)** while strictly excluding `BLOCKED` corridors.
6. **Section 6 — Benchmark & Audit (`sanjeevani/benchmark.py`, `sanjeevani/audit.py`):** Side-by-side strategy performance benchmarking on identical graph/incident inputs, plus a tamper-evident **SHA-256 hash-chained operational audit log** with interactive integrity verification and tamper detection demo.

---

## 3. Project Directory Structure

```text
sanjeevni/
├── app.py                      # Main Streamlit 6-section EOC Dashboard UI
├── requirements.txt            # Python package dependencies
├── README.md                   # Project documentation
├── data/
│   └── sample_data.csv         # Sample synthetic emergency incident dataset
├── sanjeevani/
│   ├── __init__.py             # Core package initializer
│   ├── data.py                 # Synthetic scenarios, NetworkX road graph & baseline telemetry
│   ├── resilience.py           # Member 1: Infrastructure Resilience & road failure stress testing
│   ├── evidence.py             # Member 2: Emergency Report Scoring, XSS sanitization & filtering
│   ├── twin.py                 # Member 3 (Part A): Digital Twin T+0/T+15/T+30/T+60 projections
│   ├── decision.py             # Member 3 (Part B): Two-leg NetworkX rescue routing (Strategies A/B/C)
│   ├── benchmark.py            # Member 4 (Part A): Comparative strategy benchmarking engine
│   └── audit.py                # Member 4 (Part B): SHA-256 hash-chained operational audit log
└── tests/
    └── test_core.py            # 21 automated unit, edge-case & 6-section smoke tests
```

---

## 4. Installation & Running the Dashboard

```powershell
# 1. Activate the virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the SANJEEVANI Streamlit Dashboard
streamlit run app.py
```

---

## 5. Running Compilation & Automated Tests

```powershell
# Compile all Python modules
.\.venv\Scripts\python.exe -m compileall app.py sanjeevani tests

# Run the 21 automated unit, edge-case, and section smoke tests
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
