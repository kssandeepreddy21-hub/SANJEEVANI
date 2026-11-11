"""
sanjeevani/data.py
------------------
Temporary Synthetic Prototype Data Provider & NetworkX Road Graph for SANJEEVANI.
Clearly labeled as simulated prototype data for development and demonstration
until Member 1, Member 2, and Member 3 modules are integrated.
"""

import networkx as nx
import pandas as pd


# Synthetic city center coordinates (Prototype Urban Grid)
CITY_CENTER = (12.9716, 77.5946)

SCENARIO_PROFILES = {
    "Baseline Monitoring (Normal Rain - 15 mm/hr)": {
        "status_level": "GUARDED",
        "status_color": "#22C55E",  # Green
        "rainfall_mm_hr": 15,
        "total_incidents": 6,
        "critical_incidents": 1,
        "blocked_roads": 1,
        "available_ambulances": 14,
        "total_ambulances": 16,
        "affected_population": 1850,
    },
    "Severe Urban Flood (Heavy Rain - 65 mm/hr)": {
        "status_level": "HIGH ALERT",
        "status_color": "#F97316",  # Orange
        "rainfall_mm_hr": 65,
        "total_incidents": 14,
        "critical_incidents": 5,
        "blocked_roads": 3,
        "available_ambulances": 9,
        "total_ambulances": 16,
        "affected_population": 12400,
    },
    "Extreme Flash Flood & Landslide (115 mm/hr)": {
        "status_level": "CRITICAL EMERGENCY",
        "status_color": "#EF4444",  # Red
        "rainfall_mm_hr": 115,
        "total_incidents": 23,
        "critical_incidents": 9,
        "blocked_roads": 5,
        "available_ambulances": 5,
        "total_ambulances": 16,
        "affected_population": 28900,
    },
}

# Synthetic City Junction Nodes for NetworkX representation
SYNTHETIC_JUNCTIONS = {
    "J1": {
        "name": "J1 • West Connector Hub",
        "sector": "West Connector",
        "lat": 12.9690,
        "lon": 77.5850,
        "population": 4200,
        "hospital_id": None,
    },
    "J2": {
        "name": "J2 • Central Trauma Junction (HOSP-01)",
        "sector": "Central Riverfront",
        "lat": 12.9765,
        "lon": 77.5990,
        "population": 6800,
        "hospital_id": "HOSP-01",
    },
    "J3": {
        "name": "J3 • North Medical Hub (HOSP-02)",
        "sector": "North District",
        "lat": 12.9880,
        "lon": 77.5850,
        "population": 5100,
        "hospital_id": "HOSP-02",
    },
    "J4": {
        "name": "J4 • Sector 4 Lowland Junction",
        "sector": "Sector 4 Lowlands",
        "lat": 12.9630,
        "lon": 77.5910,
        "population": 8400,
        "hospital_id": None,
    },
    "J5": {
        "name": "J5 • South Riverfront Hub (HOSP-03)",
        "sector": "South Valley",
        "lat": 12.9560,
        "lon": 77.6040,
        "population": 6200,
        "hospital_id": "HOSP-03",
    },
    "J6": {
        "name": "J6 • East Basin Residential Node",
        "sector": "East Basin",
        "lat": 12.9685,
        "lon": 77.6110,
        "population": 5500,
        "hospital_id": None,
    },
}

SECTOR_TO_JUNCTION = {
    "West Connector": "J1",
    "Central Riverfront": "J2",
    "Central Corridor": "J2",
    "North District": "J3",
    "Sector 4 Lowlands": "J4",
    "Old Bridge Junction": "J4",
    "South Valley": "J5",
    "East Basin": "J6",
    "East Residential Zone": "J6",
}


def get_scenario_names() -> list[str]:
    """Return list of available synthetic disaster scenarios."""
    return list(SCENARIO_PROFILES.keys())


