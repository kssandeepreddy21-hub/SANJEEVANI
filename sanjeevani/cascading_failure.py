"""
Phase 4: Cascading Failure Analysis, Facility Accessibility, and Human Impact.

Key Safeguards:
1. Distinguishes unique hospitals, fire stations, police stations, and suitable
   emergency shelters into separate categories.
2. Excludes non-emergency shelters such as bus shelters (`public_transport`),
   gazebos (`gazebo`), picnic shelters (`picnic_shelter`), and pergolas (`pergola`).
3. Avoids double-counting across OSM relations, ways, and duplicate POI nodes.
4. Explicitly flags all OSM facility records as `unverified_osm_record`.
5. Separately reports completely inaccessible facilities versus reachable
   facilities experiencing increased travel times/detours.
6. Explicitly distinguishes missing/unavailable population data from synthetic
   scenario inputs.
"""

from collections import defaultdict
from pathlib import Path

import networkx as nx
from pyproj import Geod

from sanjeevani.config import get_pbf_path


EXCLUDED_SHELTER_TYPES = {
    "gazebo",
    "public_transport",
    "picnic_shelter",
    "pergola",
    "sun_shelter",
    "field_shelter",
    "rock_shelter",
    "lean_to",
}

FACILITY_CATEGORIES = (
    "hospitals",
    "fire_stations",
    "police_stations",
    "suitable_shelters",
)


def _create_osm_facility_collector():
    """Lazily import pyosmium and construct the PBF handler only when reading PBF files."""
    import osmium

    class _OSMFacilityCollector(osmium.SimpleHandler):
        """
        Collects raw OSM nodes, ways, and relations for emergency facilities
        while recording member references to prevent double-counting.
        """

        def __init__(self):
            super().__init__()
            self.nodes = []
            self.ways = []
            self.relations = []
            self.way_node_refs = defaultdict(set)
            self.rel_member_refs = defaultdict(set)
            self.excluded_non_emergency_shelters = 0

        def _classify(self, tags):
            amenity = tags.get("amenity", "").strip().lower()
            social = tags.get("social_facility", "").strip().lower()
            emergency = tags.get("emergency", "").strip().lower()
            shelter_type = tags.get("shelter_type", "").strip().lower()

            if amenity == "hospital":
                return "hospitals"
            if amenity == "fire_station":
                return "fire_stations"
            if amenity == "police":
                return "police_stations"

            if amenity == "shelter" or social == "shelter" or emergency == "shelter":
                if shelter_type in EXCLUDED_SHELTER_TYPES:
                    self.excluded_non_emergency_shelters += 1
                    return None
                return "suitable_shelters"

            return None

        def node(self, n):
            category = self._classify(n.tags)
            if category and n.location.valid():
                self.nodes.append(
                    {
                        "osm_type": "node",
                        "osm_id": str(n.id),
                        "raw_id": n.id,
                        "category": category,
                        "name": n.tags.get("name", "").strip(),
                        "shelter_type": n.tags.get("shelter_type", "unspecified"),
                        "lon": float(n.location.lon),
                        "lat": float(n.location.lat),
                    }
                )

        def way(self, w):
            category = self._classify(w.tags)
            if category:
                coords = [
                    (float(nd.location.lon), float(nd.location.lat))
                    for nd in w.nodes
                    if nd.location.valid()
                ]
                nrefs = {nd.ref for nd in w.nodes}
                self.way_node_refs[category].update(nrefs)
                if coords:
                    avg_lon = sum(c[0] for c in coords) / len(coords)
                    avg_lat = sum(c[1] for c in coords) / len(coords)
                    self.ways.append(
                        {
                            "osm_type": "way",
                            "osm_id": str(w.id),
                            "raw_id": w.id,
                            "category": category,
                            "name": w.tags.get("name", "").strip(),
                            "shelter_type": w.tags.get("shelter_type", "unspecified"),
                            "lon": avg_lon,
                            "lat": avg_lat,
                        }
                    )

        def relation(self, r):
            category = self._classify(r.tags)
            if category:
                mrefs = {(m.type, m.ref) for m in r.members}
                self.rel_member_refs[category].update(mrefs)
                self.relations.append(
                    {
                        "osm_type": "relation",
                        "osm_id": str(r.id),
                        "raw_id": r.id,
                        "category": category,
                        "name": r.tags.get("name", "").strip(),
                        "shelter_type": r.tags.get("shelter_type", "unspecified"),
                        "members": mrefs,
                    }
                )

    return _OSMFacilityCollector()


