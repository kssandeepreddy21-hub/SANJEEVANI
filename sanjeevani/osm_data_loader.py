"""Cached loaders for the precomputed Member 3 payload and external Bengaluru OSM graph."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import networkx as nx

from sanjeevani.config import (
    ENV_DATA_DIR,
    get_cache_path,
    get_graph_path,
    get_payload_path,
    osm_data_available,
)
from sanjeevani.twin_member3 import extract_corridor_subgraph
from sanjeevani.validate_osm_graph import load_or_cache_osm_graph

DEFAULT_CORRIDOR_BBOX: tuple[float, float, float, float] = (
    77.565,
    12.955,
    77.625,
    13.005,
)


class OSMDataUnavailableError(FileNotFoundError):
    """Raised when Real Bengaluru OSM data files are not available locally."""


@lru_cache(maxsize=4)
def _load_payload_cached(path_str: str) -> dict[str, Any]:
    with open(path_str, "r", encoding="utf-8") as f:
        return json.load(f)


def load_dashboard_payload(path: Path | str | None = None, use_cache: bool = True) -> dict[str, Any]:
    """
    Load the lightweight Member 3 JSON payload (~46 KB).
    Reads directly from disk without loading the 940 MB GraphML file.
    """
    target = Path(path) if path is not None else get_payload_path()
    if not target.exists():
        raise OSMDataUnavailableError(
            f"Dashboard payload JSON not found: {target}"
        )
    resolved = str(target.resolve())
    if not use_cache:
        with open(resolved, "r", encoding="utf-8") as f:
            return json.load(f)
    return _load_payload_cached(resolved)


@lru_cache(maxsize=1)
def _load_full_graph_cached(graph_str: str, cache_str: str) -> nx.MultiDiGraph:
    return load_or_cache_osm_graph(
        graph_file=Path(graph_str),
        cache_file=Path(cache_str),
        use_cache=True,
    )


def load_full_graph() -> nx.MultiDiGraph:
    """
    Load the full Bengaluru OSM MultiDiGraph once per process from cache/GraphML.
    Raises `OSMDataUnavailableError` with instructions when data files are absent.
    """
    if not osm_data_available():
        graph_p = get_graph_path()
        cache_p = get_cache_path()
        raise OSMDataUnavailableError(
            "Real Bengaluru OSM graph/cache not found. "
            f"Checked '{graph_p}' and '{cache_p}'. "
            f"Set environment variable {ENV_DATA_DIR} to the directory containing "
            "processed/bengaluru_osm.graphml or processed/bengaluru_osm_cached.pkl."
        )
    return _load_full_graph_cached(str(get_graph_path()), str(get_cache_path()))


@lru_cache(maxsize=4)
def _load_corridor_cached(
    bbox: tuple[float, float, float, float],
    graph_str: str,
    cache_str: str,
) -> nx.MultiDiGraph:
    full_g = _load_full_graph_cached(graph_str, cache_str)
    return extract_corridor_subgraph(full_g, *bbox)


def load_corridor(
    bbox: tuple[float, float, float, float] = DEFAULT_CORRIDOR_BBOX,
) -> nx.MultiDiGraph:
    """
    Return a cached geographic corridor subgraph (copy) from the full Bengaluru OSM graph.
    """
    if len(bbox) != 4:
        raise ValueError("bbox must be a 4-tuple: (min_lon, min_lat, max_lon, max_lat).")
    if not osm_data_available():
        graph_p = get_graph_path()
        cache_p = get_cache_path()
        raise OSMDataUnavailableError(
            "Cannot extract corridor subgraph because Real Bengaluru OSM data is unavailable. "
            f"Checked '{graph_p}' and '{cache_p}'. Set {ENV_DATA_DIR} to locate external data."
        )
    norm_bbox = tuple(float(c) for c in bbox)
    return _load_corridor_cached(
        norm_bbox,  # type: ignore[arg-type]
        str(get_graph_path()),
        str(get_cache_path()),
    )


def clear_loader_caches() -> None:
    """Clear in-process caches for payload, full graph, and corridor subgraphs."""
    _load_payload_cached.cache_clear()
    _load_full_graph_cached.cache_clear()
    _load_corridor_cached.cache_clear()

