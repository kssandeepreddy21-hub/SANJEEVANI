
import osmium
import networkx as nx
import json

from pathlib import Path
from pyproj import Geod


# --------------------------------------------------
# FILE PATHS
# --------------------------------------------------

PBF_FILE = Path(
    "data/raw/planet_77.46_12.907_d3d9fd17.osm.pbf"
)

OUTPUT_FILE = Path(
    "data/processed/bengaluru_osm.graphml"
)


# --------------------------------------------------
# DRIVABLE ROAD TYPES
# --------------------------------------------------

DRIVABLE_ROADS = {
    "motorway",
    "motorway_link",
    "trunk",
    "trunk_link",
    "primary",
    "primary_link",
    "secondary",
    "secondary_link",
    "tertiary",
    "tertiary_link",
    "residential",
    "living_street",
    "unclassified",
    "road",
    "service"
}


# --------------------------------------------------
# ONE-WAY DIRECTION DETECTION
# --------------------------------------------------

def get_road_direction(tags):

    oneway = tags.get("oneway", "").lower()

    highway = tags.get("highway", "")

    junction = tags.get("junction", "")

    if oneway in ("yes", "true", "1"):

        return "forward"

    elif oneway == "-1":

        return "reverse"

    elif oneway in ("no", "false", "0"):

        return "both"

    elif oneway in ("reversible", "alternating"):

        return "conditional"

    elif highway in ("motorway", "motorway_link"):

        return "forward"

    elif junction in ("roundabout", "circular"):

        return "forward"

    else:

        return "both"


# --------------------------------------------------
# ROAD EXTRACTOR
# --------------------------------------------------

class RoadExtractor(osmium.SimpleHandler):

    def __init__(self):

        super().__init__()

        self.graph = nx.MultiDiGraph()

        self.geod = Geod(ellps="WGS84")

        self.road_count = 0

        self.skipped_count = 0

        self.short_segment_count = 0

        self.direction_counts = {
            "forward": 0,
            "reverse": 0,
            "both": 0,
            "conditional": 0
        }

        self.highway_counts = {}

        self.bridge_count = 0

        self.tunnel_count = 0

        self.restricted_count = 0

    # --------------------------------------------------
    # PROCESS EACH OSM ROAD WAY
    # --------------------------------------------------

    def way(self, way):

        tags = way.tags

        highway = tags.get("highway")

        if highway not in DRIVABLE_ROADS:

            return

        # Preserve all original OSM tags.

        original_tags = {
            tag.k: tag.v
            for tag in tags
        }

        # Extract road nodes.

        node_list = []

        valid_way = True

        for node in way.nodes:

            if not node.location.valid():

                valid_way = False

                break

            node_id = str(node.ref)

            longitude = float(node.location.lon)

            latitude = float(node.location.lat)

            node_list.append(
                (
                    node_id,
                    longitude,
                    latitude
                )
            )

        # Do not connect across missing node locations.

        if not valid_way or len(node_list) < 2:

            self.skipped_count += 1

            return

        # Determine road direction.

        direction = get_road_direction(tags)

        road_id = str(way.id)

        road_name = tags.get("name", "")

        # --------------------------------------------------
        # ROAD ATTRIBUTES
        # --------------------------------------------------

        attributes = {

            "road_id": road_id,

            "name": road_name,

            "highway": highway,

            "oneway": direction,

            "oneway_raw": tags.get(
                "oneway",
                "not_specified"
            ),

            "length_m": 0.0,

            "bridge": tags.get("bridge", "no"),

            "tunnel": tags.get("tunnel", "no"),

            "access": tags.get("access", "unknown"),

            "vehicle": tags.get("vehicle", "unknown"),

            "motor_vehicle": tags.get(
                "motor_vehicle",
                "unknown"
            ),

            "emergency": tags.get(
                "emergency",
                "unknown"
            ),

            "maxspeed": tags.get("maxspeed", "unknown"),

            "surface": tags.get("surface", "unknown"),

            "lanes": tags.get("lanes", "unknown"),

            "junction": tags.get("junction", "unknown"),

            "layer": tags.get("layer", "0"),

            "lit": tags.get("lit", "unknown"),

            "smoothness": tags.get(
                "smoothness",
                "unknown"
            ),

            "width": tags.get("width", "unknown"),

            "toll": tags.get("toll", "unknown"),

            "ford": tags.get("ford", "no"),

            "osm_tags": json.dumps(
                original_tags,
                ensure_ascii=False
            )
        }

        # --------------------------------------------------
        # UPDATE STATISTICS
        # --------------------------------------------------

        self.road_count += 1

        self.highway_counts[highway] = (
            self.highway_counts.get(highway, 0) + 1
        )

        self.direction_counts[direction] += 1

        if tags.get("bridge", "no") not in ("no", ""):

            self.bridge_count += 1

        if tags.get("tunnel", "no") not in ("no", ""):

            self.tunnel_count += 1

        if any(
            tags.get(key, "") in ("private", "no")
            for key in ("access", "vehicle", "motor_vehicle")
        ):

            self.restricted_count += 1

        # --------------------------------------------------
        # ADD NODES AND ROAD SEGMENTS
        # --------------------------------------------------

        for index in range(len(node_list)):

            node_id, longitude, latitude = node_list[index]

            self.graph.add_node(

                node_id,

                x=longitude,

                y=latitude

            )

        for index in range(len(node_list) - 1):

            start_id, start_lon, start_lat = node_list[index]

            end_id, end_lon, end_lat = node_list[index + 1]

            if start_id == end_id:

                continue

            # Calculate geodesic segment length.

            _, _, length = self.geod.inv(

                start_lon,
                start_lat,

                end_lon,
                end_lat

            )

            length = float(length)

            if length < 0.05:

                self.short_segment_count += 1

            edge_attributes = attributes.copy()

            edge_attributes["length_m"] = length

            # Forward direction.

            if direction == "forward":

                self.graph.add_edge(

                    start_id,
                    end_id,

                    **edge_attributes

                )

            # Reverse direction.

            elif direction == "reverse":

                self.graph.add_edge(

                    end_id,
                    start_id,

                    **edge_attributes

                )

            # Conditional direction:
            # Both candidate directions are retained,
            # but must not be treated as automatically safe.

            elif direction == "conditional":

                self.graph.add_edge(

                    start_id,
                    end_id,

                    **edge_attributes

                )

                self.graph.add_edge(

                    end_id,
                    start_id,

                    **edge_attributes

                )

            # Bidirectional road.

            else:

                self.graph.add_edge(

                    start_id,
                    end_id,

                    **edge_attributes

                )

                self.graph.add_edge(

                    end_id,
                    start_id,

                    **edge_attributes

                )


