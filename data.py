"""
SANJEEVANI: Human-Centric Disaster Intelligence & Infrastructure Resilience
Module 1: Disaster Prediction & Infrastructure Resilience
File: data.py

Purpose:
    Generates and manages the synthetic city road network model.
    Provides graph representations of residential zones, hospitals,
    shelters, emergency stations, junctions, roads, and bridges.

Scientific & Prototype Disclaimer:
    ALL DATA IN THIS MODULE IS SYNTHETIC AND DESIGNED SOLELY FOR PROTOTYPE
    DEMONSTRATION AND DECISION-SUPPORT TESTING. IT DOES NOT REPRESENT REAL-WORLD
    GEOGRAPHICAL SURVEYS OR CALIBRATED FLOOD PREDICTIONS.
"""

import json
from typing import Dict, List, Tuple, Any
import networkx as nx
import pandas as pd


# -----------------------------------------------------------------------------
# 1. SYNTHETIC RAW DATA DEFINITIONS
# -----------------------------------------------------------------------------

SYNTHETIC_METADATA: Dict[str, Any] = {
    "dataset_name": "SANJEEVANI_Synthetic_City_Network",
    "version": "1.0-prototype",
    "is_synthetic": True,
    "description": (
        "Synthetic city network modeled with residential wards, critical hospitals, "
        "emergency shelters, response bases, roads, and flood-vulnerable bridges."
    ),
}

# Node definitions with IDs, names, types, capacities/populations, and (x, y) map coordinates
RAW_NODES: List[Dict[str, Any]] = [
    # Residential Zones
    {
        "id": "R1",
        "name": "Riverside Colony",
        "type": "residential",
        "population": 14000,
        "flood_exposure": "high",
        "pos": (15, 40),
    },
    {
        "id": "R2",
        "name": "Downtown Heights",
        "type": "residential",
        "population": 28000,
        "flood_exposure": "medium",
        "pos": (45, 60),
    },
    {
        "id": "R3",
        "name": "Hilltop Suburb",
        "type": "residential",
        "population": 9500,
        "flood_exposure": "low",
        "pos": (20, 85),
    },
    {
        "id": "R4",
        "name": "East End Ward",
        "type": "residential",
        "population": 18000,
        "flood_exposure": "medium",
        "pos": (85, 45),
    },
    {
        "id": "R5",
        "name": "Old Town Quarter",
        "type": "residential",
        "population": 12500,
        "flood_exposure": "high",
        "pos": (60, 25),
    },
    {
        "id": "R6",
        "name": "Lakeside Enclave",
        "type": "residential",
        "population": 8000,
        "flood_exposure": "high",
        "pos": (30, 15),
    },
    # Hospitals
    {
        "id": "H1",
        "name": "City General Hospital",
        "type": "hospital",
        "capacity": 450,  # Inpatient bed capacity
        "pos": (50, 75),
    },
    {
        "id": "H2",
        "name": "Apex Trauma Center",
        "type": "hospital",
        "capacity": 250,
        "pos": (80, 20),
    },
    # Emergency Shelters
    {
        "id": "S1",
        "name": "North Community Stadium Shelter",
        "type": "shelter",
        "capacity": 3500,  # Evacuee capacity
        "pos": (35, 90),
    },
    {
        "id": "S2",
        "name": "East High School Civic Camp",
        "type": "shelter",
        "capacity": 2000,
        "pos": (70, 70),
    },
    # Emergency Response Stations (Ambulance / Fire / Rescue)
    {
        "id": "E1",
        "name": "Central Fire & EMS Hub",
        "type": "emergency_station",
        "capacity": 20,  # Available vehicle fleet
        "pos": (40, 50),
    },
    {
        "id": "E2",
        "name": "Westside Rescue Depot",
        "type": "emergency_station",
        "capacity": 15,
        "pos": (10, 60),
    },
    # Road Junctions (intersections)
    {
        "id": "J1",
        "name": "Central Circle Junction",
        "type": "junction",
        "pos": (35, 45),
    },
    {
        "id": "J2",
        "name": "River Crossing Bridgehead",
        "type": "junction",
        "pos": (55, 45),
    },
    {
        "id": "J3",
        "name": "East Arterial Junction",
        "type": "junction",
        "pos": (75, 55),
    },
    {
        "id": "J4",
        "name": "North Ridge Junction",
        "type": "junction",
        "pos": (25, 75),
    },
]