def get_overview_metrics(
    scenario_name: str,
    manual_failed_roads: set[str] | None = None,
    extra_incidents_count: int = 0,
    extra_critical_count: int = 0,
) -> dict:
    """Return top-level KPI metrics for the selected synthetic scenario, adjusted for live session interactions."""
    base = dict(
        SCENARIO_PROFILES.get(
            scenario_name,
            SCENARIO_PROFILES["Severe Urban Flood (Heavy Rain - 65 mm/hr)"],
        )
    )
    roads = get_synthetic_roads(scenario_name, manual_failed_roads=manual_failed_roads)
    blocked_count = sum(1 for r in roads if r["status"] == "BLOCKED")
    base["blocked_roads"] = blocked_count
    base["total_incidents"] = base["total_incidents"] + extra_incidents_count
    base["critical_incidents"] = base["critical_incidents"] + extra_critical_count
    if manual_failed_roads:
        # Add affected population from manually failed roads
        extra_pop = sum(
            r["population_impact"]
            for r in roads
            if r["road_id"] in manual_failed_roads and r["base_status"] != "BLOCKED"
        )
        base["affected_population"] += extra_pop
    return base


def get_synthetic_hospitals() -> pd.DataFrame:
    """Return synthetic hospitals (BLUE markers)."""
    data = [
        {
            "hospital_id": "HOSP-01",
            "name": "Central Trauma & Emergency Hospital (Synthetic)",
            "junction": "J2",
            "lat": 12.9765,
            "lon": 77.5990,
            "icu_beds_free": 18,
            "status": "Operational",
        },
        {
            "hospital_id": "HOSP-02",
            "name": "North District Medical Centre (Synthetic)",
            "junction": "J3",
            "lat": 12.9880,
            "lon": 77.5850,
            "icu_beds_free": 9,
            "status": "Operational",
        },
        {
            "hospital_id": "HOSP-03",
            "name": "South Riverfront General Hospital (Synthetic)",
            "junction": "J5",
            "lat": 12.9560,
            "lon": 77.6040,
            "icu_beds_free": 4,
            "status": "High Load",
        },
    ]
    return pd.DataFrame(data)


def get_synthetic_rescue_teams() -> pd.DataFrame:
    """Return synthetic rescue teams & ambulances (PURPLE markers)."""
    data = [
        {
            "unit_id": "RESCUE-ALPHA",
            "type": "NDRF Flood Response Boat Unit",
            "lat": 12.9730,
            "lon": 77.5860,
            "status": "Deployed",
            "assigned_sector": "Sector 4 Lowlands",
        },
        {
            "unit_id": "AMB-104",
            "type": "Advanced Life Support Ambulance",
            "lat": 12.9795,
            "lon": 77.6010,
            "status": "Available",
            "assigned_sector": "Central Corridor",
        },
        {
            "unit_id": "RESCUE-BRAVO",
            "type": "Heavy Engineering & Clearance Team",
            "lat": 12.9630,
            "lon": 77.5910,
            "status": "En Route",
            "assigned_sector": "Old Bridge Junction",
        },
        {
            "unit_id": "AMB-207",
            "type": "Rapid Medical Response Unit",
            "lat": 12.9685,
            "lon": 77.6110,
            "status": "Available",
            "assigned_sector": "East Residential Zone",
        },
    ]
    return pd.DataFrame(data)


