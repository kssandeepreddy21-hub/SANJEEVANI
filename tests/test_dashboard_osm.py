"""Tests for RESQ-AI Stage 3 dashboard OSM views, bounded Folium maps, and AppTest UI."""

from __future__ import annotations

import math
from pathlib import Path

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import pytest
from streamlit.testing.v1 import AppTest

from sanjeevani import config, dashboard_evidence, dashboard_osm, data
from sanjeevani.osm_data_loader import load_dashboard_payload

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_PATH = REPO_ROOT / "app.py"


def _mock_corridor_graph() -> nx.MultiDiGraph:
    """Build a small realistic MultiDiGraph within Central Bengaluru GPS bounds."""
    g = nx.MultiDiGraph()
    nodes = {
        "N1": (12.9716, 77.5946),
        "N2": (12.9750, 77.5980),
        "N3": (12.9790, 77.6010),
        "N4": (12.9825, 77.6040),
        "N5": (12.9760, 77.6045),
    }
    for nid, (lat, lon) in nodes.items():
        g.add_node(nid, x=lon, y=lat)

    edges = [
        ("N1", "N2", "R10", "primary", 550.0, "no", "no"),
        ("N2", "N1", "R10", "primary", 550.0, "no", "no"),
        ("N2", "N3", "R11", "secondary", 620.0, "no", "yes"),  # high-vuln tunnel
        ("N3", "N2", "R11", "secondary", 620.0, "no", "yes"),
        ("N3", "N4", "R12", "primary", 510.0, "no", "no"),
        ("N4", "N3", "R12", "primary", 510.0, "no", "no"),
        ("N2", "N5", "R13", "tertiary", 780.0, "no", "no"),
        ("N5", "N4", "R14", "tertiary", 820.0, "no", "no"),
    ]
    for u, v, rid, hw, length_m, bridge, tunnel in edges:
        g.add_edge(
            u,
            v,
            road_id=rid,
            name=f"Corridor {rid}",
            highway=hw,
            length_m=length_m,
            bridge=bridge,
            tunnel=tunnel,
            oneway="no",
            access="yes",
            emergency="unknown",
        )
    return g


def test_corridor_map_snapshot_schema_size_and_bengaluru_bounds():
    assert dashboard_osm.SNAPSHOT_PATH.exists(), "Corridor map snapshot JSON must exist"
    size_bytes = dashboard_osm.SNAPSHOT_PATH.stat().st_size
    assert 1_000 < size_bytes < 500_000, f"Unexpected snapshot size: {size_bytes} bytes"

    snap = dashboard_osm.load_corridor_snapshot()
    assert snap is not None
    assert snap["metadata"]["arterial_segments_count"] <= dashboard_osm.MAX_ARTERIAL_OVERLAYS
    assert snap["metadata"]["vulnerable_segments_count"] <= dashboard_osm.MAX_VULNERABLE_OVERLAYS
    assert snap["metadata"]["facilities_count"] <= dashboard_osm.MAX_FACILITY_OVERLAYS

    # Verify GPS bounds across all polyline segments & markers
    for seg in snap["arterial_segments"] + snap["vulnerable_segments"]:
        for lat, lon in seg["coords"]:
            assert 12.70 <= lat <= 13.30
            assert 77.30 <= lon <= 77.90
            assert math.isfinite(lat) and math.isfinite(lon)

    for fac in snap["facilities"]:
        assert 12.70 <= fac["lat"] <= 13.30
        assert 77.30 <= fac["lon"] <= 77.90

    assert len(snap["routes"]["primary_coords"]) >= 10
    assert len(snap["routes"]["alternative_coords"]) >= 10
    assert len(snap["phase8_observations"]) >= 1