# Edge definitions: Roads and Bridges connecting nodes
# failure_probability and flood_sensitivity are normalized scores between 0.0 and 1.0.
RAW_EDGES: List[Dict[str, Any]] = [
    {
        "road_id": "RD01",
        "source": "R1",
        "destination": "J1",
        "name": "Riverside South Link",
        "distance_km": 2.5,
        "travel_time_min": 5.0,
        "failure_probability": 0.65,
        "flood_sensitivity": 0.80,
        "road_type": "arterial",
        "is_available": True,
    },
    {
        "road_id": "RD02",
        "source": "R1",
        "destination": "E2",
        "name": "West Embankment Road",
        "distance_km": 2.0,
        "travel_time_min": 4.0,
        "failure_probability": 0.70,
        "flood_sensitivity": 0.85,
        "road_type": "local",
        "is_available": True,
    },
    {
        "road_id": "RD03",
        "source": "E2",
        "destination": "J4",
        "name": "West Bypass Highway",
        "distance_km": 3.0,
        "travel_time_min": 4.5,
        "failure_probability": 0.15,
        "flood_sensitivity": 0.20,
        "road_type": "highway",
        "is_available": True,
    },
    {
        "road_id": "RD04",
        "source": "J4",
        "destination": "R3",
        "name": "Hilltop Access Road",
        "distance_km": 1.8,
        "travel_time_min": 3.6,
        "failure_probability": 0.10,
        "flood_sensitivity": 0.10,
        "road_type": "local",
        "is_available": True,
    },
    {
        "road_id": "RD05",
        "source": "J4",
        "destination": "S1",
        "name": "North Stadium Way",
        "distance_km": 2.2,
        "travel_time_min": 4.0,
        "failure_probability": 0.12,
        "flood_sensitivity": 0.15,
        "road_type": "arterial",
        "is_available": True,
    },
    {
        "road_id": "RD06",
        "source": "S1",
        "destination": "H1",
        "name": "Hospital North Link",
        "distance_km": 2.8,
        "travel_time_min": 5.0,
        "failure_probability": 0.15,
        "flood_sensitivity": 0.20,
        "road_type": "arterial",
        "is_available": True,
    },
    {
        "road_id": "RD07",
        "source": "J4",
        "destination": "J1",
        "name": "North-Central Corridor",
        "distance_km": 3.5,
        "travel_time_min": 6.0,
        "failure_probability": 0.25,
        "flood_sensitivity": 0.30,
        "road_type": "arterial",
        "is_available": True,
    },
    {
        "road_id": "RD08",
        "source": "J1",
        "destination": "E1",
        "name": "Central Station Link",
        "distance_km": 1.0,
        "travel_time_min": 2.0,
        "failure_probability": 0.10,
        "flood_sensitivity": 0.20,
        "road_type": "local",
        "is_available": True,
    },
    {
        "road_id": "RD09",
        "source": "E1",
        "destination": "R2",
        "name": "Downtown Spine Avenue",
        "distance_km": 1.5,
        "travel_time_min": 3.0,
        "failure_probability": 0.20,
        "flood_sensitivity": 0.25,
        "road_type": "arterial",
        "is_available": True,
    },
    {
        "road_id": "RD10",
        "source": "R2",
        "destination": "H1",
        "name": "Downtown Hospital Expressway",
        "distance_km": 2.0,
        "travel_time_min": 3.5,
        "failure_probability": 0.15,
        "flood_sensitivity": 0.15,
        "road_type": "highway",
        "is_available": True,
    },
    {
        "road_id": "RD11",
        "source": "J1",
        "destination": "J2",
        "name": "Grand River Bridge",
        "distance_km": 2.2,
        "travel_time_min": 4.4,
        "failure_probability": 0.80,
        "flood_sensitivity": 0.90,
        "road_type": "bridge",
        "is_available": True,
    },
    {
        "road_id": "RD12",
        "source": "J2",
        "destination": "R5",
        "name": "Old Town Riverway",
        "distance_km": 2.5,
        "travel_time_min": 5.0,
        "failure_probability": 0.55,
        "flood_sensitivity": 0.70,
        "road_type": "arterial",
        "is_available": True,
    },
    {
        "road_id": "RD13",
        "source": "R5",
        "destination": "H2",
        "name": "Apex Hospital Spur",
        "distance_km": 2.0,
        "travel_time_min": 4.0,
        "failure_probability": 0.20,
        "flood_sensitivity": 0.25,
        "road_type": "local",
        "is_available": True,
    },
    {
        "road_id": "RD14",
        "source": "J2",
        "destination": "J3",
        "name": "East Crossway Bridge",
        "distance_km": 2.8,
        "travel_time_min": 5.5,
        "failure_probability": 0.75,
        "flood_sensitivity": 0.85,
        "road_type": "bridge",
        "is_available": True,
    },
    {
        "road_id": "RD15",
        "source": "J3",
        "destination": "R4",
        "name": "East End Boulevard",
        "distance_km": 2.0,
        "travel_time_min": 4.0,
        "failure_probability": 0.25,
        "flood_sensitivity": 0.30,
        "road_type": "arterial",
        "is_available": True,
    },
    {
        "road_id": "RD16",
        "source": "J3",
        "destination": "S2",
        "name": "East Shelter Approach",
        "distance_km": 1.8,
        "travel_time_min": 3.5,
        "failure_probability": 0.18,
        "flood_sensitivity": 0.20,
        "road_type": "local",
        "is_available": True,
    },
    {
        "road_id": "RD17",
        "source": "S2",
        "destination": "H1",
        "name": "Civic Overpass",
        "distance_km": 3.2,
        "travel_time_min": 5.5,
        "failure_probability": 0.20,
        "flood_sensitivity": 0.25,
        "road_type": "highway",
        "is_available": True,
    },
    {
        "road_id": "RD18",
        "source": "R6",
        "destination": "J1",
        "name": "Lakeside Boulevard",
        "distance_km": 3.0,
        "travel_time_min": 6.0,
        "failure_probability": 0.60,
        "flood_sensitivity": 0.75,
        "road_type": "arterial",
        "is_available": True,
    },
    {
        "road_id": "RD19",
        "source": "R6",
        "destination": "R5",
        "name": "South Bank Causeway Bridge",
        "distance_km": 3.5,
        "travel_time_min": 7.0,
        "failure_probability": 0.85,
        "flood_sensitivity": 0.95,
        "road_type": "bridge",
        "is_available": True,
    },
    {
        "road_id": "RD20",
        "source": "R4",
        "destination": "H2",
        "name": "Industrial Link to Trauma Center",
        "distance_km": 2.5,
        "travel_time_min": 5.0,
        "failure_probability": 0.20,
        "flood_sensitivity": 0.20,
        "road_type": "arterial",
        "is_available": True,
    },
]


