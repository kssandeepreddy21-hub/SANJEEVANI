import json
import pickle
import sys
import xml.parsers.expat
import networkx as nx

from pathlib import Path
from collections import Counter


from sanjeevani.config import get_cache_path, get_graph_path


# --------------------------------------------------
# FILE PATHS
# --------------------------------------------------

GRAPH_FILE = get_graph_path()
CACHE_FILE = get_cache_path()


# --------------------------------------------------
# HELPER: STREAMING GRAPHML LOADER (LOW MEMORY)
# --------------------------------------------------

def load_graphml_streaming(file_path):
    """
    Stream-parse a large GraphML file into a NetworkX MultiDiGraph
    using Python's C-accelerated expat parser without building a
    multi-gigabyte XML DOM tree in memory.
    """

    graph = nx.MultiDiGraph()
    intern = sys.intern

    key_name = {}
    key_type = {}
    key_for = {}

    current_target = None  # "node" or "edge"
    current_node_id = None
    current_edge_src = None
    current_edge_dst = None
    current_edge_key = None
    current_attrs = {}
    current_data_key = None
    char_buffer = []

    def start_element(name, attrs):
        nonlocal current_target, current_node_id
        nonlocal current_edge_src, current_edge_dst, current_edge_key
        nonlocal current_attrs, current_data_key, char_buffer

        if name == "data":
            current_data_key = attrs.get("key")
            char_buffer = []
        elif name == "edge":
            current_target = "edge"
            current_edge_src = intern(attrs["source"])
            current_edge_dst = intern(attrs["target"])
            raw_id = attrs.get("id")
            current_edge_key = (
                int(raw_id)
                if raw_id is not None and raw_id.isdigit()
                else raw_id
            )
            current_attrs = {}
        elif name == "node":
            current_target = "node"
            current_node_id = intern(attrs["id"])
            current_attrs = {}
        elif name == "key":
            kid = attrs["id"]
            key_name[kid] = intern(attrs["attr.name"])
            key_type[kid] = attrs.get("attr.type", "string")
            key_for[kid] = attrs.get("for", "all")

    def char_data(data):
        if current_data_key is not None:
            char_buffer.append(data)

    def end_element(name):
        nonlocal current_target, current_node_id
        nonlocal current_edge_src, current_edge_dst, current_edge_key
        nonlocal current_attrs, current_data_key

        if name == "data" and current_data_key is not None:
            raw_val = "".join(char_buffer)
            attr_name = key_name.get(current_data_key, current_data_key)
            attr_type = key_type.get(current_data_key, "string")

            if attr_type in ("double", "float"):
                try:
                    val = float(raw_val)
                except ValueError:
                    val = raw_val
            elif attr_type in ("int", "long"):
                try:
                    val = int(raw_val)
                except ValueError:
                    val = raw_val
            elif attr_type == "boolean":
                val = raw_val.lower() in ("true", "1")
            else:
                val = intern(raw_val) if len(raw_val) <= 64 else raw_val

            current_attrs[attr_name] = val
            current_data_key = None

        elif name == "node" and current_target == "node":
            graph.add_node(current_node_id, **current_attrs)
            current_target = None
            current_node_id = None
            current_attrs = {}

        elif name == "edge" and current_target == "edge":
            if current_edge_key is not None:
                graph.add_edge(
                    current_edge_src,
                    current_edge_dst,
                    key=current_edge_key,
                    **current_attrs
                )
            else:
                graph.add_edge(
                    current_edge_src,
                    current_edge_dst,
                    **current_attrs
                )
            current_target = None
            current_edge_src = None
            current_edge_dst = None
            current_edge_key = None
            current_attrs = {}

    parser = xml.parsers.expat.ParserCreate()
    parser.StartElementHandler = start_element
    parser.EndElementHandler = end_element
    parser.CharacterDataHandler = char_data

    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(8 * 1024 * 1024)
            if not chunk:
                break
            parser.Parse(chunk, False)
        parser.Parse(b"", True)

    return graph