def test_osm_view_models_and_plotly_figures():
    payload = load_dashboard_payload()
    snap = dashboard_osm.load_corridor_snapshot()

    kpis = dashboard_osm.get_osm_overview_kpis(payload)
    assert len(kpis) == 6
    assert any("437,698" in c["value"] for c in kpis)

    vuln_df = dashboard_osm.get_vulnerability_summary_df(payload, scope="central_corridor")
    assert len(vuln_df) == 4
    assert vuln_df["Unique Road Ways"].sum() == 9521

    top_df = dashboard_osm.get_top_vulnerable_roads_df(snapshot=snap)
    assert not top_df.empty
    assert "Vulnerability Score" in top_df.columns

    prog_df = dashboard_osm.get_corridor_progression_df(payload)
    assert len(prog_df) == 4
    assert prog_df["Blocked Ways"].iloc[-1] == 54

    fac_counts_df = dashboard_osm.get_facility_counts_df(payload)
    fac_imp_df = dashboard_osm.get_facility_impact_df(payload)
    assert len(fac_counts_df) == 4
    assert len(fac_imp_df) == 4

    routes_df = dashboard_osm.get_rescue_routes_df(payload)
    obs_df = dashboard_osm.get_active_observations_df(payload)
    comp_df = dashboard_osm.get_strategy_comparison_df(payload)
    alloc_df, loc_df = dashboard_osm.get_allocations_df(payload)
    assert len(routes_df) == 2
    assert len(obs_df) == 8
    assert len(comp_df) == 3
    assert not alloc_df.empty and len(loc_df) == 6

    figs = [
        dashboard_osm.build_vulnerability_distribution_chart(payload),
        dashboard_osm.build_corridor_rainfall_progression_chart(prog_df),
        dashboard_osm.build_facility_impact_chart(fac_imp_df),
        dashboard_osm.build_osm_strategy_comparison_chart(comp_df),
    ]
    for fig in figs:
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1


def test_folium_bengaluru_map_bounded_and_safe_fallback():
    payload = load_dashboard_payload()
    snap = dashboard_osm.load_corridor_snapshot()
    inc_df = data.get_synthetic_incidents(data.get_scenario_names()[1]).copy()
    # Inject one bad NaN coordinate to ensure graceful filtering
    inc_df.loc[inc_df.index[0], "lat"] = float("nan")

    fmap = dashboard_osm.build_bengaluru_osm_map(payload, snap, incidents_df=inc_df)
    stats = fmap._resq_overlay_stats  # type: ignore[attr-defined]
    total_vectors = sum(stats.values())
    assert stats["arterial_polylines"] <= dashboard_osm.MAX_ARTERIAL_OVERLAYS
    assert stats["vulnerable_polylines"] <= dashboard_osm.MAX_VULNERABLE_OVERLAYS
    assert stats["facility_markers"] <= dashboard_osm.MAX_FACILITY_OVERLAYS + 5
    assert total_vectors < 1000
    html_out = fmap._repr_html_()
    assert "Bengaluru" in html_out or "leaflet" in html_out.lower()

    # Fallback without snapshot still renders hospital marker cleanly
    fmap_no_snap = dashboard_osm.build_bengaluru_osm_map(payload, snapshot=None)
    assert fmap_no_snap._resq_overlay_stats["facility_markers"] >= 1  # type: ignore[attr-defined]


def test_offline_missing_osm_dir_graceful_degradation(monkeypatch, tmp_path):
    empty_dir = tmp_path / "no_osm_here"
    empty_dir.mkdir()
    monkeypatch.setenv(config.ENV_DATA_DIR, str(empty_dir))
    assert config.osm_data_available() is False

    payload = load_dashboard_payload()
    snap = dashboard_osm.load_corridor_snapshot()
    inc_df = data.get_synthetic_incidents(data.get_scenario_names()[1])
    snapped_df, _ = dashboard_osm.snap_emergency_reports_to_corridor(
        inc_df, corridor_graph=None, snapshot=snap
    )
    assert "OSM Dispatch Queue" in snapped_df.columns
    assert not snapped_df.empty
    fmap = dashboard_osm.build_bengaluru_osm_map(payload, snap)
    assert fmap is not None


