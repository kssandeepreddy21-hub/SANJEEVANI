"""Tests for `sanjeevani.osm_data_loader` payload validation and graceful fallback."""

import pytest

from sanjeevani.osm_data_loader import (
    OSMDataUnavailableError,
    clear_loader_caches,
    load_corridor,
    load_dashboard_payload,
    load_full_graph,
)

EXPECTED_PHASE_KEYS = {
    "phase1_network_validation",
    "phase2_vulnerability",
    "phase3_rainfall_simulation",
    "phase4_cascading_and_facilities",
    "phase5_rescue_routing",
    "phase6_resource_allocation",
    "phase7_strategy_comparison",
    "phase8_active_observation_plan",
}


def test_payload_contains_all_eight_phases_and_metadata():
    payload = load_dashboard_payload()
    assert "metadata" in payload
    assert EXPECTED_PHASE_KEYS.issubset(payload.keys())
    assert payload["phase1_network_validation"]["validation_status"] == "PASS"


def test_payload_size_under_100kb():
    from sanjeevani.config import get_payload_path

    p = get_payload_path()
    assert p.exists()
    assert p.stat().st_size < 100 * 1024


def test_payload_contains_no_graph_objects():
    payload = load_dashboard_payload()
    assert "updated_graph" not in str(payload)
    assert "MultiDiGraph" not in str(payload.get("phase5_rescue_routing", {}))


def test_missing_graph_raises_clear_error(monkeypatch, tmp_path):
    clear_loader_caches()
    empty_dir = tmp_path / "no_osm_here"
    empty_dir.mkdir()
    monkeypatch.setenv("RESQ_AI_DATA_DIR", str(empty_dir))

    with pytest.raises(OSMDataUnavailableError) as exc_info:
        load_full_graph()
    assert "RESQ_AI_DATA_DIR" in str(exc_info.value)


def test_missing_corridor_raises_clear_error(monkeypatch, tmp_path):
    clear_loader_caches()
    empty_dir = tmp_path / "no_osm_here_either"
    empty_dir.mkdir()
    monkeypatch.setenv("RESQ_AI_DATA_DIR", str(empty_dir))

    with pytest.raises(OSMDataUnavailableError) as exc_info:
        load_corridor()
    assert "RESQ_AI_DATA_DIR" in str(exc_info.value)

