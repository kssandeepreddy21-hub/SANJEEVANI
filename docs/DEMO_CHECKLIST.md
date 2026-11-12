# SANJEEVANI — Pre-Presentation Readiness Checklist
## Module 1: Disaster Prediction & Infrastructure Resilience

> **Purpose:** Use this checklist immediately prior to your hackathon presentation or judge evaluation to verify that your environment, tests, outputs, and demonstration scripts are 100% operational.

---

## 1. Environment & Dependencies Verification

- [ ] **Python Installation:** Python 3.12 (64-bit) verified in virtual environment.
  - Verify with: `.\.venv\Scripts\python.exe --version` $\rightarrow$ `Python 3.12.3`
- [ ] **Core Dependencies:** All 5 required packages verified without missing modules.
  - Command: `.\.venv\Scripts\python.exe -c "import networkx, pandas, numpy, matplotlib, pytest; print('Environment OK')"`
- [ ] **Git Repository Status:**
  - Git is not initialized (`.git` is absent). No uncommitted or broken git index exists.

---

## 2. Automated Test Suite Verification

- [ ] **Execute Complete Pytest Suite:**
  - Command: `.\.venv\Scripts\python.exe -m pytest -v`
  - Expected Outcome: **All 42 tests passing with zero failures and zero errors**.
  - Runtime: $\approx 20\text{ seconds}$.
- [ ] **Critical Assertions Tested:**
  - Baseline graph instance & connectivity (16 nodes, 20 edges, 90,000 population).
  - Cut-edge identification (`RD04` single point of failure).
  - Graph preservation across sequential simulations (no graph mutation).
  - Non-double-counting set union logic (R3 affected population = 9,500, not 19,000).
  - Both RD04 (acute isolation) and RD10 (acute delay) classified as `CRITICAL`.
  - Staging plan includes Hilltop Suburb `R3` as #1 priority for supplies.

---

## 3. Master Pipeline Execution & Artifact Generation

- [ ] **Execute Master Pipeline:**
  - Command: `.\.venv\Scripts\python.exe main.py`
  - Expected Outcome: Pipeline runs sequentially through Phases 1 to 7 and exits with code 0.
- [ ] **Verify All 14 Output Artifacts in `outputs/`:**
  - [ ] `city_summary.json` (373 B)
  - [ ] `baseline_city_network.json` (10.7 KB)
  - [ ] `rd04_failure_scenario.json` (6.0 KB)
  - [ ] `rd11_failure_scenario.json` (5.9 KB)
  - [ ] `human_impact_results.csv` (1.3 KB)
  - [ ] `critical_road_ranking.csv` (4.1 KB)
  - [ ] `critical_road_ranking.json` (17.2 KB)
  - [ ] `resource_positioning_plan.csv` (5.1 KB)
  - [ ] `resource_positioning_plan.json` (12.9 KB)
  - [ ] `viz_city_network.png` (> 200 KB, valid PNG)
  - [ ] `viz_critical_roads.png` (> 160 KB, valid PNG)
  - [ ] `viz_rd04_failure.png` (> 165 KB, valid PNG)
  - [ ] `viz_rd11_failure.png` (> 165 KB, valid PNG)
  - [ ] `viz_resource_plan.png` (> 170 KB, valid PNG)

---

## 4. Scenario Outputs Verification

- [ ] **Scenario A (`RD04: Hilltop Access Road`):**
  - Confirmed: Connected components = 2.
  - Confirmed: Isolated residential zone = `['R3']` (9,500 residents).
  - Confirmed: Unique population losing critical service access = 9,500.
  - Confirmed: Risk score = 950.0.
- [ ] **Scenario B (`RD11: Grand River Bridge`):**
  - Confirmed: Connected components = 1 (remains connected via detours).
  - Confirmed: Isolated residential zones = `[]` (zero citizens lose total service reach).
  - Confirmed: Hospital response delays verified (Riverside `R1` to Apex Trauma `H2` delay = +3.6 min).

---

## 5. Pre-Disaster Resource Plan Verification

- [ ] **Total Staged Assets:** 15 assets allocated across 10 strategic city hubs.
- [ ] **Ambulances:** Staged at `E1` (Central Hub), `H2` (Apex Trauma), `H1` (City General), `R2` (Downtown Heights).
- [ ] **Rescue Boats:** Staged at `E2` (Westside river depot), `R1` (Riverside Colony), `R6` (Lakeside Enclave).
- [ ] **Rescue Teams:** Staged across dual-quadrant response bases `E1`, `E2` and evacuation shelters `S1`, `S2`.
- [ ] **Emergency Supplies:** Confirmed that `R3: Hilltop Suburb` is the #1 priority recommendation.

---

## 6. Visual Presentation Readiness

- [ ] Have the 5 PNG files in `outputs/` open in your image viewer or ready to display in tabs:
  - `outputs/viz_city_network.png` (Baseline City Map)
  - `outputs/viz_critical_roads.png` (Critical Road Colors)
  - `outputs/viz_rd04_failure.png` (R3 Cut-Edge Isolation)
  - `outputs/viz_rd11_failure.png` (Bridge Closure & Detour)
  - `outputs/viz_resource_plan.png` (Resource Staging Map)
- [ ] Have the 5-7 minute pitch script ready:
  - [`docs/JUDGE_DEMONSTRATION.md`](file:///c:/Users/dell/Desktop/SANJIVANI/docs/JUDGE_DEMONSTRATION.md)
- [ ] Have the team integration guide ready for teammate questions:
  - [`docs/TEAM_INTEGRATION_CONTRACT.md`](file:///c:/Users/dell/Desktop/SANJIVANI/docs/TEAM_INTEGRATION_CONTRACT.md)

---

## 7. Presentation Confidence Check

- [ ] Remember the tagline: *"Predict the failure. Protect the connection. Save the response time."*
- [ ] Be ready to explain why `RD10` is CRITICAL (delays 42,000 citizens by up to 14.9 minutes!).
- [ ] Be ready to explain why `R3` is the #1 supply priority (single road `RD04` cut-edge).
- [ ] Be proud of achieving **42 passing automated tests with zero errors**!

