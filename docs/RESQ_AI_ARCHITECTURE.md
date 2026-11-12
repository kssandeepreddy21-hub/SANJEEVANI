# RESQ-AI Backend Architecture & Configuration Guide

## Two Operating Modes

RESQ-AI preserves the existing 16-node/6-node **Synthetic Prototype Mode** while integrating Member 3's **Real Bengaluru OSM Mode** (`437,698` nodes, `921,188` directed edges) through clean adapter and configuration boundaries.

| Mode | Environment Setting | Graph Source | Primary Use Case |
| :--- | :--- | :--- | :--- |
| **Synthetic Prototype Mode** (Default) | `RESQ_AI_MODE=synthetic` | In-memory `nx.Graph` (`data.py`, `sanjeevani/data.py`) | Zero-dependency demos, Member 1 static resilience pipeline, 6-section prototype EOC |
| **Real Bengaluru OSM Mode** | `RESQ_AI_MODE=osm` | Repo-local `member3_dashboard_payload.json` + optional external `RESQ_AI_DATA_DIR` OSM cache | Real Bengaluru road vulnerability, rainfall horizons, facility impact, A*/Dijkstra rescue routing, resource optimization |

## External OSM Data Setup (`RESQ_AI_DATA_DIR`)

The large OpenStreetMap files (`bengaluru_osm.graphml` ~940 MB, `bengaluru_osm_cached.pkl` ~304 MB, `planet_77.46_12.907_d3d9fd17.osm.pbf` ~40 MB) are excluded by `.gitignore` and stored outside the Git repository.

Set `RESQ_AI_DATA_DIR` to the folder containing `processed/` and `raw/`:

```powershell
$env:RESQ_AI_DATA_DIR = "D:\path\to\bengaluru_data"
```

When `RESQ_AI_DATA_DIR` is unset, `sanjeevani/config.py` resolves paths relative to the repository-local `data/` folder. The 46.6 KB precomputed payload at `data/processed/member3_dashboard_payload.json` works immediately without requiring external files.

## Integrated Backend Modules

- **`sanjeevani/config.py`**: Resolves `RESQ_AI_DATA_DIR`, `RESQ_AI_MODE`, and file paths with zero hardcoded personal directories.
- **`sanjeevani/graph_adapter.py`**: MultiDiGraph-safe edge iteration, `edge_attrs`, multi-segment `remove_road`, directed `weak_component_summary`, corridor collapse `to_undirected_simple`, and vectorized NumPy haversine `nearest_node`.
- **`sanjeevani/osm_data_loader.py`**: Process-cached loaders for the lightweight JSON payload (`load_dashboard_payload`), full graph (`load_full_graph`), and geographic corridor subgraphs (`load_corridor`).
- **`sanjeevani/incident_bridge.py`**: Snaps Member 2 emergency reports (`sanjeevani/evidence.py`) to nearest OSM nodes, holds unverified or duplicate-flagged reports, and emits `affected_locations` for `allocate_emergency_resources` / `compare_rescue_strategies`.
- **`sanjeevani/twin.py` & `sanjeevani/decision.py`**: Preserve every original synthetic prototype function while additively exposing Member 3's real-OSM functions (`twin_member3.py`, `decision_member3.py`).