def load_or_cache_osm_graph(graph_file=None, cache_file=None, use_cache=True):
    """
    Load the Bengaluru OSM road graph, using a binary pickle cache when
    available so the 896 MB GraphML XML file is not repeatedly parsed.
    """

    graph_path = Path(graph_file) if graph_file is not None else get_graph_path()
    cache_path = Path(cache_file) if cache_file is not None else get_cache_path()

    if use_cache and cache_path.exists():
        try:
            if not graph_path.exists() or cache_path.stat().st_mtime >= graph_path.stat().st_mtime:
                with open(cache_path, "rb") as f:
                    return pickle.load(f)
        except Exception:
            pass

    if not graph_path.exists():
        raise FileNotFoundError(f"Graph file not found: {graph_path}")

    graph = load_graphml_streaming(graph_path)

    if use_cache:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "wb") as f:
                pickle.dump(graph, f, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception:
            pass

    return graph


# --------------------------------------------------
# HELPER: CHECK WHETHER AN ATTRIBUTE IS AVAILABLE
# --------------------------------------------------

DEFAULT_PLACEHOLDER_VALUES = {
    "bridge": {"no", "unknown", "not_specified", "none", ""},
    "tunnel": {"no", "unknown", "not_specified", "none", ""},
    "ford": {"no", "unknown", "not_specified", "none", ""},
    "layer": {"0", "unknown", "not_specified", "none", ""},
}


def is_available(value, attribute=None, osm_tags_dict=None):
    """
    Check whether an edge attribute is genuinely available.
    For attributes that were assigned default values during extraction
    (such as bridge="no", tunnel="no", ford="no", layer="0"), verify
    whether the tag was explicitly present in OSM or differs from the
    default placeholder.
    """

    if value is None:
        return False

    normalized = str(value).strip().lower()

    if normalized in ("", "unknown", "not_specified", "none"):
        return False

    if attribute in DEFAULT_PLACEHOLDER_VALUES:
        if osm_tags_dict is not None:
            return attribute in osm_tags_dict
        if normalized in DEFAULT_PLACEHOLDER_VALUES[attribute]:
            return False

    return True


# --------------------------------------------------
# MAIN VALIDATION FUNCTION
# --------------------------------------------------

def validate_osm_graph(graph_file=None, use_cache=True):

    graph_path = Path(graph_file) if graph_file is not None else get_graph_path()

    if not graph_path.exists():

        raise FileNotFoundError(
            f"Graph file not found: {graph_path}"
        )

    print("Loading Bengaluru OSM road graph...", flush=True)

    graph = load_or_cache_osm_graph(graph_path, use_cache=use_cache)

    print("\n===================================")
    print("      GRAPH SUMMARY")
    print("===================================")

    print("Graph type:", type(graph).__name__)

    print("Is directed:", graph.is_directed())

    print("Is multigraph:", graph.is_multigraph())

    print("Total nodes:", graph.number_of_nodes())

    print("Total directed edges:", graph.number_of_edges(), flush=True)

    # --------------------------------------------------
    # CONNECTIVITY CHECK (WEAKLY CONNECTED - ZERO COPY)
    # --------------------------------------------------

    print("\n===================================")
    print("       CONNECTIVITY CHECK")
    print("===================================")

    component_count = 0
    largest_size = 0

    for comp in nx.weakly_connected_components(graph):
        component_count += 1
        comp_len = len(comp)
        if comp_len > largest_size:
            largest_size = comp_len

    total_nodes = graph.number_of_nodes()

    coverage = (
        largest_size / total_nodes * 100
        if total_nodes > 0
        else 0
    )

    print("Connected components:", component_count)

    print("Largest component nodes:", largest_size)

    print(
        "Largest component coverage:",
        round(coverage, 2),
        "%"
    )

    print(
        "Nodes outside largest component:",
        total_nodes - largest_size,
        flush=True
    )

    # --------------------------------------------------
    # DIRECTED CONNECTIVITY CHECK
    # --------------------------------------------------

    print("\n===================================")
    print("      DIRECTED CONNECTIVITY")
    print("===================================")

    strong_component_count = 0

    largest_strong_component = 0

    for component in nx.strongly_connected_components(graph):

        strong_component_count += 1

        if len(component) > largest_strong_component:

            largest_strong_component = len(component)

    print(
        "Strongly connected components:",
        strong_component_count
    )

    print(
        "Largest strongly connected component:",
        largest_strong_component
    )

    print(
        "Note: Strong connectivity is stricter than ordinary road connectivity.",
        flush=True
    )

    # --------------------------------------------------
    # SINGLE-PASS EDGE & ATTRIBUTE VALIDATION
    # --------------------------------------------------

    attributes_to_check = [
        "road_id",
        "name",
        "highway",
        "bridge",
        "tunnel",
        "access",
        "vehicle",
        "motor_vehicle",
        "emergency",
        "maxspeed",
        "surface",
        "lanes",
        "junction",
        "layer",
        "lit",
        "smoothness",
        "width",
        "toll",
        "ford",
        "osm_tags"
    ]

    direction_counts = Counter()
    highway_counts = Counter()
    populated_counts = {attr: 0 for attr in attributes_to_check}
    explicit_tag_counts = {attr: 0 for attr in attributes_to_check}

    unique_road_ways = set()
    bridge_edges = 0
    bridge_ways = set()
    tunnel_edges = 0
    tunnel_ways = set()
    restricted_edges = 0
    restricted_ways = set()

    valid_length_count = 0
    min_length = float("inf")
    max_length = 0.0
    total_length = 0.0
    missing_lengths = 0
    invalid_lengths = 0
    short_lengths = 0

    for _, _, data in graph.edges(data=True):

        road_id = str(data.get("road_id", ""))
        if road_id:
            unique_road_ways.add(road_id)

        # Parse original OSM tags if available to check explicit tagging
        raw_osm_tags = data.get("osm_tags")
        osm_tags_dict = None
        if isinstance(raw_osm_tags, str) and raw_osm_tags.startswith("{"):
            try:
                osm_tags_dict = json.loads(raw_osm_tags)
            except Exception:
                osm_tags_dict = None

        # 1. Direction
        direction = data.get("oneway", "missing")
        direction_counts[direction] += 1

        # 2. Highway classification
        highway = data.get("highway", "unknown")
        highway_counts[highway] += 1

        # 3. Attribute availability (both non-empty/default and explicitly tagged)
        for attr in attributes_to_check:
            val = data.get(attr)
            if is_available(val):
                populated_counts[attr] += 1
            if is_available(val, attribute=attr, osm_tags_dict=osm_tags_dict):
                explicit_tag_counts[attr] += 1

        # 4. Infrastructure & access restrictions (edges AND unique road ways)
        bridge = str(data.get("bridge", "unknown")).lower()
        tunnel = str(data.get("tunnel", "unknown")).lower()

        if bridge not in ("no", "unknown", ""):
            bridge_edges += 1
            if road_id:
                bridge_ways.add(road_id)

        if tunnel not in ("no", "unknown", ""):
            tunnel_edges += 1
            if road_id:
                tunnel_ways.add(road_id)

        restricted_values = (
            str(data.get("access", "unknown")).lower(),
            str(data.get("vehicle", "unknown")).lower(),
            str(data.get("motor_vehicle", "unknown")).lower()
        )

        if any(value in ("private", "no") for value in restricted_values):
            restricted_edges += 1
            if road_id:
                restricted_ways.add(road_id)

        # 5. Road length validation
        try:
            length = float(data.get("length_m"))
            if length <= 0:
                invalid_lengths += 1
            else:
                valid_length_count += 1
                total_length += length
                if length < min_length:
                    min_length = length
                if length > max_length:
                    max_length = length
                if length < 0.05:
                    short_lengths += 1
        except (TypeError, ValueError):
            missing_lengths += 1

    # --------------------------------------------------
    # ROAD DIRECTION CHECK
    # --------------------------------------------------

    print("\n===================================")
    print("       ROAD DIRECTION CHECK")
    print("===================================")

    for direction, count in sorted(direction_counts.items()):
        print(f"{direction}: {count}")

    # --------------------------------------------------
    # ROAD CLASSIFICATION CHECK
    # --------------------------------------------------

    print("\n===================================")
    print("       ROAD CLASSIFICATIONS")
    print("===================================")

    for highway, count in highway_counts.most_common():
        print(f"{highway}: {count}")

    # --------------------------------------------------
    # ATTRIBUTE AVAILABILITY CHECK
    # --------------------------------------------------

    print("\n===================================")
    print("       ROAD ATTRIBUTE CHECK")
    print("===================================")
    print("(Distinguishing explicitly tagged OSM values from extraction defaults)")

    total_edges = graph.number_of_edges()

    for attribute in attributes_to_check:
        explicit = explicit_tag_counts[attribute]
        populated = populated_counts[attribute]
        pct_explicit = (explicit / total_edges * 100) if total_edges > 0 else 0.0
        if attribute in DEFAULT_PLACEHOLDER_VALUES:
            print(
                f"{attribute:15} : "
                f"{explicit:8} / {total_edges} explicitly tagged ({pct_explicit:.2f}%) "
                f"[populated incl. default: {populated}]"
            )
        else:
            print(
                f"{attribute:15} : "
                f"{explicit:8} / {total_edges} "
                f"({pct_explicit:.2f}%)"
            )

    # --------------------------------------------------
    # BRIDGE AND TUNNEL CHECK
    # --------------------------------------------------

    print("\n===================================")
    print("       INFRASTRUCTURE CHECK")
    print("===================================")

    print("Unique OSM road ways in graph:", len(unique_road_ways))
    print(
        f"Bridges        : {len(bridge_ways):6} unique OSM road ways | "
        f"{bridge_edges:8} directed edges"
    )
    print(
        f"Tunnels        : {len(tunnel_ways):6} unique OSM road ways | "
        f"{tunnel_edges:8} directed edges"
    )
    print(
        f"Restricted     : {len(restricted_ways):6} unique OSM road ways | "
        f"{restricted_edges:8} directed edges (access/vehicle/motor_vehicle in private/no)"
    )

    # --------------------------------------------------
    # ROAD LENGTH VALIDATION
    # --------------------------------------------------

    print("\n===================================")
    print("       ROAD LENGTH VALIDATION")
    print("===================================")

    if valid_length_count > 0:

        print("Valid road lengths:", valid_length_count)

        print("Minimum length:", round(min_length, 2), "m")

        print("Maximum length:", round(max_length, 2), "m")

        print(
            "Average length:",
            round(total_length / valid_length_count, 2),
            "m"
        )

    print("Missing or unreadable lengths:", missing_lengths)

    print("Invalid non-positive lengths:", invalid_lengths)

    print("Very short segments (< 0.05 m):", short_lengths)

    # --------------------------------------------------
    # FINAL VALIDATION SUMMARY
    # --------------------------------------------------

    print("\n===================================")
    print("       VALIDATION SUMMARY")
    print("===================================")

    checks = {
        "Graph loaded successfully":
            graph.number_of_nodes() > 0,

        "Graph is directed":
            graph.is_directed(),

        "Graph preserves parallel edges":
            graph.is_multigraph(),

        "Road connectivity exists":
            component_count > 0,

        "Road IDs are available":
            direction_counts.total() > 0,

        "Road lengths are available":
            valid_length_count > 0
    }

    for check, passed in checks.items():

        print(
            ("PASS" if passed else "CHECK"),
            "-",
            check
        )

    print("\nGraph validation completed.")

    print("===================================", flush=True)

    return graph


# --------------------------------------------------
# PROGRAM ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":

    validate_osm_graph()