def test_live_mock_multidigraph_corridor_workflows():
    g = _mock_corridor_graph()

    rain_res = dashboard_osm.run_live_corridor_rainfall(g, current_rainfall=65, increase_per_15_min=10)
    assert len(rain_res["scenarios"]) == 4
    top_df = dashboard_osm.get_top_vulnerable_roads_df(live_graph=rain_res["latest_graph"])
    assert not top_df.empty

    rt_res = dashboard_osm.run_live_corridor_routing(
        g, origin_node="N1", destination_node="N4", rainfall_intensity=85.0
    )
    assert rt_res["primary_route"]["reachable"] is True
    assert rt_res["alternative_route"]["reachable"] is True
    assert len(rt_res["primary_coords"]) >= 2

    # Member 2 report queue: verified vs unverified vs simulated duplicate
    r_ok = dashboard_evidence.score_emergency_report("Flooded Clinic", "Sector 1 – Central Civic Hub", "Medical Evacuation", "CRITICAL", False, 0)
    r_dup = dashboard_evidence.score_emergency_report("Old Photo", "Sector 2 – East Floodplain", "Flash Flood Entrapment", "WARNING", True, 1)
    inc_df = pd.DataFrame([r_ok, r_dup])

    snapped_df, bridged = dashboard_osm.snap_emergency_reports_to_corridor(inc_df, corridor_graph=g)
    assert len(bridged["affected_locations"]) == 1
    assert len(bridged["held_incidents"]) == 1
    assert set(snapped_df["OSM Dispatch Queue"]) == {
        "READY FOR DISPATCH",
        "HELD (Duplicate/recycled evidence warning)",
    }

    alloc_res = dashboard_osm.run_live_corridor_allocation(g, inc_df, strategy="budget_aware_optimized", total_budget=3000.0)
    assert alloc_res["allocation"] is not None
    assert alloc_res["comparison"] is not None
    assert len(alloc_res["comparison"]["comparison_summary"]) == 3


def test_no_hardcoded_user_paths_in_new_stage3_files():
    forbidden = ("C:\\Users\\", "C:/Users/", "HIMASHRI")
    for path in (
        REPO_ROOT / "sanjeevani" / "dashboard_osm.py",
        REPO_ROOT / "scripts" / "build_corridor_map_snapshot.py",
        dashboard_osm.SNAPSHOT_PATH,
    ):
        txt = path.read_text(encoding="utf-8")
        for frag in forbidden:
            assert frag not in txt, f"Hardcoded personal path fragment '{frag}' found in {path}"


def test_streamlit_apptest_both_modes_render_cleanly(monkeypatch):
    monkeypatch.setenv(config.ENV_MODE, "synthetic")
    at = AppTest.from_file(str(APP_PATH), default_timeout=20)
    at.run()
    assert not at.exception

    # Switch to Real Bengaluru OSM Network mode and test multiple tabs
    mode_radio = at.sidebar.radio[0]
    mode_radio.set_value("Real Bengaluru OSM Network").run()
    assert not at.exception

    nav_radio = at.sidebar.radio[1]
    for tab in (
        "2. Infrastructure Resilience & Flood Vulnerability",
        "3. Rainfall Simulation",
        "4. Cascading Failures & Facilities",
        "5. Emergency Intelligence",
        "6. Rescue Route Planning",
        "7. Resource Allocation & Strategy Comparison",
        "8. Benchmark & Audit",
    ):
        nav_radio.set_value(tab).run()
        assert not at.exception, f"Exception on OSM tab '{tab}': {at.exception}"

    # Verify Synthetic Mode tab traversal too
    at.sidebar.radio[0].set_value("Synthetic Prototype Mode").run()
    assert not at.exception
    for tab in (
        "2. Infrastructure Resilience & Flood Vulnerability",
        "3. Rainfall Simulation",
        "4. Cascading Failures & Facilities",
        "5. Emergency Intelligence",
        "6. Rescue Route Planning",
        "7. Resource Allocation & Strategy Comparison",
        "8. Benchmark & Audit",
    ):
        at.sidebar.radio[1].set_value(tab).run()
        assert not at.exception, f"Exception on Synthetic tab '{tab}': {at.exception}"