def snap_facilities_to_graph(facilities_by_category, graph, max_snap_distance_m=500.0):
    """
    Snap facility coordinates (lon, lat) to the nearest road graph node using a
    spatial grid index (~0.01 deg cells) so large graphs (437k nodes) are
    indexed in ~1 second without brute-force search.
    """

    cell_size = 0.01  # ~1.1 km grid cell
    grid = defaultdict(list)
    nodes_with_coords = 0

    for node_id, ndata in graph.nodes(data=True):
        lon = ndata.get("x", ndata.get("lon"))
        lat = ndata.get("y", ndata.get("lat"))
        if lon is None or lat is None:
            continue
        lon_f = float(lon)
        lat_f = float(lat)
        gx = int(lon_f // cell_size)
        gy = int(lat_f // cell_size)
        grid[(gx, gy)].append((node_id, lon_f, lat_f))
        nodes_with_coords += 1

    if nodes_with_coords == 0:
        return facilities_by_category

    geod = Geod(ellps="WGS84")

    for category, items in facilities_by_category.items():
        for fac in items:
            flon = fac.get("lon")
            flat = fac.get("lat")
            if flon is None or flat is None:
                fac["nearest_node"] = None
                fac["snap_distance_m"] = None
                continue

            gx = int(flon // cell_size)
            gy = int(flat // cell_size)

            candidates = []
            for radius in (1, 2, 4):
                for dx in range(-radius, radius + 1):
                    for dy in range(-radius, radius + 1):
                        candidates.extend(grid.get((gx + dx, gy + dy), ()))
                if candidates:
                    break

            best_node = None
            best_dist = float("inf")
            for nid, nlon, nlat in candidates:
                # Fast degree filter before geodesic calculation
                if abs(flon - nlon) > 0.02 or abs(flat - nlat) > 0.02:
                    continue
                _, _, dist = geod.inv(flon, flat, nlon, nlat)
                if dist < best_dist:
                    best_dist = dist
                    best_node = nid

            if best_node is not None and best_dist <= max_snap_distance_m:
                fac["nearest_node"] = best_node
                fac["snap_distance_m"] = round(float(best_dist), 2)
            else:
                fac["nearest_node"] = None
                fac["snap_distance_m"] = None

    return facilities_by_category


def extract_emergency_facilities(
    pbf_path=None,
    graph=None,
):
    """
    Extract and deduplicate emergency facilities from the local OSM PBF file.

    Returns a dictionary containing:
    - categories: dict mapping each of the 4 facility categories
      ("hospitals", "fire_stations", "police_stations", "suitable_shelters")
      to its list of unique facility dicts
    - counts: summary counts per category (raw vs deduplicated)
    - excluded_non_emergency_shelters: count of excluded gazebos/bus/picnic shelters
    - verification_disclaimer: explicit statement that OSM records are unverified
    """

    pbf_file = Path(pbf_path) if pbf_path is not None else get_pbf_path()
    if not pbf_file.exists():
        raise FileNotFoundError(
            f"PBF file not found: {pbf_file}. "
            "Set RESQ_AI_DATA_DIR to the external Bengaluru data directory if stored outside the repo."
        )

    collector = _create_osm_facility_collector()
    collector.apply_file(str(pbf_file), locations=True)
    geod = Geod(ellps="WGS84")

    way_by_id = {w["raw_id"]: (w["lon"], w["lat"]) for w in collector.ways}
    node_by_id = {n["raw_id"]: (n["lon"], n["lat"]) for n in collector.nodes}

    categories = {cat: [] for cat in FACILITY_CATEGORIES}
    counts_summary = {}

    for cat in FACILITY_CATEGORIES:
        cat_nodes = [n for n in collector.nodes if n["category"] == cat]
        cat_ways = [w for w in collector.ways if w["category"] == cat]
        cat_rels = [r for r in collector.relations if r["category"] == cat]

        rel_way_ids = {
            ref for (mtype, ref) in collector.rel_member_refs[cat] if mtype == "w"
        }
        rel_node_ids = {
            ref for (mtype, ref) in collector.rel_member_refs[cat] if mtype == "n"
        }
        way_vertex_ids = collector.way_node_refs[cat]

        filtered_ways = [w for w in cat_ways if w["raw_id"] not in rel_way_ids]
        filtered_nodes = [
            n
            for n in cat_nodes
            if n["raw_id"] not in rel_node_ids and n["raw_id"] not in way_vertex_ids
        ]

        # Estimate relation centroids from member ways/nodes
        valid_rels = []
        for r in cat_rels:
            mcoords = []
            for mtype, ref in r["members"]:
                if mtype == "w" and ref in way_by_id:
                    mcoords.append(way_by_id[ref])
                elif mtype == "n" and ref in node_by_id:
                    mcoords.append(node_by_id[ref])
            if mcoords:
                r["lon"] = sum(c[0] for c in mcoords) / len(mcoords)
                r["lat"] = sum(c[1] for c in mcoords) / len(mcoords)
            else:
                r["lon"] = None
                r["lat"] = None
            valid_rels.append(r)

        # Deduplicate POI nodes that duplicate a way or relation footprint
        footprints = filtered_ways + [
            r for r in valid_rels if r["lon"] is not None and r["lat"] is not None
        ]
        dedup_nodes = []
        dup_poi_removed = 0

        for n in filtered_nodes:
            is_dup = False
            n_name = n["name"].lower()
            for fp in footprints:
                if abs(n["lon"] - fp["lon"]) > 0.003 or abs(n["lat"] - fp["lat"]) > 0.003:
                    continue
                _, _, dist = geod.inv(n["lon"], n["lat"], fp["lon"], fp["lat"])
                fp_name = fp["name"].lower()
                if (n_name and fp_name and n_name == fp_name and dist <= 250.0) or dist <= 40.0:
                    is_dup = True
                    break
            if is_dup:
                dup_poi_removed += 1
            else:
                dedup_nodes.append(n)

        combined = valid_rels + filtered_ways + dedup_nodes
        formatted_list = []
        for item in combined:
            formatted_list.append(
                {
                    "facility_id": f"{item['osm_type']}:{item['osm_id']}",
                    "osm_type": item["osm_type"],
                    "osm_id": item["osm_id"],
                    "category": cat,
                    "name": item["name"] or f"Unnamed {cat[:-1].replace('_', ' ').title()}",
                    "is_named": bool(item["name"]),
                    "lon": item.get("lon"),
                    "lat": item.get("lat"),
                    "nearest_node": None,
                    "snap_distance_m": None,
                    "verification_status": "unverified_osm_record",
                    "data_source": "OpenStreetMap_PBF",
                }
            )

        categories[cat] = formatted_list
        counts_summary[cat] = {
            "raw_nodes": len(cat_nodes),
            "raw_ways": len(cat_ways),
            "raw_relations": len(cat_rels),
            "duplicate_poi_nodes_removed": dup_poi_removed,
            "unique_facilities": len(formatted_list),
            "named_facilities": sum(1 for x in formatted_list if x["is_named"]),
            "unnamed_facilities": sum(1 for x in formatted_list if not x["is_named"]),
        }

    if graph is not None:
        snap_facilities_to_graph(categories, graph)

    return {
        "categories": categories,
        "counts": counts_summary,
        "excluded_non_emergency_shelters": collector.excluded_non_emergency_shelters,
        "verification_disclaimer": (
            "All facility records are extracted from crowd-sourced OpenStreetMap data "
            "and have NOT been independently verified for operational bed/shelter capacity."
        ),
    }


def simulate_road_failures(city_graph, failed_roads=None, include_blocked_condition=True):
    """
    Simulate single or multiple road failures without modifying `city_graph`.

    `failed_roads` can be:
    - None (uses only edges already marked `available=False` or `condition='BLOCKED'`)
    - A single road_id string (e.g., "R1" or "4354938")
    - A single edge tuple `(u, v)` or `(u, v, key)`
    - An iterable of road_id strings and/or `(u, v)` edge tuples

    Returns `(degraded_graph, failure_report)` where `degraded_graph` is a copy
    of `city_graph` with failed edges marked `available=False`, `condition="BLOCKED"`,
    `failed=True`, and `passable_graph` in `failure_report` has blocked edges removed
    for connectivity/routing analysis.
    """

    failed_road_ids = set()
    failed_edge_pairs = set()

    if failed_roads is not None:
        if isinstance(failed_roads, str):
            failed_road_ids.add(failed_roads)
        elif (
            isinstance(failed_roads, tuple)
            and len(failed_roads) in (2, 3)
            and all(isinstance(x, (str, int, tuple)) for x in failed_roads)
        ):
            failed_edge_pairs.add((failed_roads[0], failed_roads[1]))
        else:
            for item in failed_roads:
                if isinstance(item, str):
                    failed_road_ids.add(item)
                elif isinstance(item, tuple) and len(item) >= 2:
                    failed_edge_pairs.add((item[0], item[1]))
                else:
                    failed_road_ids.add(str(item))

    degraded_graph = city_graph.copy()
    is_multi = degraded_graph.is_multigraph()
    passable_graph = degraded_graph.__class__()
    for n, ndata in degraded_graph.nodes(data=True):
        passable_graph.add_node(n, **ndata)

    failed_edges_count = 0
    failed_unique_ways = set()
    active_edges_count = 0

    edge_iter = (
        degraded_graph.edges(keys=True, data=True)
        if is_multi
        else ((u, v, None, data) for u, v, data in degraded_graph.edges(data=True))
    )

    for u, v, k, data in edge_iter:
        road_id = str(data.get("road_id", f"{u}-{v}"))
        already_blocked = include_blocked_condition and (
            data.get("available") is False or data.get("condition") == "BLOCKED"
        )
        explicitly_failed = (
            road_id in failed_road_ids
            or (u, v) in failed_edge_pairs
            or ( not degraded_graph.is_directed() and (v, u) in failed_edge_pairs )
        )

        if already_blocked or explicitly_failed:
            data["condition"] = "BLOCKED"
            data["available"] = False
            data["failed"] = True
            failed_edges_count += 1
            failed_unique_ways.add(road_id)
        else:
            data.setdefault("available", True)
            data.setdefault("condition", "OPEN")
            data["failed"] = False
            active_edges_count += 1
            if is_multi:
                passable_graph.add_edge(u, v, key=k, **data)
            else:
                passable_graph.add_edge(u, v, **data)

    report = {
        "total_edges": degraded_graph.number_of_edges(),
        "failed_directed_edges": failed_edges_count,
        "failed_unique_road_ways": len(failed_unique_ways),
        "failed_road_ids": sorted(failed_unique_ways),
        "remaining_active_edges": active_edges_count,
        "passable_graph": passable_graph,
    }

    return degraded_graph, report


def _component_metrics(graph):
    total_nodes = graph.number_of_nodes()
    if total_nodes == 0:
        return {
            "component_count": 0,
            "largest_component_size": 0,
            "largest_component_nodes": set(),
            "isolated_nodes": set(),
        }

    if graph.is_directed():
        comps = list(nx.weakly_connected_components(graph))
    else:
        comps = list(nx.connected_components(graph))

    largest = max(comps, key=len) if comps else set()
    isolated = {n for c in comps if len(c) == 1 for n in c}

    return {
        "component_count": len(comps),
        "largest_component_size": len(largest),
        "largest_component_nodes": largest,
        "isolated_nodes": isolated,
    }


def analyze_cascading_failures(
    city_graph,
    failed_roads=None,
    facilities_by_category=None,
    dispatch_nodes=None,
    population_by_node=None,
    population_is_synthetic=True,
):
    """
    Analyze cascading network fragmentation, emergency facility accessibility,
    and human impact caused by single or multiple road failures.

    Key outputs:
    - connectivity_impact: baseline vs post-failure components, newly disconnected
      nodes, and newly isolated nodes.
    - facility_impact: per-category breakdown separating:
        * `inaccessible_facilities`: facilities unreachable from dispatch hubs or
          disconnected from the main road network.
        * `increased_travel_time_facilities`: facilities that remain reachable
          but require a longer detour route (distance/time increase).
    - population_impact: estimates affected population ONLY when `population_by_node`
      is provided, and clearly flags whether population values are synthetic or missing.
    """

    baseline_Sim, baseline_rep = simulate_road_failures(
        city_graph, failed_roads=None, include_blocked_condition=False
    )
    baseline_passable = baseline_rep["passable_graph"]

    degraded_graph, failure_rep = simulate_road_failures(
        city_graph, failed_roads=failed_roads, include_blocked_condition=True
    )
    post_passable = failure_rep["passable_graph"]

    base_comp = _component_metrics(baseline_passable)
    post_comp = _component_metrics(post_passable)

    newly_disconnected_nodes = (
        base_comp["largest_component_nodes"] - post_comp["largest_component_nodes"]
    )
    newly_isolated_nodes = post_comp["isolated_nodes"] - base_comp["isolated_nodes"]

    connectivity_impact = {
        "total_nodes": city_graph.number_of_nodes(),
        "baseline_components": base_comp["component_count"],
        "post_failure_components": post_comp["component_count"],
        "new_components_created": max(
            0, post_comp["component_count"] - base_comp["component_count"]
        ),
        "baseline_largest_component_size": base_comp["largest_component_size"],
        "post_failure_largest_component_size": post_comp["largest_component_size"],
        "newly_disconnected_node_count": len(newly_disconnected_nodes),
        "newly_disconnected_nodes": sorted(str(n) for n in newly_disconnected_nodes),
        "newly_isolated_node_count": len(newly_isolated_nodes),
        "failed_directed_edges": failure_rep["failed_directed_edges"],
        "failed_unique_road_ways": failure_rep["failed_unique_road_ways"],
    }

    # Determine dispatch origin nodes for travel-time / reachability checks
    valid_dispatch = []
    if dispatch_nodes:
        valid_dispatch = [n for n in dispatch_nodes if n in baseline_passable]
    elif base_comp["largest_component_nodes"]:
        # Pick highest-degree node in the baseline largest component as reference hub
        best_hub = max(
            base_comp["largest_component_nodes"],
            key=lambda n: baseline_passable.degree(n),
        )
        valid_dispatch = [best_hub]

    # Compute single-source shortest path lengths from dispatch hubs (fast O(E log V))
    def _edge_weight(u, v, d):
        # For MultiDiGraph, NetworkX passes dict of parallel edges if weight is callable,
        # OR string attribute name if weight="length_m".
        if isinstance(d, dict) and "length_m" not in d and any(isinstance(val, dict) for val in d.values()):
            return min(float(sub.get("length_m", 1.0)) for sub in d.values())
        return float(d.get("length_m", 1.0))

    baseline_dist = {}
    post_dist = {}
    if valid_dispatch:
        baseline_dist = nx.multi_source_dijkstra_path_length(
            baseline_passable, sources=valid_dispatch, weight=_edge_weight
        )
        post_dist = nx.multi_source_dijkstra_path_length(
            post_passable, sources=valid_dispatch, weight=_edge_weight
        )

    # Evaluate emergency facilities separately for each category
    facility_impact = {}
    if facilities_by_category:
        for cat, fac_list in facilities_by_category.items():
            inaccessible = []
            increased_travel = []
            unaffected = []
            unmapped_to_road = 0

            for fac in fac_list:
                node_id = fac.get("nearest_node", fac.get("node_id"))
                if node_id is None or node_id not in city_graph:
                    unmapped_to_road += 1
                    continue

                was_reachable = node_id in baseline_dist
                now_reachable = node_id in post_dist and (
                    node_id in post_comp["largest_component_nodes"] or len(valid_dispatch) > 0
                )

                if was_reachable and node_id not in post_dist:
                    inaccessible.append(
                        {
                            "facility_id": fac.get("facility_id", str(node_id)),
                            "name": fac.get("name", "Unnamed"),
                            "category": cat,
                            "node_id": node_id,
                            "baseline_distance_m": round(baseline_dist[node_id], 2),
                            "post_failure_distance_m": None,
                            "status": "INACCESSIBLE",
                            "verification_status": fac.get(
                                "verification_status", "unverified_osm_record"
                            ),
                        }
                    )
                elif not was_reachable and node_id not in post_comp["largest_component_nodes"]:
                    inaccessible.append(
                        {
                            "facility_id": fac.get("facility_id", str(node_id)),
                            "name": fac.get("name", "Unnamed"),
                            "category": cat,
                            "node_id": node_id,
                            "baseline_distance_m": None,
                            "post_failure_distance_m": None,
                            "status": "INACCESSIBLE",
                            "verification_status": fac.get(
                                "verification_status", "unverified_osm_record"
                            ),
                        }
                    )
                elif was_reachable and node_id in post_dist:
                    b_d = baseline_dist[node_id]
                    p_d = post_dist[node_id]
                    delta_m = p_d - b_d
                    if delta_m > 1.0:
                        # Assume 30 km/h (8.33 m/s) urban emergency response speed for detour delta
                        extra_time_s = delta_m / 8.3333
                        increased_travel.append(
                            {
                                "facility_id": fac.get("facility_id", str(node_id)),
                                "name": fac.get("name", "Unnamed"),
                                "category": cat,
                                "node_id": node_id,
                                "baseline_distance_m": round(b_d, 2),
                                "post_failure_distance_m": round(p_d, 2),
                                "detour_increase_m": round(delta_m, 2),
                                "estimated_extra_time_sec": round(extra_time_s, 1),
                                "status": "INCREASED_TRAVEL_TIME",
                                "verification_status": fac.get(
                                    "verification_status", "unverified_osm_record"
                                ),
                            }
                        )
                    else:
                        unaffected.append(fac.get("facility_id", str(node_id)))

            facility_impact[cat] = {
                "total_evaluated": len(fac_list) - unmapped_to_road,
                "unmapped_to_road_network": unmapped_to_road,
                "inaccessible_count": len(inaccessible),
                "increased_travel_time_count": len(increased_travel),
                "unaffected_count": len(unaffected),
                "inaccessible_facilities": inaccessible,
                "increased_travel_time_facilities": increased_travel,
                "verification_status": "unverified_osm_record",
            }

    # Population impact estimation (honest handling of missing vs synthetic data)
    if population_by_node is None:
        population_impact = {
            "population_data_available": False,
            "population_data_type": "unavailable",
            "disconnected_population": None,
            "delayed_access_population": None,
            "total_affected_population": None,
            "note": (
                "OpenStreetMap road data does not include verified census population counts "
                "per road node. Provide `population_by_node` to compute population impact."
            ),
        }
    else:
        disconnected_pop = 0
        delayed_pop = 0
        for nid, pop in population_by_node.items():
            pop_val = int(pop)
            if nid in newly_disconnected_nodes or (
                nid in baseline_dist and nid not in post_dist
            ):
                disconnected_pop += pop_val
            elif (
                nid in baseline_dist
                and nid in post_dist
                and (post_dist[nid] - baseline_dist[nid]) > 1.0
            ):
                delayed_pop += pop_val

        population_impact = {
            "population_data_available": True,
            "population_data_type": (
                "synthetic_scenario_assumption"
                if population_is_synthetic
                else "verified_external_dataset"
            ),
            "is_synthetic": bool(population_is_synthetic),
            "disconnected_population": disconnected_pop,
            "delayed_access_population": delayed_pop,
            "total_affected_population": disconnected_pop + delayed_pop,
            "note": (
                "Population figures are based on synthetic scenario inputs for prototype demonstration."
                if population_is_synthetic
                else "Population figures derived from supplied external dataset."
            ),
        }

    return {
        "degraded_graph": degraded_graph,
        "connectivity_impact": connectivity_impact,
        "facility_impact": facility_impact,
        "population_impact": population_impact,
    }