# -----------------------------------------------------------------------------
# 2. GRAPH CONSTRUCTION FUNCTIONS
# -----------------------------------------------------------------------------

def build_synthetic_city() -> nx.Graph:
    """
    Constructs and returns the synthetic city road network as an undirected NetworkX Graph.

    Each node contains:
        - name (str): Human-readable landmark name
        - type (str): 'residential', 'hospital', 'shelter', 'emergency_station', 'junction'
        - pos (tuple[int, int]): Synthetic coordinate for map rendering
        - population (int, optional): Inhabitants (for residential zones)
        - capacity (int, optional): Beds or evacuee limit (for hospitals/shelters/stations)
        - flood_exposure (str, optional): Inherent vulnerability rating

    Each edge contains:
        - road_id (str): Unique road identifier (e.g. 'RD01')
        - name (str): Descriptive road name
        - distance_km (float): Physical road length in kilometres
        - travel_time_min (float): Normal travel duration in minutes
        - failure_probability (float): Risk likelihood between 0.0 and 1.0
        - flood_sensitivity (float): Inundation vulnerability between 0.0 and 1.0
        - road_type (str): 'bridge', 'highway', 'arterial', 'local'
        - is_available (bool): Operability flag (True = open, False = flooded/blocked)
        - is_synthetic (bool): Explicit synthetic data declaration
    """
    # nx.Graph represents an undirected network (traffic flows in both directions)
    G = nx.Graph()
    G.graph["metadata"] = SYNTHETIC_METADATA.copy()

    # Add all nodes with their associated properties
    for node_info in RAW_NODES:
        node_id = node_info["id"]
        # Copy attributes so caller mutations do not alter constant data
        attrs = {k: v for k, v in node_info.items() if k != "id"}
        attrs["is_synthetic"] = True
        G.add_node(node_id, **attrs)

    # Add all edges with their associated properties
    for edge_info in RAW_EDGES:
        u = edge_info["source"]
        v = edge_info["destination"]
        attrs = {k: v for k, v in edge_info.items() if k not in ("source", "destination")}
        attrs["is_synthetic"] = True
        G.add_edge(u, v, **attrs)

    return G


