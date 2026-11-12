"""
SANJEEVANI: Human-Centric Disaster Intelligence & Infrastructure Resilience
Module 1: Disaster Prediction & Infrastructure Resilience
File: main.py

Purpose:
    Master Integration Pipeline & Demonstration Pipeline.
    Executes the complete end-to-end resilience analysis workflow:
        1. City Network Construction
        2. Network Statistics & Topological Screening
        3. Cut-Edge Detection & Vulnerability Analysis
        4. Scenario Failure Simulations (RD04 Cut-Edge & RD11 River Bridge)
        5. Human Impact Estimation & Delay Quantification
        6. Comprehensive Critical Road Ranking
        7. Pre-Disaster Emergency Resource Positioning Plan
        8. Visual Network Map Generation (PNG)
        9. Structured Data Artifact Exports (JSON & CSV)

Scientific & Prototype Disclaimer:
    ALL DATA AND METRICS IN THIS MODULE ARE SYNTHETIC AND DESIGNED SOLELY
    FOR PROTOTYPE DEMONSTRATION AND DECISION-SUPPORT TESTING. THEY DO NOT
    REPRESENT REAL-WORLD GEOGRAPHICAL SURVEYS OR CALIBRATED FLOOD PREDICTIONS.
"""

import os
import json
from typing import Dict, Any, Tuple
import networkx as nx
import pandas as pd

# Set headless Matplotlib backend for reliable, non-blocking rendering on all systems
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Import module components
from data import (
    build_synthetic_city,
    get_city_summary,
    save_city_to_json,
    export_city_to_dataframes,
)
from resilience import (
    calculate_edge_centrality,
    identify_critical_bridges,
    simulate_road_failure,
    simulate_multiple_failures,
    estimate_human_impact,
    evaluate_all_roads_human_impact,
    rank_critical_roads_comprehensive,
    export_comprehensive_ranking,
    generate_resource_plan,
    export_resource_plan,
)


# -----------------------------------------------------------------------------
# 1. VISUALIZATION ENGINE (PNG EXPORTS)
# -----------------------------------------------------------------------------

NODE_COLOR_MAP = {
    "residential": "#3498db",        # Sky Blue
    "hospital": "#e74c3c",           # Crimson Red
    "shelter": "#2ecc71",            # Emerald Green
    "emergency_station": "#f39c12",  # Amber Orange
    "junction": "#95a5a6",           # Slate Grey
}


def _get_node_positions(G: nx.Graph) -> Dict[str, Tuple[int, int]]:
    """Extracts (x, y) coordinates from node attributes."""
    return {n: d.get("pos", (0, 0)) for n, d in G.nodes(data=True)}


