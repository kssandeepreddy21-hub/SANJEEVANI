import networkx as nx
from pathlib import Path


def validate_graph():

    path = Path("data/processed/bengaluru_roads.graphml")

    print("Loading Bengaluru road graph...")

    graph = nx.read_graphml(path)

    print("\nGRAPH SUMMARY")
    print("-------------------------")

    print("Nodes:", graph.number_of_nodes())
    print("Edges:", graph.number_of_edges())

    print("\nCONNECTIVITY CHECK")
    print("-------------------------")

    undirected = graph.to_undirected()

    components = list(nx.connected_components(undirected))

    print("Connected components:", len(components))

    largest = max(components, key=len)

    print("Largest component nodes:", len(largest))

    percentage = (
        len(largest) / graph.number_of_nodes()
    ) * 100

    print("Largest component coverage:", round(percentage, 2), "%")


if __name__ == "__main__":
    validate_graph()