def get_nodes_by_type(graph: nx.Graph, node_type: str) -> List[str]:
    """
    Returns a list of node IDs matching the specified type.
    
    Examples:
        get_nodes_by_type(G, 'residential') -> ['R1', 'R2', 'R3', 'R4', 'R5', 'R6']
        get_nodes_by_type(G, 'hospital')    -> ['H1', 'H2']
        get_nodes_by_type(G, 'shelter')     -> ['S1', 'S2']
    """
    return [
        node_id for node_id, data in graph.nodes(data=True)
        if data.get("type") == node_type
    ]


def get_city_summary(graph: nx.Graph) -> Dict[str, Any]:
    """
    Produces a structured dictionary summarizing the city network statistics.
    Useful for health checks, debugging, and dashboard header cards.
    """
    residential_nodes = get_nodes_by_type(graph, "residential")
    hospitals = get_nodes_by_type(graph, "hospital")
    shelters = get_nodes_by_type(graph, "shelter")
    stations = get_nodes_by_type(graph, "emergency_station")
    junctions = get_nodes_by_type(graph, "junction")

    total_population = sum(
        graph.nodes[n].get("population", 0) for n in residential_nodes
    )
    total_hospital_capacity = sum(
        graph.nodes[n].get("capacity", 0) for n in hospitals
    )
    total_shelter_capacity = sum(
        graph.nodes[n].get("capacity", 0) for n in shelters
    )

    bridges = [
        (u, v) for u, v, data in graph.edges(data=True)
        if data.get("road_type") == "bridge"
    ]

    return {
        "is_synthetic": True,
        "total_nodes": graph.number_of_nodes(),
        "total_edges": graph.number_of_edges(),
        "residential_zones_count": len(residential_nodes),
        "total_population": total_population,
        "hospitals_count": len(hospitals),
        "total_hospital_beds": total_hospital_capacity,
        "shelters_count": len(shelters),
        "total_shelter_capacity": total_shelter_capacity,
        "emergency_stations_count": len(stations),
        "junctions_count": len(junctions),
        "bridges_count": len(bridges),
        "is_fully_connected_initially": nx.is_connected(graph),
    }


def export_city_to_dataframes(graph: nx.Graph) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Converts graph nodes and edges into two tabular Pandas DataFrames.
    This provides an integration-friendly interface for Member 3 and Member 4.
    """
    # 1. Nodes DataFrame
    node_rows = []
    for node_id, data in graph.nodes(data=True):
        row = {"node_id": node_id, **data}
        # Flatten tuple coordinates for tabular clarity
        if "pos" in row and isinstance(row["pos"], (tuple, list)):
            row["pos_x"] = row["pos"][0]
            row["pos_y"] = row["pos"][1]
        node_rows.append(row)
    nodes_df = pd.DataFrame(node_rows)

    # 2. Edges DataFrame
    edge_rows = []
    for u, v, data in graph.edges(data=True):
        row = {"source": u, "destination": v, **data}
        edge_rows.append(row)
    edges_df = pd.DataFrame(edge_rows)

    return nodes_df, edges_df


def save_city_to_json(graph: nx.Graph, filepath: str) -> None:
    """
    Serializes the synthetic network to a clean, JSON-compatible format on disk.
    Allows non-Python modules or external dashboards to read the city graph.
    """
    payload: Dict[str, Any] = {
        "metadata": graph.graph.get("metadata", SYNTHETIC_METADATA),
        "nodes": [],
        "edges": [],
    }

    for node_id, data in graph.nodes(data=True):
        payload["nodes"].append({"id": node_id, **data})

    for u, v, data in graph.edges(data=True):
        payload["edges"].append({"source": u, "destination": v, **data})

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_city_from_json(filepath: str) -> nx.Graph:
    """
    Reconstructs an undirected NetworkX Graph from a saved JSON file.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        payload = json.load(f)

    G = nx.Graph()
    G.graph["metadata"] = payload.get("metadata", {})

    for node_info in payload.get("nodes", []):
        node_id = node_info["id"]
        attrs = {k: v for k, v in node_info.items() if k != "id"}
        if "pos" in attrs and isinstance(attrs["pos"], list):
            attrs["pos"] = tuple(attrs["pos"])
        G.add_node(node_id, **attrs)

    for edge_info in payload.get("edges", []):
        u = edge_info["source"]
        v = edge_info["destination"]
        attrs = {k: v for k, v in edge_info.items() if k not in ("source", "destination")}
        G.add_edge(u, v, **attrs)

    return G

