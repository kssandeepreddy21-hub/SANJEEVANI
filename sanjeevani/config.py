"""Central configuration and path resolution for RESQ-AI."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
LOCAL_DATA_DIR: Path = REPO_ROOT / "data"

GRAPH_FILENAME = "bengaluru_osm.graphml"
CACHE_FILENAME = "bengaluru_osm_cached.pkl"
PBF_FILENAME = "planet_77.46_12.907_d3d9fd17.osm.pbf"
PAYLOAD_FILENAME = "member3_dashboard_payload.json"

ENV_DATA_DIR = "RESQ_AI_DATA_DIR"
ENV_MODE = "RESQ_AI_MODE"
VALID_MODES = ("synthetic", "osm")


def get_data_dir() -> Path:
    """
    Return the root directory for external Bengaluru OSM data.
    Uses the `RESQ_AI_DATA_DIR` environment variable when set; otherwise
    falls back to the repository-local `data/` folder.
    """
    raw = os.environ.get(ENV_DATA_DIR, "").strip()
    if raw:
        return Path(raw).expanduser()
    return LOCAL_DATA_DIR


def _resolve_data_file(subdir: str, filename: str) -> Path:
    base = get_data_dir()
    nested = base / subdir / filename
    if nested.exists():
        return nested
    flat = base / filename
    if flat.exists():
        return flat
    return nested


def get_graph_path() -> Path:
    """Return the configured path to `bengaluru_osm.graphml`."""
    return _resolve_data_file("processed", GRAPH_FILENAME)


def get_cache_path() -> Path:
    """Return the configured path to `bengaluru_osm_cached.pkl`."""
    return _resolve_data_file("processed", CACHE_FILENAME)


def get_pbf_path() -> Path:
    """Return the configured path to the Bengaluru `.osm.pbf` extract."""
    return _resolve_data_file("raw", PBF_FILENAME)


def get_payload_path() -> Path:
    """Return the path to the repo-local Member 3 dashboard JSON payload."""
    local_payload = LOCAL_DATA_DIR / "processed" / PAYLOAD_FILENAME
    if local_payload.exists():
        return local_payload
    return _resolve_data_file("processed", PAYLOAD_FILENAME)


def get_mode() -> str:
    """
    Return active backend mode: `'synthetic'` (default) or `'osm'`.
    Reads `RESQ_AI_MODE` environment variable.
    """
    raw = os.environ.get(ENV_MODE, "synthetic").strip().lower()
    if raw in ("osm", "real", "bengaluru"):
        return "osm"
    return "synthetic"


def osm_data_available() -> bool:
    """Return True if either the OSM GraphML or binary pickle cache exists."""
    return get_graph_path().exists() or get_cache_path().exists()