def get_synthetic_roads(
    scenario_name: str,
    manual_failed_roads: set[str] | None = None,
) -> list[dict]:
    """
    Return synthetic road segments with NetworkX node endpoints, coordinates, and status.
    Status colors:
      - SAFE: #22C55E (Green)
      - WARNING: #F97316 (Orange)
      - BLOCKED: #EF4444 (Red)
    """
    is_extreme = "Extreme" in scenario_name
    is_baseline = "Baseline" in scenario_name
    manual_failed = manual_failed_roads or set()

    roads = [
        {
            "road_id": "RD-101",
            "name": "Riverfront Arterial Bridge (Synthetic)",
            "u": "J1",
            "v": "J2",
            "distance_km": 3.4,
            "coords": [[12.9690, 77.5850], [12.9716, 77.5946], [12.9765, 77.5990]],
            "base_status": "WARNING" if is_baseline else "BLOCKED",
            "failure_prob": 0.35 if is_baseline else 0.92,
            "vulnerability_score": 88,
            "population_impact": 6400,
            "critical_rank": 1,
            "preposition_Zone": "J1 • West Bridge Approach",
            "reason": "Water level above deck threshold",
        },
        {
            "road_id": "RD-102",
            "name": "North Medical Corridor (Synthetic)",
            "u": "J2",
            "v": "J3",
            "distance_km": 2.9,
            "coords": [[12.9765, 77.5990], [12.9830, 77.5920], [12.9880, 77.5850]],
            "base_status": "SAFE",
            "failure_prob": 0.12,
            "vulnerability_score": 24,
            "population_impact": 3900,
            "critical_rank": 5,
            "preposition_Zone": "J2 • Central Trauma Plaza",
            "reason": "Elevated highway - clear drainage",
        },
        {
            "road_id": "RD-103",
            "name": "Sector 4 Underpass Link (Synthetic)",
            "u": "J4",
            "v": "J2",
            "distance_km": 2.2,
            "coords": [[12.9630, 77.5910], [12.9680, 77.5930], [12.9716, 77.5946], [12.9765, 77.5990]],
            "base_status": "BLOCKED",
            "failure_prob": 0.96,
            "vulnerability_score": 95,
            "population_impact": 8400,
            "critical_rank": 2,
            "preposition_Zone": "J4 • Sector 4 High Ground School",
            "reason": "Submerged underpass (2.1m water depth)",
        },
        {
            "road_id": "RD-104",
            "name": "East Ring Expressway (Synthetic)",
            "u": "J5",
            "v": "J6",
            "distance_km": 3.1,
            "coords": [[12.9560, 77.6040], [12.9620, 77.6085], [12.9685, 77.6110]],
            "base_status": "WARNING" if is_extreme else "SAFE",
            "failure_prob": 0.64 if is_extreme else 0.18,
            "vulnerability_score": 46,
            "population_impact": 5200,
            "critical_rank": 4,
            "preposition_Zone": "J6 • East Ring Interchange",
            "reason": "Surface runoff accumulation near exit 4",
        },
        {
            "road_id": "RD-105",
            "name": "South Valley Causeway (Synthetic)",
            "u": "J4",
            "v": "J5",
            "distance_km": 2.5,
            "coords": [[12.9630, 77.5910], [12.9600, 77.5960], [12.9560, 77.6040]],
            "base_status": "SAFE" if is_baseline else ("BLOCKED" if is_extreme else "WARNING"),
            "failure_prob": 0.22 if is_baseline else (0.88 if is_extreme else 0.58),
            "vulnerability_score": 76,
            "population_impact": 7100,
            "critical_rank": 3,
            "preposition_Zone": "J5 • South Causeway Staging Point",
            "reason": "Embankment saturation warning",
        },
        {
            "road_id": "RD-106",
            "name": "West Highland Bypass (Synthetic)",
            "u": "J1",
            "v": "J3",
            "distance_km": 4.2,
            "coords": [[12.9690, 77.5850], [12.9790, 77.5820], [12.9880, 77.5850]],
            "base_status": "SAFE",
            "failure_prob": 0.08,
            "vulnerability_score": 18,
            "population_impact": 2800,
            "critical_rank": 6,
            "preposition_Zone": "J3 • Highland Emergency Depot",
            "reason": "High-elevation alternate rescue corridor",
        },
        {
            "road_id": "RD-107",
            "name": "East-Central Hospital Connector (Synthetic)",
            "u": "J6",
            "v": "J2",
            "distance_km": 2.7,
            "coords": [[12.9685, 77.6110], [12.9730, 77.6050], [12.9765, 77.5990]],
            "base_status": "SAFE",
            "failure_prob": 0.15,
            "vulnerability_score": 31,
            "population_impact": 4600,
            "critical_rank": 5,
            "preposition_Zone": "J6 • East Basin Staging Area",
            "reason": "Primary east-west hospital access link",
        },
        {
            "road_id": "RD-108",
            "name": "West-South Service Link (Synthetic)",
            "u": "J1",
            "v": "J4",
            "distance_km": 1.9,
            "coords": [[12.9690, 77.5850], [12.9660, 77.5880], [12.9630, 77.5910]],
            "base_status": "WARNING" if is_extreme else "SAFE",
            "failure_prob": 0.52 if is_extreme else 0.24,
            "vulnerability_score": 54,
            "population_impact": 4900,
            "critical_rank": 4,
            "preposition_Zone": "J1 • West Connector Depot",
            "reason": "Secondary connector to Sector 4 Lowlands",
        },
    ]

    for r in roads:
        if r["road_id"] in manual_failed:
            r["status"] = "BLOCKED"
            r["failure_prob"] = 1.0
            r["reason"] = f"SIMULATED ROAD FAILURE (Manual Stress Test) — {r['reason']}"
            r["is_manual_failure"] = True
        else:
            r["status"] = r["base_status"]
            r["is_manual_failure"] = False

    return roads


