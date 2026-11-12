"""Build a compact static Central Bengaluru Corridor map snapshot for RESQ-AI.

Reads the external Bengaluru OSM graph (configured via `RESQ_AI_DATA_DIR`) and
optionally the `.osm.pbf` facility extract to export lightweight `< 500 KB`
JSON coordinates for the RESQ-AI dashboard so Folium maps render real roads,
underpasses, facilities, and rescue routes cleanly even without the 940 MB GraphML.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Ensure repo root is importable when running as `python scripts/build_corridor_map_snapshot.py`
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sanjeevani.cascading_failure import extract_emergency_facilities, snap_facilities_to_graph
from sanjeevani.config import LOCAL_DATA_DIR, get_pbf_path, osm_data_available
from sanjeevani.decision_member3 import find_alternative_route, find_shortest_safe_route
from sanjeevani.flood_vulnerability import annotate_graph_vulnerability
from sanjeevani.osm_data_loader import DEFAULT_CORRIDOR_BBOX, load_corridor, load_dashboard_payload
from sanjeevani.twin_member3 import simulate_rainfall

SNAPSHOT_FILENAME = "member3_corridor_map_snapshot.json"
DEFAULT_OUTPUT_PATH = LOCAL_DATA_DIR / "processed" / SNAPSHOT_FILENAME

ARTERIAL_HIGHWAYS = {"trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link"}
FACILITY_CATEGORY_CAPS = {
    "hospitals": 60,
    "fire_stations": 25,
    "police_stations": 40,
    "suitable_shelters": 25,
}


def _round_coord(val: Any) -> float:
    return round(float(val), 6)


def _node_lat_lon(graph: Any, node_id: Any) -> tuple[float, float] | None:
    if node_id not in graph:
        return None
    nd = graph.nodes[node_id]
    lat = nd.get("y", nd.get("lat"))
    lon = nd.get("x", nd.get("lon"))
    if lat is None or lon is None:
        return None
    return _round_coord(lat), _round_coord(lon)


def _edge_segment_dict(
    graph: Any,
    u: Any,
    v: Any,
    data: dict[str, Any],
) -> dict[str, Any] | None:
    p1 = _node_lat_lon(graph, u)
    p2 = _node_lat_lon(graph, v)
    if p1 is None or p2 is None:
        return None
    return {
        "road_id": str(data.get("road_id", f"{u}-{v}")),
        "name": str(data.get("name", "") or "").strip(),
        "highway": str(data.get("highway", "unknown")),
        "vulnerability": round(float(data.get("vulnerability_score", data.get("flood_sensitivity", 0.0))), 3),
        "risk_category": str(data.get("risk_category", "MODERATE")),
        "condition": str(data.get("condition", "OPEN")),
        "bridge": str(data.get("bridge", "no")),
        "tunnel": str(data.get("tunnel", "no")),
        "length_m": round(float(data.get("length_m", 0.0)), 1),
        "coords": [[p1[0], p1[1]], [p2[0], p2[1]]],
    }


def _in_bbox(lat: float | None, lon: float | None, bbox: tuple[float, float, float, float]) -> bool:
    if lat is None or lon is None:
        return False
    min_lon, min_lat, max_lon, max_lat = bbox
    return min_lon <= float(lon) <= max_lon and min_lat <= float(lat) <= max_lat


def build_corridor_map_snapshot(
    output_path: Path | str = DEFAULT_OUTPUT_PATH,
    bbox: tuple[float, float, float, float] = DEFAULT_CORRIDOR_BBOX,
    max_arterial: int = 250,
    max_vulnerable: int = 250,
) -> dict[str, Any]:
    """Generate and persist the compact Central Bengaluru Corridor geo-snapshot."""
    if not osm_data_available():
        raise FileNotFoundError(
            "Bengaluru OSM graph/cache not available. Set RESQ_AI_DATA_DIR before building snapshot."
        )

    payload = load_dashboard_payload()
    corridor = load_corridor(bbox=bbox)
    vuln_graph = annotate_graph_vulnerability(corridor)
    sim_graph, _ = simulate_rainfall(vuln_graph, 95.0)  # Matches payload T+60 corridor scenario

    phase8_recs = payload.get("phase8_active_observation_plan", {}).get("recommendations", [])
    phase8_road_ids = {str(item.get("road_id", "")) for item in phase8_recs}

    # Deduplicate edges into undirected road-way segments to keep payload crisp
    seen_arterial: set[tuple[str, tuple[str, str]]] = set()
    arterial_candidates: list[dict[str, Any]] = []
    seen_vuln: set[tuple[str, tuple[str, str]]] = set()
    vulnerable_candidates: list[tuple[tuple[int, int, float, int], dict[str, Any]]] = []
    way_best: dict[str, dict[str, Any]] = {}

    highway_rank = {
        "trunk": 6,
        "primary": 5,
        "secondary": 4,
        "trunk_link": 3,
        "primary_link": 3,
        "secondary_link": 2,
        "tertiary": 2,
    }

    for u, v, data in sim_graph.edges(data=True):
        road_id = str(data.get("road_id", f"{u}-{v}"))
        pair = (min(str(u), str(v)), max(str(u), str(v)))
        hw = str(data.get("highway", "unknown"))
        cond = str(data.get("condition", "OPEN"))
        risk = str(data.get("risk_category", "MODERATE"))
        vuln = float(data.get("vulnerability_score", data.get("flood_sensitivity", 0.0)))
        is_tunnel = str(data.get("tunnel", "no")).lower() not in ("no", "unknown", "")
        is_bridge = str(data.get("bridge", "no")).lower() not in ("no", "unknown", "")

        seg = _edge_segment_dict(sim_graph, u, v, data)
        if seg is None:
            continue

        # Track top vulnerable road ways summary
        existing_way = way_best.get(road_id)
        if existing_way is None or vuln > existing_way["vulnerability_score"] or (
            vuln == existing_way["vulnerability_score"] and seg["name"] and not existing_way["name"]
        ):
            way_best[road_id] = {
                "road_id": road_id,
                "name": seg["name"] or f"OSM Way {road_id}",
                "highway": hw,
                "vulnerability_score": round(vuln, 4),
                "risk_category": risk,
                "t60_condition": cond,
                "is_tunnel": is_tunnel,
                "is_bridge": is_bridge,
                "length_m": seg["length_m"],
                "lat": _round_coord((seg["coords"][0][0] + seg["coords"][1][0]) / 2.0),
                "lon": _round_coord((seg["coords"][0][1] + seg["coords"][1][1]) / 2.0),
            }

        if hw in ARTERIAL_HIGHWAYS:
            key = (road_id, pair)
            if key not in seen_arterial:
                seen_arterial.add(key)
                arterial_candidates.append(seg)

        is_interesting = (
            cond == "BLOCKED"
            or road_id in phase8_road_ids
            or risk == "CRITICAL"
            or (hw in ARTERIAL_HIGHWAYS and cond == "AT RISK")
            or is_tunnel
        )
        if is_interesting:
            key = (road_id, pair)
            if key not in seen_vuln:
                seen_vuln.add(key)
                priority = (
                    2 if cond == "BLOCKED" else (1 if cond == "AT RISK" else 0),
                    1 if (road_id in phase8_road_ids or is_tunnel) else 0,
                    vuln,
                    highway_rank.get(hw, 0),
                )
                vulnerable_candidates.append((priority, seg))

    arterial_candidates.sort(
        key=lambda item: (highway_rank.get(item["highway"], 0), item["length_m"]),
        reverse=True,
    )
    arterial_segments = arterial_candidates[:max_arterial]

    vulnerable_candidates.sort(key=lambda item: item[0], reverse=True)
    vulnerable_segments = [item[1] for item in vulnerable_candidates[:max_vulnerable]]

    # Top vulnerable ways table (for UI Section 2)
    top_ways_sorted = sorted(
        way_best.values(),
        key=lambda w: (
            1 if w["t60_condition"] == "BLOCKED" else 0,
            w["vulnerability_score"],
            1 if w["is_tunnel"] else 0,
            1 if w["highway"] in ARTERIAL_HIGHWAYS else 0,
        ),
        reverse=True,
    )[:25]

    # Phase 5 route polylines
    phase5 = payload.get("phase5_rescue_routing", {})
    origin_node = str(phase5.get("dispatch_origin_node", ""))
    target_hospital = phase5.get("target_hospital", {})
    dest_node = str(target_hospital.get("nearest_node", ""))

    primary_coords: list[list[float]] = []
    alternative_coords: list[list[float]] = []
    if origin_node in sim_graph and dest_node in sim_graph:
        primary_res = find_shortest_safe_route(
            sim_graph, origin_node, dest_node, optimize_for="time"
        )
        if primary_res.get("reachable"):
            for nid in primary_res.get("nodes", []):
                pt = _node_lat_lon(sim_graph, nid)
                if pt is not None:
                    primary_coords.append([pt[0], pt[1]])

        alt_bundle = find_alternative_route(
            sim_graph,
            origin_node,
            dest_node,
            primary_route=primary_res,
            optimize_for="time",
        )
        alt_res = alt_bundle.get("alternative_route", {})
        if alt_res.get("reachable"):
            for nid in alt_res.get("nodes", []):
                pt = _node_lat_lon(sim_graph, nid)
                if pt is not None:
                    alternative_coords.append([pt[0], pt[1]])

    # Phase 8 active observation locations
    observation_points: list[dict[str, Any]] = []
    for rec in phase8_recs:
        p1 = _node_lat_lon(sim_graph, str(rec.get("u", "")))
        p2 = _node_lat_lon(sim_graph, str(rec.get("v", "")))
        if p1 is not None and p2 is not None:
            observation_points.append(
                {
                    "rank": rec.get("rank"),
                    "road_id": str(rec.get("road_id", "")),
                    "name": str(rec.get("name", "") or "").strip() or f"Way {rec.get('road_id')}",
                    "highway": rec.get("highway", "unknown"),
                    "condition": rec.get("condition", "AT RISK"),
                    "observation_priority_score": rec.get("observation_priority_score"),
                    "lat": _round_coord((p1[0] + p2[0]) / 2.0),
                    "lon": _round_coord((p1[1] + p2[1]) / 2.0),
                    "coords": [[p1[0], p1[1]], [p2[0], p2[1]]],
                }
            )

    # Deduplicated Central Corridor facilities from PBF (capped <= 150 markers total)
    facilities_out: list[dict[str, Any]] = []
    pbf_path = get_pbf_path()
    if pbf_path.exists():
        extracted = extract_emergency_facilities(str(pbf_path))
        raw_cats = extracted.get("categories", {})
        bbox_filtered: dict[str, list[dict[str, Any]]] = {}
        for cat in FACILITY_CATEGORY_CAPS:
            items = [
                f for f in raw_cats.get(cat, []) if _in_bbox(f.get("lat"), f.get("lon"), bbox)
            ]
            # Named facilities first so landmarks show clearly on the map
            items.sort(key=lambda f: (1 if f.get("is_named") else 0, str(f.get("name", ""))), reverse=True)
            bbox_filtered[cat] = items[: FACILITY_CATEGORY_CAPS[cat]]

        snapped = snap_facilities_to_graph(bbox_filtered, sim_graph)
        for cat in FACILITY_CATEGORY_CAPS:
            for item in snapped.get(cat, []):
                facilities_out.append(
                    {
                        "facility_id": item.get("facility_id"),
                        "category": cat,
                        "name": item.get("name"),
                        "is_named": bool(item.get("is_named", False)),
                        "lat": _round_coord(item["lat"]),
                        "lon": _round_coord(item["lon"]),
                        "nearest_node": str(item.get("nearest_node")) if item.get("nearest_node") is not None else None,
                        "snap_distance_m": round(float(item.get("snap_distance_m", 0.0)), 2)
                        if item.get("snap_distance_m") is not None
                        else None,
                        "verification_status": item.get("verification_status", "unverified_osm_record"),
                    }
                )
    elif target_hospital.get("lat") and target_hospital.get("lon"):
        facilities_out.append(
            {
                "facility_id": target_hospital.get("facility_id", "way:38536360"),
                "category": "hospitals",
                "name": target_hospital.get("name", "K C General Hospital"),
                "is_named": True,
                "lat": _round_coord(target_hospital["lat"]),
                "lon": _round_coord(target_hospital["lon"]),
                "nearest_node": dest_node or None,
                "snap_distance_m": target_hospital.get("snap_distance_m"),
                "verification_status": target_hospital.get("verification_status", "unverified_osm_record"),
            }
        )

    origin_pt = _node_lat_lon(sim_graph, origin_node)
    snapshot: dict[str, Any] = {
        "metadata": {
            "city": "Bengaluru, Karnataka, India",
            "corridor_bbox": list(bbox),
            "scenario": "T+60 Central Corridor Heavy Rainfall (95.0 mm/hr)",
            "data_source": "OpenStreetMap Corridor Extract (RESQ-AI Snapshot)",
            "arterial_segments_count": len(arterial_segments),
            "vulnerable_segments_count": len(vulnerable_segments),
            "facilities_count": len(facilities_out),
        },
        "arterial_segments": arterial_segments,
        "vulnerable_segments": vulnerable_segments,
        "top_vulnerable_roads": top_ways_sorted,
        "facilities": facilities_out,
        "routes": {
            "origin_node": origin_node,
            "origin_coords": list(origin_pt) if origin_pt else None,
            "target_hospital": target_hospital,
            "primary_coords": primary_coords,
            "alternative_coords": alternative_coords,
        },
        "phase8_observations": observation_points,
    }

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, separators=(",", ":"))
    return snapshot


def main() -> None:
    snapshot = build_corridor_map_snapshot()
    size_kb = DEFAULT_OUTPUT_PATH.stat().st_size / 1024.0
    print(f"Snapshot written: {DEFAULT_OUTPUT_PATH} ({size_kb:.1f} KB)")
    print("Metadata:", json.dumps(snapshot["metadata"], indent=2))
    print(
        f"Routes -> primary points: {len(snapshot['routes']['primary_coords'])}, "
        f"alternative points: {len(snapshot['routes']['alternative_coords'])}, "
        f"phase8 obs: {len(snapshot['phase8_observations'])}"
    )


if __name__ == "__main__":
    main()
