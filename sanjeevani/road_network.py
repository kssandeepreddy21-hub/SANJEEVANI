import geopandas as gpd
import networkx as nx
import ast
import re
from pathlib import Path
from pyproj import Geod


def parse_oneway(tags):
    """
    Safely read one-way information from OpenStreetMap tags.
    """

    if not isinstance(tags, str) or not tags.strip():
        return "unknown"

    match = re.search(
        r'"oneway"\s*=>\s*"([^"]+)"',
        tags
    )

    if not match:
        return "unknown"

    value = match.group(1).lower()

    if value in ("yes", "true", "1"):
        return "yes"

    if value == "-1":
        return "reverse"

    if value in ("no", "false", "0"):
        return "no"

    return "unknown"



def build_road_graph():

    print("Loading extracted Bengaluru roads...")

    path = Path("data/processed/bengaluru_roads.gpkg")
    roads = gpd.read_file(path, layer="roads")

    geod = Geod(ellps="WGS84")

    graph = nx.MultiDiGraph()
    graph.graph["crs"] = "EPSG:4326"

    for _, road in roads.iterrows():

        geometry = road.geometry

        if geometry is None or geometry.is_empty:
            continue

        coordinates = list(geometry.coords)

        if len(coordinates) < 2:
            continue

        start = tuple(coordinates[0])
        end = tuple(coordinates[-1])

        if start == end:
            continue

        _, _, length = geod.inv(
            start[0], start[1],
            end[0], end[1]
        )

        tags = road.get("other_tags")
        direction = parse_oneway(tags)

        attributes = {
            "osm_id": str(road.get("osm_id")),
            "name": road.get("name"),
            "highway": road.get("highway"),
            "length_m": float(length),
            "geometry": geometry.wkt,
            "oneway": direction
        }

        graph.add_node(start, x=start[0], y=start[1])
        graph.add_node(end, x=end[0], y=end[1])

        if direction == "yes":
            graph.add_edge(start, end, **attributes)

        elif direction == "reverse":
            graph.add_edge(end, start, **attributes)

        else:
            graph.add_edge(start, end, **attributes)
            graph.add_edge(end, start, **attributes)

    print("\nPreliminary graph created!")

    print("Nodes:", graph.number_of_nodes())
    print("Directed edges:", graph.number_of_edges())

    output = Path("data/processed/bengaluru_roads.graphml")

    nx.write_graphml(graph, output)

    print("Graph saved at:", output)

    return graph


if __name__ == "__main__":
    build_road_graph()