def build_city_road_graph(
    scenario_name: str,
    manual_failed_roads: set[str] | None = None,
    include_blocked: bool = False,
) -> nx.Graph:
    """
    Build a NetworkX Graph representing the synthetic city road network.
    - Nodes: City junctions (J1..J6) with lat, lon, sector, population, hospital_id.
    - Edges: Roads (RD-101..RD-108) with distance_km, risk, status, availability.
    When include_blocked=False (default for routing), BLOCKED roads are excluded
    so shortest-path calculations only use passable roads.
    """
    G = nx.Graph()
    for j_id, attrs in SYNTHETIC_JUNCTIONS.items():
        G.add_node(j_id, **attrs)

    roads = get_synthetic_roads(scenario_name, manual_failed_roads=manual_failed_roads)
    for r in roads:
        available = r["status"] != "BLOCKED"
        if not include_blocked and not available:
            continue
        # Risk-weighted travel cost: warning roads have a 1.35x penalty
        penalty = 1.0 if r["status"] == "SAFE" else (1.35 if r["status"] == "WARNING" else 999.0)
        G.add_edge(
            r["u"],
            r["v"],
            road_id=r["road_id"],
            name=r["name"],
            distance_km=r["distance_km"],
            effective_cost=round(r["distance_km"] * penalty, 2),
            risk=r["failure_prob"],
            vulnerability_score=r["vulnerability_score"],
            status=r["status"],
            available=available,
            population_impact=r["population_impact"],
        )
    return G


