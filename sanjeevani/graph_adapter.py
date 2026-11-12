"""NetworkX graph-type adapters supporting both simple Graph and OSM MultiDiGraph."""

from __future__ import annotations

import math
from typing import Any, Iterator

import networkx as nx
import numpy as np

EARTH_RADIUS_M = 6_371_000.0


def iter_edges_with_keys(G: nx.Graph) -> Iterator[tuple[Any, Any, Any, dict[str, Any]]]:
    """Yield `(u, v, key, data)` uniformly for MultiGraphs (`key`) and simple Graphs (`None`)."""
    if G.is_multigraph():
        for u, v, key, data in G.edges(keys=True, data=True):
            yield u, v, key, data
    else:
        for u, v, data in G.edges(data=True):
            yield u, v, None, data


def edge_attrs(
    G: nx.Graph,
    u: Any,
    v: Any,
    key: Any = None,
    weight_attr: str = "length_m",
) -> dict[str, Any] | None:
    """
    Safely return a single edge attribute dict between `(u, v)`.
    On MultiGraphs, returns the matching `key` or selects the best parallel
    edge (preferring passable edges with lowest `weight_attr`).
    """
    if not G.has_edge(u, v):
        return None
    if not G.is_multigraph():
        return G[u][v]

    edge_bundle = G[u][v]
    if key is not None and key in edge_bundle:
        return edge_bundle[key]

    best_data = None
    best_rank = None
    for edge_data in edge_bundle.values():
        is_blocked = (
            edge_data.get("available") is False
            or edge_data.get("condition") == "BLOCKED"
            or edge_data.get("failed") is True
        )
        weight = edge_data.get(weight_attr)
        numeric_w = float(weight) if isinstance(weight, (int, float)) else 1e12
        rank = (1 if is_blocked else 0, numeric_w)
        if best_rank is None or rank < best_rank:
            best_rank = rank
            best_data = edge_data
    return best_data


def edges_for_road_id(G: nx.Graph, road_id: str | int) -> list[tuple[Any, Any, Any]]:
    """Return every `(u, v, key)` tuple belonging to `road_id` across all directions."""
    target = str(road_id)
    matches: list[tuple[Any, Any, Any]] = []
    for u, v, key, data in iter_edges_with_keys(G):
        if str(data.get("road_id", "")) == target:
            matches.append((u, v, key))
    return matches


def remove_road(
    G: nx.Graph,
    road_id: str | int,
    inplace: bool = False,
) -> nx.Graph:
    """
    Remove all directed/parallel edge segments sharing `road_id`.
    Does not mutate `G` unless `inplace=True`.
    """
    target_graph = G if inplace else G.copy()
    for u, v, key in edges_for_road_id(target_graph, road_id):
        if target_graph.is_multigraph():
            target_graph.remove_edge(u, v, key=key)
        else:
            target_graph.remove_edge(u, v)
    return target_graph


def weak_component_summary(G: nx.Graph) -> dict[str, Any]:
    """Safely summarize connected components for both directed and undirected graphs."""
    n_nodes = G.number_of_nodes()
    if n_nodes == 0:
        return {
            "num_components": 0,
            "is_connected": False,
            "largest_component_size": 0,
            "largest_component_pct": 0.0,
        }

    comp_iter = (
        nx.weakly_connected_components(G)
        if G.is_directed()
        else nx.connected_components(G)
    )
    sizes = [len(c) for c in comp_iter]
    largest = max(sizes) if sizes else 0
    num_comps = len(sizes)
    return {
        "num_components": num_comps,
        "is_connected": num_comps == 1,
        "largest_component_size": largest,
        "largest_component_pct": round((largest / n_nodes) * 100.0, 2),
    }


def to_undirected_simple(
    G: nx.Graph,
    weight_attr: str = "length_m",
    only_passable: bool = False,
) -> nx.Graph:
    """
    Collapse a directed/multi graph (intended for corridor subgraphs) into a
    simple undirected `nx.Graph` by keeping the lowest-weight edge per `(u, v)`.
    Useful for undirected algorithms such as `nx.bridges()` without failing on
    MultiDiGraph inputs.
    """
    simple = nx.Graph()
    for node_id, ndata in G.nodes(data=True):
        simple.add_node(node_id, **ndata)

    for u, v, _key, data in iter_edges_with_keys(G):
        if u == v:
            continue
        is_blocked = (
            data.get("available") is False
            or data.get("condition") == "BLOCKED"
            or data.get("failed") is True
        )
        if only_passable and is_blocked:
            continue
        raw_w = data.get(weight_attr)
        weight_val = float(raw_w) if isinstance(raw_w, (int, float)) else 1.0
        if simple.has_edge(u, v):
            existing_w = simple[u][v].get(weight_attr, float("inf"))
            if isinstance(existing_w, (int, float)) and weight_val >= float(existing_w):
                continue
        attrs = dict(data)
        attrs[weight_attr] = weight_val
        simple.add_edge(u, v, **attrs)

    return simple


def nearest_node(G: nx.Graph, lat: float, lon: float) -> tuple[Any | None, float | None]:
    """
    Find the graph node closest to `(lat, lon)` using vectorized NumPy haversine
    distance over `y`/`lat` and `x`/`lon` node attributes.
    """
    if lat is None or lon is None or not (math.isfinite(float(lat)) and math.isfinite(float(lon))):
        return None, None

    node_ids: list[Any] = []
    lats: list[float] = []
    lons: list[float] = []

    for node_id, ndata in G.nodes(data=True):
        n_lat = ndata.get("y", ndata.get("lat"))
        n_lon = ndata.get("x", ndata.get("lon"))
        if n_lat is None or n_lon is None:
            continue
        try:
            lats.append(float(n_lat))
            lons.append(float(n_lon))
            node_ids.append(node_id)
        except (TypeError, ValueError):
            continue

    if not node_ids:
        return None, None

    lat_arr = np.radians(np.asarray(lats, dtype=np.float64))
    lon_arr = np.radians(np.asarray(lons, dtype=np.float64))
    lat0 = math.radians(float(lat))
    lon0 = math.radians(float(lon))

    dlat = lat_arr - lat0
    dlon = lon_arr - lon0
    a = np.sin(dlat / 2.0) ** 2 + math.cos(lat0) * np.cos(lat_arr) * (np.sin(dlon / 2.0) ** 2)
    distances_m = 2.0 * EARTH_RADIUS_M * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))

    best_idx = int(np.argmin(distances_m))
    return node_ids[best_idx], round(float(distances_m[best_idx]), 2)
