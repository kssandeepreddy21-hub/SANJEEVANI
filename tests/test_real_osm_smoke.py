"""Optional smoke tests against the real external Bengaluru OSM data when available."""

import pytest

from sanjeevani.config import osm_data_available
from sanjeevani.decision import find_shortest_safe_route
from sanjeevani.osm_data_loader import load_corridor


@pytest.mark.skipif(not osm_data_available(), reason="External Bengaluru OSM data not configured via RESQ_AI_DATA_DIR")
def test_real_osm_corridor_load_and_route():
    corridor = load_corridor()
    assert corridor.number_of_nodes() > 1000
    assert corridor.number_of_edges() > 1000

    nodes = list(corridor.nodes())[:2]
    res = find_shortest_safe_route(corridor, origin=nodes[0], destination=nodes[1])
    assert "reachable" in res