def evaluate_network_resilience(
    scenario_name: str,
    manual_failed_roads: set[str] | None = None,
) -> dict:
    """
    Use NetworkX to evaluate hospital accessibility and sector connectivity
    under the active scenario and any user-simulated road failures.
    """
    G_active = build_city_road_graph(
        scenario_name,
        manual_failed_roads=manual_failed_roads,
        include_blocked=False,
    )
    hospital_nodes = [
        j_id for j_id, attrs in SYNTHETIC_JUNCTIONS.items() if attrs["hospital_id"] is not None
    ]

    sector_rows = []
    isolated_population = 0
    connected_population = 0

    for j_id, attrs in SYNTHETIC_JUNCTIONS.items():
        best_hosp = None
        best_dist = float("inf")
        best_path_nodes = []
        best_road_ids = []

        for h_node in hospital_nodes:
            if nx.has_path(G_active, j_id, h_node):
                dist = nx.shortest_path_length(G_active, j_id, h_node, weight="distance_km")
                if dist < best_dist:
                    best_dist = dist
                    best_hosp = SYNTHETIC_JUNCTIONS[h_node]["hospital_id"]
                    best_path_nodes = nx.shortest_path(G_active, j_id, h_node, weight="distance_km")

        if best_hosp is not None:
            for idx in range(len(best_path_nodes) - 1):
                edge_data = G_active.get_edge_data(best_path_nodes[idx], best_path_nodes[idx + 1])
                if edge_data and "road_id" in edge_data:
                    best_road_ids.append(edge_data["road_id"])
            route_str = (
                "Direct (At Hospital Hub)"
                if len(best_road_ids) == 0
                else " → ".join(best_road_ids)
            )
            access_status = "ACCESSIBLE"
            connected_population += attrs["population"]
        else:
            route_str = "NO PASSABLE ROUTE (ISOLATED)"
            access_status = "ISOLATED"
            isolated_population += attrs["population"]

        sector_rows.append(
            {
                "Junction": j_id,
                "Sector": attrs["sector"],
                "Population": attrs["population"],
                "Hospital Access": access_status,
                "Nearest Reachable Hospital": best_hosp or "NONE",
                "Shortest Safe Distance (km)": round(best_dist, 2) if best_hosp else None,
                "Active Rescue Corridor": route_str,
            }
        )

    total_pop = connected_population + isolated_population
    access_pct = round((connected_population / total_pop) * 100, 1) if total_pop > 0 else 0.0

    return {
        "sector_df": pd.DataFrame(sector_rows),
        "connected_population": connected_population,
        "isolated_population": isolated_population,
        "hospital_access_pct": access_pct,
        "num_connected_components": nx.number_connected_components(G_active),
        "is_fully_connected": nx.is_connected(G_active),
    }


def get_synthetic_incidents(scenario_name: str) -> pd.DataFrame:
    """Return initial synthetic emergency incidents for the map and tables."""
    incidents = [
        {
            "incident_id": "INC-901",
            "title": "Submerged Commuter Bus at Sector 4 Underpass",
            "type": "Flash Flood Entrapment",
            "urgency": "CRITICAL",
            "confidence": 0.94,
            "lat": 12.9682,
            "lon": 77.5932,
            "sector": "Sector 4 Lowlands",
            "reported_at": "17:42",
            "verified": True,
            "duplicate_warning": "Clear (Unique Image)",
        },
        {
            "incident_id": "INC-902",
            "title": "Substation Water Ingress Near Riverfront Bridge",
            "type": "Infrastructure Failure",
            "urgency": "CRITICAL",
            "confidence": 0.89,
            "lat": 12.9712,
            "lon": 77.5940,
            "sector": "Central Riverfront",
            "reported_at": "17:46",
            "verified": True,
            "duplicate_warning": "Clear (Unique Image)",
        },
        {
            "incident_id": "INC-903",
            "title": "Elderly Care Facility Ground Floor Flooding",
            "type": "Medical Evacuation",
            "urgency": "CRITICAL",
            "confidence": 0.91,
            "lat": 12.9598,
            "lon": 77.5965,
            "sector": "South Valley",
            "reported_at": "17:49",
            "verified": True,
            "duplicate_warning": "Clear (Unique Image)",
        },
        {
            "incident_id": "INC-904",
            "title": "Fallen Tree Blocking Secondary Access Lane",
            "type": "Road Obstruction",
            "urgency": "WARNING",
            "confidence": 0.78,
            "lat": 12.9750,
            "lon": 77.5875,
            "sector": "West Connector",
            "reported_at": "17:51",
            "verified": True,
            "duplicate_warning": "Clear (Unique Image)",
        },
        {
            "incident_id": "INC-905",
            "title": "Unverified Social Media Photo of Dam Breach",
            "type": "Misinformation / Duplicate Check",
            "urgency": "WARNING",
            "confidence": 0.28,
            "lat": 12.9820,
            "lon": 77.6060,
            "sector": "East Basin",
            "reported_at": "17:54",
            "verified": False,
            "duplicate_warning": "⚠️ FLAGGED: Recycled 2023 Flood Photo",
        },
    ]
    return pd.DataFrame(incidents)


