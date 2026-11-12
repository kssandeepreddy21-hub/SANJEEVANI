"""Bridge converting Member 2 incident reports into Member 3 OSM routing/allocation inputs."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import networkx as nx
import pandas as pd

from sanjeevani.graph_adapter import nearest_node

URGENCY_TO_PRIORITY = {
    "CRITICAL": 3.0,
    "HIGH": 2.5,
    "WARNING": 2.0,
    "LOW": 1.0,
}

DEFAULT_URGENCY_POPULATION = {
    "CRITICAL": 1200,
    "HIGH": 800,
    "WARNING": 500,
    "LOW": 250,
}


def _is_flagged_duplicate(incident: Mapping[str, Any]) -> bool:
    dup_text = str(incident.get("duplicate_warning", "")).strip().upper()
    return "FLAGGED" in dup_text or "DUPLICATE" in dup_text and "CLEAR" not in dup_text


def _parse_finite_coord(val: Any) -> float | None:
    if val is None or isinstance(val, bool):
        return None
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def incident_to_osm_node(incident: Mapping[str, Any], graph: nx.Graph) -> dict[str, Any]:
    """
    Snap a Member 2 incident dict (with `lat` and `lon`) to the closest node in `graph`.
    """
    lat = _parse_finite_coord(incident.get("lat"))
    lon = _parse_finite_coord(incident.get("lon"))
    node_id = None
    snap_dist_m = None

    if lat is not None and lon is not None:
        node_id, snap_dist_m = nearest_node(graph, lat, lon)

    urgency = str(incident.get("urgency", "WARNING")).strip().upper()
    return {
        "incident_id": str(incident.get("incident_id", "")),
        "node": node_id,
        "snap_distance_m": snap_dist_m,
        "lat": lat,
        "lon": lon,
        "urgency": urgency,
        "confidence": float(incident.get("confidence", 0.0)),
        "verified": bool(incident.get("verified", False)),
        "duplicate_warning": str(incident.get("duplicate_warning", "Clear")),
        "disaster_type": str(incident.get("type", "Unknown")),
    }


def incidents_to_affected_locations(
    incidents: pd.DataFrame | Sequence[Mapping[str, Any]],
    graph: nx.Graph,
    default_population_map: Mapping[str, int] | None = None,
    require_verified: bool = True,
) -> dict[str, Any]:
    """
    Convert Member 2 incident records into Member 3's `affected_locations` list
    for `allocate_emergency_resources()` / `compare_rescue_strategies()`.

    Unverified or duplicate-flagged incidents are held aside in `held_incidents`
    when `require_verified=True` (matching RESQ-AI safety behaviour).
    """
    records: list[Mapping[str, Any]]
    if isinstance(incidents, pd.DataFrame):
        records = incidents.to_dict(orient="records")
    else:
        records = list(incidents)

    pop_overrides = dict(default_population_map or {})
    affected_locations: list[dict[str, Any]] = []
    held_incidents: list[dict[str, Any]] = []
    unmapped_incidents: list[dict[str, Any]] = []

    for inc in records:
        snapped = incident_to_osm_node(inc, graph)
        is_verified = snapped["verified"]
        is_dup = _is_flagged_duplicate(inc)

        if require_verified and (not is_verified or is_dup):
            held_incidents.append(
                {
                    **snapped,
                    "hold_reason": (
                        "Duplicate/recycled evidence warning"
                        if is_dup
                        else "Pending operator verification"
                    ),
                }
            )
            continue

        if snapped["node"] is None:
            unmapped_incidents.append(
                {**snapped, "unmapped_reason": "Missing coordinates or graph has no nodes."}
            )
            continue

        inc_id = snapped["incident_id"]
        urgency = snapped["urgency"]
        priority = URGENCY_TO_PRIORITY.get(urgency, 2.0)

        raw_pop = inc.get("affected_population", inc.get("population"))
        if raw_pop is not None:
            pop_val = int(raw_pop)
            is_synth_pop = bool(inc.get("is_synthetic_population", True))
        elif inc_id in pop_overrides:
            pop_val = int(pop_overrides[inc_id])
            is_synth_pop = True
        else:
            pop_val = DEFAULT_URGENCY_POPULATION.get(urgency, 500)
            is_synth_pop = True

        affected_locations.append(
            {
                "location_id": inc_id,
                "name": str(inc.get("title", inc.get("sector", inc_id))),
                "node": snapped["node"],
                "snap_distance_m": snapped["snap_distance_m"],
                "priority": priority,
                "affected_population": pop_val,
                "is_synthetic_population": is_synth_pop,
                "urgency": urgency,
                "confidence": snapped["confidence"],
                "verified": is_verified,
            }
        )

    return {
        "affected_locations": affected_locations,
        "held_incidents": held_incidents,
        "unmapped_incidents": unmapped_incidents,
        "is_population_synthetic": True,
        "data_label": "Synthetic Scenario Assumption",
    }