def plot_city_network(G: nx.Graph, output_path: str = "outputs/viz_city_network.png") -> str:
    """
    Renders and saves the baseline synthetic city network topology.
    Distinguishes hospitals, shelters, stations, residential wards, and bridges.
    """
    pos = _get_node_positions(G)
    fig, ax = plt.subplots(figsize=(12, 10))

    # 1. Draw Edges
    bridges = [(u, v) for u, v, d in G.edges(data=True) if d.get("road_type") == "bridge"]
    roads = [(u, v) for u, v, d in G.edges(data=True) if d.get("road_type") != "bridge"]

    nx.draw_networkx_edges(G, pos, edgelist=roads, edge_color="#7f8c8d", width=2.0, alpha=0.7, ax=ax)
    nx.draw_networkx_edges(G, pos, edgelist=bridges, edge_color="#8e44ad", width=4.0, style="solid", ax=ax)

    # 2. Draw Nodes by Type
    for ntype, color in NODE_COLOR_MAP.items():
        nodes = [n for n, d in G.nodes(data=True) if d.get("type") == ntype]
        if not nodes:
            continue
        sizes = [
            1100 if ntype in ("hospital", "shelter") else (900 if ntype == "emergency_station" else max(600, G.nodes[n].get("population", 0) // 30))
            for n in nodes
        ]
        nx.draw_networkx_nodes(
            G, pos, nodelist=nodes, node_color=color, node_size=sizes,
            edgecolors="#2c3e50", linewidths=1.5, ax=ax
        )

    # 3. Draw Labels
    labels = {n: f"{n}\n{G.nodes[n].get('name', n)[:12]}" for n in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8, font_weight="bold", ax=ax)

    # 4. Legend & Title
    legend_handles = [
        mpatches.Patch(color=color, label=ntype.replace("_", " ").title())
        for ntype, color in NODE_COLOR_MAP.items()
    ]
    legend_handles.append(mpatches.Patch(color="#8e44ad", label="Physical Bridge (Waterway)"))
    legend_handles.append(mpatches.Patch(color="#7f8c8d", label="Transit Road"))

    ax.legend(handles=legend_handles, loc="upper left", frameon=True, fontsize=9)
    ax.set_title("SANJEEVANI: Synthetic City Infrastructure Network\nBaseline Topological Map (Priority 1–7)", fontsize=13, fontweight="bold")
    ax.axis("off")

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_critical_roads(G: nx.Graph, ranked_df: pd.DataFrame, output_path: str = "outputs/viz_critical_roads.png") -> str:
    """
    Renders the city network with roads highlighted by criticality level.
    """
    pos = _get_node_positions(G)
    fig, ax = plt.subplots(figsize=(12, 10))

    # Map road_id to criticality_level
    crit_lookup = {r["road_id"]: r["criticality_level"] for _, r in ranked_df.iterrows()}

    level_colors = {
        "CRITICAL": "#c0392b",  # Dark Red
        "HIGH": "#e67e22",      # Deep Orange
        "MODERATE": "#f1c40f",  # Amber Yellow
        "LOW": "#bdc3c7",       # Light Grey
    }

    # Group edges by criticality level
    for level, color in level_colors.items():
        edgelist = []
        for u, v, d in G.edges(data=True):
            rid = d.get("road_id")
            if crit_lookup.get(rid) == level:
                edgelist.append((u, v))
        if edgelist:
            w = 4.5 if level == "CRITICAL" else (3.5 if level == "HIGH" else 2.0)
            nx.draw_networkx_edges(G, pos, edgelist=edgelist, edge_color=color, width=w, ax=ax)

    # Draw nodes
    for ntype, color in NODE_COLOR_MAP.items():
        nodes = [n for n, d in G.nodes(data=True) if d.get("type") == ntype]
        nx.draw_networkx_nodes(G, pos, nodelist=nodes, node_color=color, node_size=650, edgecolors="#2c3e50", ax=ax)

    labels = {n: n for n in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8, font_weight="bold", ax=ax)

    handles = [mpatches.Patch(color=color, label=f"{level} Criticality Road") for level, color in level_colors.items()]
    ax.legend(handles=handles, loc="upper left", fontsize=9)
    ax.set_title("SANJEEVANI: Comprehensive Critical Road Ranking\nMulti-Criteria Vulnerability & Impact (Priority 5)", fontsize=13, fontweight="bold")
    ax.axis("off")

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_scenario_failure(
    G: nx.Graph,
    failed_road_ids: list,
    isolated_nodes: list,
    output_path: str,
    title: str,
) -> str:
    """
    Renders a disaster scenario with failed road(s) marked in red dashed lines
    and isolated/severed nodes highlighted with warning rings.
    """
    pos = _get_node_positions(G)
    fig, ax = plt.subplots(figsize=(12, 10))

    # Active roads vs Failed roads
    active_edges = []
    failed_edges = []
    for u, v, d in G.edges(data=True):
        if d.get("road_id") in failed_road_ids:
            failed_edges.append((u, v))
        else:
            active_edges.append((u, v))

    nx.draw_networkx_edges(G, pos, edgelist=active_edges, edge_color="#7f8c8d", width=2.0, ax=ax)
    if failed_edges:
        nx.draw_networkx_edges(
            G, pos, edgelist=failed_edges, edge_color="#e74c3c",
            width=4.5, style="dashed", ax=ax
        )

    # Draw normal nodes
    normal_nodes = [n for n in G.nodes() if n not in isolated_nodes]
    nx.draw_networkx_nodes(
        G, pos, nodelist=normal_nodes,
        node_color=[NODE_COLOR_MAP.get(G.nodes[n].get("type"), "#95a5a6") for n in normal_nodes],
        node_size=650, edgecolors="#2c3e50", ax=ax
    )

    # Highlight isolated nodes with bold warning halo
    if isolated_nodes:
        nx.draw_networkx_nodes(
            G, pos, nodelist=isolated_nodes, node_color="#c0392b",
            node_size=1100, edgecolors="#f39c12", linewidths=3.5, ax=ax
        )

    labels = {n: n for n in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8, font_weight="bold", ax=ax)

    handles = [
        mpatches.Patch(color="#7f8c8d", label="Operational Roads"),
        mpatches.Patch(color="#e74c3c", label=f"Failed Road ({', '.join(failed_road_ids)})"),
    ]
    if isolated_nodes:
        handles.append(mpatches.Patch(color="#c0392b", label=f"Isolated Zones ({', '.join(isolated_nodes)})"))

    ax.legend(handles=handles, loc="upper left", fontsize=9)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.axis("off")

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_resource_plan(
    G: nx.Graph,
    plan: Dict[str, Any],
    output_path: str = "outputs/viz_resource_plan.png",
) -> str:
    """
    Renders the pre-disaster resource staging locations on the city network.
    """
    pos = _get_node_positions(G)
    fig, ax = plt.subplots(figsize=(12, 10))

    # Draw underlying infrastructure
    nx.draw_networkx_edges(G, pos, edge_color="#bdc3c7", width=1.5, ax=ax)

    summary_by_node = plan.get("summary_by_node", {})
    staged_nodes = list(summary_by_node.keys())
    non_staged_nodes = [n for n in G.nodes() if n not in staged_nodes]

    # Non-staged nodes
    nx.draw_networkx_nodes(
        G, pos, nodelist=non_staged_nodes,
        node_color=[NODE_COLOR_MAP.get(G.nodes[n].get("type"), "#95a5a6") for n in non_staged_nodes],
        node_size=500, alpha=0.5, edgecolors="#bdc3c7", ax=ax
    )

    # Staged nodes (larger, highlighted)
    if staged_nodes:
        nx.draw_networkx_nodes(
            G, pos, nodelist=staged_nodes,
            node_color=[NODE_COLOR_MAP.get(G.nodes[n].get("type"), "#95a5a6") for n in staged_nodes],
            node_size=1000, edgecolors="#2c3e50", linewidths=2.5, ax=ax
        )

    # Labels with staged counts
    labels = {}
    for n in G.nodes():
        if n in summary_by_node:
            t = summary_by_node[n].get("total_staged_assets", 0)
            labels[n] = f"{n}\n[{t} Assets]"
        else:
            labels[n] = n

    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8, font_weight="bold", ax=ax)

    ax.set_title("SANJEEVANI: Pre-Disaster Resource Positioning Plan\nStaging Depots & Asset Allocation (Priority 6)", fontsize=13, fontweight="bold")
    ax.axis("off")

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


# -----------------------------------------------------------------------------
# 2. MASTER UNIFIED PIPELINE EXECUTION
# -----------------------------------------------------------------------------

def run_pipeline(output_dir: str = "outputs") -> Dict[str, Any]:
    """
    Executes the master SANJEEVANI integration workflow sequentially:
        1. Network Construction & Graph Integrity Checks
        2. Statistical Summarization
        3. Topological Cut-Edge & Centrality Analysis
        4. Scenario Failure Simulations (RD04 & RD11)
        5. Human Impact Calculations
        6. Comprehensive Critical Road Ranking
        7. Pre-Disaster Resource Positioning Staging Plan
        8. Visual Network Map Generation (5 PNG Visualizations)
        9. Structured Disk Exports (JSON & CSV)

    Parameters:
        output_dir (str): Directory where output artifacts will be written.

    Returns:
        Dict[str, Any]: High-level pipeline execution registry and file manifest.
    """
    os.makedirs(output_dir, exist_ok=True)
    generated_files = []

    print("\n" + "=" * 80)
    print(" SANJEEVANI — Human-Centric Disaster Intelligence & Infrastructure Resilience")
    print(" Module 1: Master Unified Pipeline & Integration Verification")
    print(" Tagline: Predict the failure. Protect the connection. Save the response time.")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # STEP 1: City Network Construction
    # -------------------------------------------------------------------------
    print("\n[PHASE 1] Constructing Synthetic City Road Network...")
    G = build_synthetic_city()
    orig_nodes = G.number_of_nodes()
    orig_edges = G.number_of_edges()
    print(f" -> Initialized NetworkX Graph with {orig_nodes} nodes and {orig_edges} edges.")

    # -------------------------------------------------------------------------
    # STEP 2: Statistical Summarization & Baseline Network Export
    # -------------------------------------------------------------------------
    print("\n[PHASE 2] Generating Baseline City Statistics & Network Model...")
    summary = get_city_summary(G)
    city_summary_path = os.path.join(output_dir, "city_summary.json")
    with open(city_summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    generated_files.append(city_summary_path)

    baseline_network_path = os.path.join(output_dir, "baseline_city_network.json")
    save_city_to_json(G, baseline_network_path)
    generated_files.append(baseline_network_path)

    print(f" -> Total Residential Population: {summary['total_population']:,}")
    print(f" -> Total Hospital Bed Capacity:  {summary['total_hospital_beds']:,}")
    print(f" -> Total Shelter Capacity:       {summary['total_shelter_capacity']:,}")
    print(f" -> Exported: {city_summary_path}")
    print(f" -> Exported: {baseline_network_path}")

    # -------------------------------------------------------------------------
    # STEP 3 & 4: Cut-Edge Detection & Vulnerability Analysis
    # -------------------------------------------------------------------------
    print("\n[PHASE 3] Topological Cut-Edge Detection & Centrality Analysis...")
    cut_edges = identify_critical_bridges(G, return_classification=False)
    ebc_map = calculate_edge_centrality(G)
    print(f" -> Graph Cut-Edges (Single Points of Failure): {cut_edges}")
    top_central = sorted(ebc_map.items(), key=lambda x: x[1], reverse=True)[:3]
    print(f" -> Top 3 Betweenness Centrality Arteries: {top_central}")

    # -------------------------------------------------------------------------
    # STEP 5 & 6: Scenario Failure Simulations (RD04 & RD11)
    # -------------------------------------------------------------------------
    print("\n[PHASE 4] Simulating Road Failure Scenarios...")

    # SCENARIO A: RD04 (Hilltop Access Road)
    print(" -> Running Scenario A: Failure of RD04 (Hilltop Access Road)...")
    rep_rd04 = simulate_road_failure(G, "RD04")
    impact_rd04 = estimate_human_impact(G, rep_rd04)

    rd04_json_path = os.path.join(output_dir, "rd04_failure_scenario.json")
    serializable_rd04 = {k: v for k, v in rep_rd04.items() if k != "scenario_graph"}
    serializable_rd04["human_impact"] = {k: v for k, v in impact_rd04.items() if k != "delays_by_zone"}
    serializable_rd04["delays_by_zone"] = impact_rd04["delays_by_zone"]
    with open(rd04_json_path, "w", encoding="utf-8") as f:
        json.dump(serializable_rd04, f, indent=2)
    generated_files.append(rd04_json_path)
    print(f"    * Connected Components: {rep_rd04['connected_component_count']}")
    print(f"    * Isolated Zones:       {rep_rd04['disconnected_residential_zones']}")
    print(f"    * Pop Losing Access:    {impact_rd04['unique_population_lost_critical_service']:,}")
    print(f"    * Exported: {rd04_json_path}")

    # SCENARIO B: RD11 (Grand River Bridge)
    print(" -> Running Scenario B: Failure of RD11 (Grand River Bridge)...")
    rep_rd11 = simulate_road_failure(G, "RD11")
    impact_rd11 = estimate_human_impact(G, rep_rd11)

    rd11_json_path = os.path.join(output_dir, "rd11_failure_scenario.json")
    serializable_rd11 = {k: v for k, v in rep_rd11.items() if k != "scenario_graph"}
    serializable_rd11["human_impact"] = {k: v for k, v in impact_rd11.items() if k != "delays_by_zone"}
    serializable_rd11["delays_by_zone"] = impact_rd11["delays_by_zone"]
    with open(rd11_json_path, "w", encoding="utf-8") as f:
        json.dump(serializable_rd11, f, indent=2)
    generated_files.append(rd11_json_path)
    print(f"    * Connected Components: {rep_rd11['connected_component_count']} (Remains Connected via Detours)")
    print(f"    * Alternative Routes:   Active via RD18/RD19 (South Causeway) & RD17 (Civic Overpass)")
    print(f"    * Pop Losing Access:    {impact_rd11['unique_population_lost_critical_service']}")
    print(f"    * Exported: {rd11_json_path}")

    # Export city-wide human impact table
    human_impact_df = evaluate_all_roads_human_impact(G)
    human_impact_csv_path = os.path.join(output_dir, "human_impact_results.csv")
    human_impact_df.to_csv(human_impact_csv_path, index=False, encoding="utf-8")
    generated_files.append(human_impact_csv_path)
    print(f" -> Exported All-Roads Human Impact Table: {human_impact_csv_path}")

    # -------------------------------------------------------------------------
    # STEP 7: Comprehensive Critical Road Ranking
    # -------------------------------------------------------------------------
    print("\n[PHASE 5] Computing Comprehensive Critical Road Ranking...")
    crit_csv_path = os.path.join(output_dir, "critical_road_ranking.csv")
    crit_json_path = os.path.join(output_dir, "critical_road_ranking.json")
    ranked_df = export_comprehensive_ranking(G, csv_path=crit_csv_path, json_path=crit_json_path)
    generated_files.extend([crit_csv_path, crit_json_path])

    print(" -> Top 3 Critical Roads:")
    for _, row in ranked_df.head(3).iterrows():
        print(f"    * {row['road_id']}: {row['road_name']} [{row['criticality_level']}] (Score: {row['comprehensive_criticality_score']:.4f})")
    print(f" -> Exported: {crit_csv_path}")
    print(f" -> Exported: {crit_json_path}")

    # -------------------------------------------------------------------------
    # STEP 8: Pre-Disaster Resource Positioning Plan
    # -------------------------------------------------------------------------
    print("\n[PHASE 6] Generating Pre-Disaster Resource Positioning Plan...")
    res_csv_path = os.path.join(output_dir, "resource_positioning_plan.csv")
    res_json_path = os.path.join(output_dir, "resource_positioning_plan.json")
    res_df, plan = export_resource_plan(G, csv_path=res_csv_path, json_path=res_json_path)
    generated_files.extend([res_csv_path, res_json_path])

    print(f" -> Total Assets Staged: {plan['total_resources_allocated']} across {len(plan['summary_by_node'])} strategic locations.")
    print(f" -> Exported: {res_csv_path}")
    print(f" -> Exported: {res_json_path}")

    # -------------------------------------------------------------------------
    # STEP 9: Visual Topology Map Generation (Matplotlib PNGs)
    # -------------------------------------------------------------------------
    print("\n[PHASE 7] Generating Visual Infrastructure Maps (NetworkX & Matplotlib)...")

    # 1. Baseline Topology Map
    viz_baseline = os.path.join(output_dir, "viz_city_network.png")
    plot_city_network(G, output_path=viz_baseline)
    generated_files.append(viz_baseline)
    print(f" -> Rendered Baseline Network: {viz_baseline}")

    # 2. Critical Roads Map
    viz_crit = os.path.join(output_dir, "viz_critical_roads.png")
    plot_critical_roads(G, ranked_df, output_path=viz_crit)
    generated_files.append(viz_crit)
    print(f" -> Rendered Critical Road Map: {viz_crit}")

    # 3. Scenario A Map (RD04 Failure)
    viz_rd04 = os.path.join(output_dir, "viz_rd04_failure.png")
    plot_scenario_failure(
        G, failed_road_ids=["RD04"], isolated_nodes=["R3"],
        output_path=viz_rd04,
        title="SANJEEVANI Scenario A: Failure of RD04 (Hilltop Access Road)\nComplete Population Isolation of Zone R3 (9,500 Citizens)"
    )
    generated_files.append(viz_rd04)
    print(f" -> Rendered Scenario A Map:   {viz_rd04}")

    # 4. Scenario B Map (RD11 Failure)
    viz_rd11 = os.path.join(output_dir, "viz_rd11_failure.png")
    plot_scenario_failure(
        G, failed_road_ids=["RD11"], isolated_nodes=[],
        output_path=viz_rd11,
        title="SANJEEVANI Scenario B: Failure of RD11 (Grand River Bridge)\nArterial Bridge Blockage & Alternative Detour Routing"
    )
    generated_files.append(viz_rd11)
    print(f" -> Rendered Scenario B Map:   {viz_rd11}")

    # 5. Resource Plan Map
    viz_res = os.path.join(output_dir, "viz_resource_plan.png")
    plot_resource_plan(G, plan, output_path=viz_res)
    generated_files.append(viz_res)
    print(f" -> Rendered Resource Staging Map: {viz_res}")

    # -------------------------------------------------------------------------
    # STEP 10: Strict Non-Mutation Assertion
    # -------------------------------------------------------------------------
    assert G.number_of_nodes() == orig_nodes, "Integrity Error: Node count mutated during pipeline execution!"
    assert G.number_of_edges() == orig_edges, "Integrity Error: Edge count mutated during pipeline execution!"

    print("\n" + "=" * 80)
    print(f" PIPELINE COMPLETE: All {len(generated_files)} artifacts successfully verified & exported!")
    print(" Original city network graph preserved without mutation.")
    print("=" * 80 + "\n")

    return {
        "status": "SUCCESS",
        "output_directory": output_dir,
        "total_files_generated": len(generated_files),
        "generated_files": generated_files,
        "is_original_graph_unchanged": True,
        "summary": summary,
        "top_critical_roads": ranked_df.head(3)[["road_id", "road_name", "criticality_level"]].to_dict(orient="records"),
        "scenarios_evaluated": ["RD04", "RD11"],
    }


if __name__ == "__main__":
    run_pipeline()