def get_precautions_by_disaster_type() -> dict[str, list[str]]:
    """Return operational precautions & field protocols for Section 3 (Live Response)."""
    return {
        "Flash Flood Entrapment": [
            "Deploy shallow-draft inflatable boat unit (RESCUE-ALPHA); do not send standard ambulances into water > 0.4m.",
            "Coordinate upstream storm-drain gate throttling before entering underpass.",
            "Route medical evacuees to HOSP-01 via elevated corridors (RD-106 / RD-102).",
        ],
        "Infrastructure Failure": [
            "Isolate electrical feeder lines within 250m radius before deploying clearance crews.",
            "Activate backup diesel generators at nearest hospital hub.",
            "Mark adjacent road corridor as WARNING/BLOCKED until structural inspection completes.",
        ],
        "Medical Evacuation": [
            "Prioritize Advanced Life Support (ALS) units with portable oxygen and triage kits.",
            "Verify destination hospital free ICU bed count before dispatch.",
            "Use NetworkX shortest safe route avoiding all BLOCKED road segments.",
        ],
        "Road Obstruction": [
            "Dispatch Heavy Engineering & Clearance Team (RESCUE-BRAVO) with hydraulic saws.",
            "Broadcast automated detour advisory to all active ambulances in sector.",
        ],
    }


def get_critical_alerts(scenario_name: str) -> list[dict]:
    """Return synthetic critical alerts for the Overview panel."""
    return [
        {
            "severity": "CRITICAL",
            "time": "17:54",
            "code": "ALT-01",
            "title": "RD-103 Sector 4 Underpass Completely Impassable",
            "detail": "Simulated sensor depth > 2.1m. Automatic rerouting via RD-106 West Highland Bypass activated.",
        },
        {
            "severity": "CRITICAL",
            "time": "17:51",
            "code": "ALT-02",
            "title": "High-Priority Medical Evacuation at South Valley (INC-903)",
            "detail": "Evidence confidence 91%. Assigned unit AMB-104 via East Ring Expressway.",
        },
        {
            "severity": "WARNING",
            "time": "17:48",
            "code": "ALT-03",
            "title": "Duplicate / Recycled Flood Image Flagged (INC-905)",
            "detail": "Evidence module flagged low confidence (28%) — human verification required before dispatch.",
        },
        {
            "severity": "WARNING",
            "time": "17:44",
            "code": "ALT-04",
            "title": "South Riverfront General Hospital Approaching ICU Capacity",
            "detail": "Only 4 free ICU beds remaining. Diverting non-critical cases to HOSP-01 Central Trauma.",
        },
    ]


def get_recent_activity() -> pd.DataFrame:
    """Return synthetic recent system activity following OBSERVE -> VERIFY workflow."""
    rows = [
        {
            "Timestamp": "17:55:10",
            "Stage": "VERIFY",
            "Module": "Member 2 • Evidence",
            "Event": "Flagged INC-905 image as probable duplicate (Confidence: 0.28)",
            "Status": "Warning",
        },
        {
            "Timestamp": "17:53:42",
            "Stage": "OPTIMIZE",
            "Module": "Member 3 • Decision",
            "Event": "Rerouted AMB-104 around blocked RD-103 to reach INC-903",
            "Status": "Resolved",
        },
        {
            "Timestamp": "17:50:19",
            "Stage": "SIMULATE",
            "Module": "Member 3 • Digital Twin",
            "Event": "Updated +30 min flood projection for Riverfront Arterial Bridge",
            "Status": "Active",
        },
        {
            "Timestamp": "17:47:05",
            "Stage": "ESTIMATE",
            "Module": "Member 1 • Resilience",
            "Event": "Recalculated failure probability for RD-101 (0.92) & hospital isolation risk",
            "Status": "Critical",
        },
        {
            "Timestamp": "17:42:30",
            "Stage": "OBSERVE",
            "Module": "Member 2 • Evidence",
            "Event": "Ingested emergency report INC-901 (Sector 4 Underpass entrapment)",
            "Status": "Critical",
        },
    ]
    return pd.DataFrame(rows)