# --------------------------------------------------
# BUILD COMPLETE BENGALURU ROAD GRAPH
# --------------------------------------------------

def build_osm_graph():

    if not PBF_FILE.exists():

        raise FileNotFoundError(

            f"PBF file not found: {PBF_FILE}"

        )

    print("Reading original OpenStreetMap PBF data...")

    print("This may take a few minutes.")

    extractor = RoadExtractor()

    extractor.apply_file(

        str(PBF_FILE),

        locations=True

    )

    graph = extractor.graph

    # --------------------------------------------------
    # EXTRACTION REPORT
    # --------------------------------------------------

    print("\nROAD EXTRACTION COMPLETED")

    print("--------------------------------")

    print(
        "Road ways processed:",
        extractor.road_count
    )

    print(
        "Road ways skipped:",
        extractor.skipped_count
    )

    print(
        "Graph nodes:",
        graph.number_of_nodes()
    )

    print(
        "Directed edges:",
        graph.number_of_edges()
    )

    print("\nROAD DIRECTIONS")

    print("--------------------------------")

    for direction, count in extractor.direction_counts.items():

        print(direction, ":", count)

    print("\nROAD CLASSIFICATIONS")

    print("--------------------------------")

    for highway, count in sorted(
        extractor.highway_counts.items(),
        key=lambda item: item[1],
        reverse=True
    ):

        print(highway, ":", count)

    print("\nSPECIAL ROAD ATTRIBUTES")

    print("--------------------------------")

    print("Roads tagged as bridges:", extractor.bridge_count)

    print("Roads tagged as tunnels:", extractor.tunnel_count)

    print(
        "Roads with explicit restrictive access tags:",
        extractor.restricted_count
    )

    print(
        "Very short road segments (< 0.05 m):",
        extractor.short_segment_count
    )

    # --------------------------------------------------
    # SAVE GRAPH
    # --------------------------------------------------

    OUTPUT_FILE.parent.mkdir(

        parents=True,

        exist_ok=True

    )

    print("\nSaving road graph...")

    nx.write_graphml(

        graph,

        OUTPUT_FILE

    )

    print("\nSUCCESS!")

    print("Graph saved at:", OUTPUT_FILE)


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":

    build_osm_graph()
