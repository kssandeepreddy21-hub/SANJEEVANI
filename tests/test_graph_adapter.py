"""Unit tests for MultiDiGraph-safe helpers in `sanjeevani.graph_adapter`."""

import networkx as nx

from sanjeevani.graph_adapter import (
    edge_attrs,
    edges_for_road_id,
    iter_edges_with_keys,
    nearest_node,
    remove_road,
    to_undirected_simple,
    weak_component_summary,
)


def _sample_multidigraph():
    G = nx.MultiDiGraph()
    G.add_node("A", x=77.5900, y=12.9700)
    G.add_node("B", x=77.5950, y=12.9700)
    G.add_node("C", x=77.6000, y=12.9750)
    G.add_node("ISLAND", x=77.6100, y=12.9800)

    # Parallel edges between A and B: key 0 blocked (short), key 1 available (longer)
    G.add_edge("A", "B", road_id="R-MAIN", length_m=100.0, available=False, condition="BLOCKED")
    G.add_edge("A", "B", road_id="R-ALT", length_m=250.0, available=True, condition="OPEN")
    # Road R-MAIN continues B->C and opposite C->B (multi-segment bidirectional road_id)
    G.add_edge("B", "C", road_id="R-MAIN", length_m=150.0, available=True, condition="OPEN")
    G.add_edge("C", "B", road_id="R-MAIN", length_m=150.0, available=True, condition="OPEN")
    return G


def test_iter_edges_with_keys_supports_simple_and_multi():
    mg = _sample_multidigraph()
    sg = nx.Graph()
    sg.add_edge("X", "Y", road_id="S1", length_m=50.0)

    mg_items = list(iter_edges_with_keys(mg))
    sg_items = list(iter_edges_with_keys(sg))

    assert len(mg_items) == 4
    assert all(item[2] is not None for item in mg_items)
    assert len(sg_items) == 1
    assert sg_items[0][2] is None


def test_edge_attrs_selects_best_available_parallel_edge():
    mg = _sample_multidigraph()
    best = edge_attrs(mg, "A", "B")
    assert best is not None
    assert best["road_id"] == "R-ALT"
    assert edge_attrs(mg, "A", "B", key=0)["road_id"] == "R-MAIN"
    assert edge_attrs(mg, "ISLAND", "A") is None


def test_edge_attrs_on_simple_graph():
    sg = nx.Graph()
    sg.add_edge("U", "V", road_id="RD-1", length_m=300.0)
    assert edge_attrs(sg, "U", "V")["road_id"] == "RD-1"


def test_remove_road_removes_all_segments_and_preserves_original():
    mg = _sample_multidigraph()
    orig_edges = mg.number_of_edges()

    matches = edges_for_road_id(mg, "R-MAIN")
    assert len(matches) == 3

    updated = remove_road(mg, "R-MAIN", inplace=False)
    assert mg.number_of_edges() == orig_edges  # Non-mutating
    assert updated.number_of_edges() == 1
    assert edges_for_road_id(updated, "R-MAIN") == []
    assert updated.has_edge("A", "B")  # R-ALT stays open


def test_weak_component_summary_handles_directed_and_undirected():
    mg = _sample_multidigraph()
    summary = weak_component_summary(mg)
    assert summary["num_components"] == 2
    assert summary["is_connected"] is False
    assert summary["largest_component_size"] == 3
    assert summary["largest_component_pct"] == 75.0

    sg = nx.Graph()
    sg.add_edge(1, 2)
    sg.add_edge(2, 3)
    assert weak_component_summary(sg)["is_connected"] is True


def test_to_undirected_simple_collapses_parallel_and_skips_blocked():
    mg = _sample_multidigraph()
    simple_all = to_undirected_simple(mg, weight_attr="length_m", only_passable=False)
    assert isinstance(simple_all, nx.Graph)
    assert not simple_all.is_multigraph()
    assert simple_all["A"]["B"]["road_id"] == "R-MAIN"  # shorter 100m kept when all allowed

    simple_pass = to_undirected_simple(mg, weight_attr="length_m", only_passable=True)
    assert simple_pass["A"]["B"]["road_id"] == "R-ALT"  # blocked 100m skipped
    assert list(nx.bridges(simple_pass))  # nx.bridges works cleanly on collapsed simple graph


def test_nearest_node_vectorized_haversine():
    mg = _sample_multidigraph()
    nid, dist_m = nearest_node(mg, lat=12.9751, lon=77.6001)
    assert nid == "C"
    assert dist_m is not None and dist_m < 30.0


def test_nearest_node_handles_empty_graph():
    empty = nx.MultiDiGraph()
    nid, dist_m = nearest_node(empty, lat=12.97, lon=77.59)
    assert nid is None
    assert dist_m is None

