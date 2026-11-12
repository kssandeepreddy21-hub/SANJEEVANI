import networkx as nx
from pathlib import Path


def inspect_osm_graph():

    path = Path("data/processed/bengaluru_osm.graphml")

    print("Loading Bengaluru road graph...")

    graph = nx.read_graphml(path)

    print("\n1. ROAD LENGTH CHECK")
    print("-------------------------")

    lengths = [
        float(data["length_m"])
        for _, _, data in graph.edges(data=True)
        if "length_m" in data
    ]

    print("Edges with lengths:", len(lengths))
    print("Minimum road segment length:", round(min(lengths), 2), "m")
    print("Maximum road segment length:", round(max(lengths), 2), "m")

    print("\n2. ROAD CLASSIFICATION")
    print("-------------------------")

    highway_counts = {}

    for _, _, data in graph.edges(data=True):

        highway = data.get("highway", "unknown")

        highway_counts[highway] = (
            highway_counts.get(highway, 0) + 1
        )

    for highway, count in sorted(
        highway_counts.items(),
        key=lambda item: item[1],
        reverse=True
    ):

        print(highway, ":", count)

    print("\n3. SPECIAL ROAD ATTRIBUTES")
    print("-------------------------")

    for tag in ["bridge", "tunnel", "access", "maxspeed"]:

        count = sum(
            1 for _, _, data in graph.edges(data=True)
            if tag in data
        )

        print(tag, "attributes available:", count)


if __name__ == "__main__":
    inspect_osm_graph()