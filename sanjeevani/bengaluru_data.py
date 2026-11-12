import osmnx as ox
from pathlib import Path


def download_bengaluru_roads():

    print("Connecting to OpenStreetMap...")

    # Use an alternative Overpass server
    ox.settings.overpass_url = "https://overpass.kumi.systems/api"

    # Increase timeout to 300 seconds
    ox.settings.requests_timeout = 300

    print("Downloading Bengaluru road network...")
    
    graph = ox.graph_from_place(
        "Bengaluru, Karnataka, India",
        network_type="drive",
        simplify=True
    )

    print("\nDownload completed!")

    print("Number of intersections:", len(graph.nodes))
    print("Number of road segments:", len(graph.edges))

    data_folder = Path("data")
    data_folder.mkdir(exist_ok=True)

    file_path = data_folder / "bengaluru_roads.graphml"

    ox.save_graphml(graph, filepath=file_path)

    print("\nRoad network saved at:", file_path)

    return graph


if __name__ == "__main__":
    download_bengaluru_roads()
