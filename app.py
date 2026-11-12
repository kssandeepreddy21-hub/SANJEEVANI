"""
app.py
------
RESQ-AI — Emergency Operations Centre (EOC) Main Dashboard
Member 4: Dashboard UI, Interactive GIS Mapping, and Unified System Integration.

Unifies:
  - Member 1: Infrastructure Resilience & Critical Corridor Prototype
  - Member 2: Emergency Report Intake & Simulated Evidence Verification
  - Member 3: Real Bengaluru OSM Network, Flood Simulation, Routing & Optimization
"""

from __future__ import annotations

import html
import textwrap
from pathlib import Path
from typing import Any

import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from sanjeevani.audit import (
    append_audit_event,
    create_initial_audit_log,
    get_audit_dataframe,
    verify_audit_chain_detailed,
)
from sanjeevani.benchmark import run_benchmark_evaluation
from sanjeevani.config import ENV_DATA_DIR, get_mode, osm_data_available
from sanjeevani.dashboard_osm import (
    SNAPSHOT_PATH,
    build_bengaluru_osm_map,
    build_corridor_rainfall_progression_chart,
    build_facility_impact_chart,
    build_osm_strategy_comparison_chart,
    build_vulnerability_distribution_chart,
    get_active_observations_df,
    get_allocations_df,
    get_corridor_progression_df,
    get_facility_counts_df,
    get_facility_impact_df,
    get_osm_overview_kpis,
    get_rescue_routes_df,
    get_strategy_comparison_df,
    get_top_vulnerable_roads_df,
    get_vulnerability_summary_df,
    load_corridor_snapshot,
    load_member1_artifacts,
    run_live_corridor_allocation,
    run_live_corridor_rainfall,
    run_live_corridor_routing,
    snap_emergency_reports_to_corridor,
)
from sanjeevani.data import (
    CITY_CENTER,
    SYNTHETIC_JUNCTIONS,
    get_critical_alerts,
    get_overview_metrics,
    get_precautions_by_disaster_type,
    get_recent_activity,
    get_scenario_names,
    get_synthetic_hospitals,
    get_synthetic_incidents,
    get_synthetic_rescue_teams,
    get_synthetic_roads,
)
from sanjeevani.decision import (
    allocate_rescue_resources,
    compare_all_strategies,
    get_strategy_names,
)
from sanjeevani.evidence import (
    SECTOR_COORDINATES,
    filter_incident_reports,
    score_emergency_report,
    summarize_evidence_metrics,
)
from sanjeevani.osm_data_loader import (
    OSMDataUnavailableError,
    load_corridor,
    load_dashboard_payload,
)
from sanjeevani.resilience import (
    assess_road_network_resilience,
    simulate_single_road_failure,
)
from sanjeevani.twin import (
    HORIZON_LABELS,
    HORIZONS_MINUTES,
    build_horizon_comparison_df,
    build_road_progression_df,
    compute_rainfall_sensitivity_curve,
    get_cascading_impacts_and_observations,
    simulate_all_horizons,
)

# ---------------------------------------------------------------------------
# 1. PAGE CONFIGURATION
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="RESQ-AI | Disaster Intelligence & EOC",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# 2. DARK NAVY EOC STYLING (CSS)
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        background-color: #0B1120;
        color: #F8FAFC;
        font-family: 'Inter', 'Segoe UI', Roboto, Helvetica, sans-serif;
    }
    section[data-testid="stSidebar"] {
        background-color: #0F172A;
        border-right: 1px solid #1E293B;
    }
    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 2.5rem;
        max-width: 100%;
    }
    .eoc-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        border: 1px solid #334155;
        border-left: 5px solid #38BDF8;
        border-radius: 10px;
        padding: 18px 24px;
        margin-bottom: 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 16px;
    }
    .eoc-title {
        font-size: 1.7rem;
        font-weight: 800;
        letter-spacing: 1.2px;
        color: #F8FAFC;
        margin: 0;
    }
    .eoc-subtitle {
        font-size: 0.9rem;
        color: #94A3B8;
        margin-top: 2px;
    }
    .eoc-tagline {
        font-size: 0.78rem;
        color: #38BDF8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 4px;
    }
    .status-badge {
        display: inline-block;
        padding: 8px 16px;
        border-radius: 999px;
        font-weight: 700;
        font-size: 0.82rem;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        white-space: nowrap;
        border: 1px solid rgba(255,255,255,0.15);
    }
    .workflow-bar {
        background-color: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 8px;
        padding: 10px 18px;
        margin-bottom: 18px;
        font-size: 0.78rem;
        color: #94A3B8;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 10px;
    }
    .workflow-steps span {
        color: #E2E8F0;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 4px;
        background-color: #1E293B;
        margin: 0 3px;
        display: inline-block;
    }
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(6, minmax(0, 1fr));
        gap: 14px;
        margin-bottom: 20px;
        align-items: stretch;
    }
    @media (max-width: 1400px) {
        .kpi-grid {
            grid-template-columns: repeat(3, minmax(0, 1fr));
        }
    }
    @media (max-width: 768px) {
        .kpi-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }
    .kpi-card {
        background-color: #111C33;
        border: 1px solid #1E293B;
        border-radius: 10px;
        padding: 16px 16px;
        min-height: 118px;
        height: 100%;
        box-sizing: border-box;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    }
    .kpi-label {
        font-size: 0.73rem;
        text-transform: uppercase;
        letter-spacing: 0.7px;
        color: #94A3B8;
        font-weight: 600;
        margin-bottom: 6px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .kpi-value {
        font-size: clamp(1.25rem, 1.5vw, 1.65rem);
        font-weight: 800;
        color: #F8FAFC;
        line-height: 1.2;
        word-break: keep-all;
        overflow-wrap: normal;
    }
    .kpi-status-text {
        font-size: clamp(0.95rem, 1.15vw, 1.2rem);
        font-weight: 800;
        line-height: 1.25;
        word-break: keep-all;
        overflow-wrap: normal;
    }
    .kpi-sub {
        font-size: 0.75rem;
        margin-top: 8px;
        color: #CBD5E1;
        line-height: 1.3;
    }
    .alert-card-critical {
        background-color: rgba(239, 68, 68, 0.12);
        border: 1px solid rgba(239, 68, 68, 0.45);
        border-left: 4px solid #EF4444;
        border-radius: 8px;
        padding: 12px 14px;
        margin-bottom: 12px;
    }
    .alert-card-warning {
        background-color: rgba(249, 115, 22, 0.12);
        border: 1px solid rgba(249, 115, 22, 0.45);
        border-left: 4px solid #F97316;
        border-radius: 8px;
        padding: 12px 14px;
        margin-bottom: 12px;
    }
    .alert-header {
        display: flex;
        justify-content: space-between;
        font-size: 0.75rem;
        font-weight: 700;
        margin-bottom: 4px;
    }
    .alert-title {
        font-size: 0.9rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-bottom: 3px;
    }
    .alert-detail {
        font-size: 0.8rem;
        color: #CBD5E1;
    }
    .section-header {
        font-size: 1.05rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid #1E293B;
    }
    .legend-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 12px;
    }
    .legend-pill {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 99px;
        font-size: 0.74rem;
        font-weight: 600;
        white-space: nowrap;
    }
    .provenance-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 14px;
    }
    .provenance-pill {
        display: inline-block;
        padding: 4px 11px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.3px;
    }
    iframe[title="streamlit_folium.st_folium"] {
        width: 100% !important;
        border-radius: 10px;
        border: 1px solid #1E293B;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 2B. SESSION STATE & CACHED DATA LOADERS
# ---------------------------------------------------------------------------
if "manual_failed_roads" not in st.session_state:
    st.session_state.manual_failed_roads = set()

if "custom_incidents" not in st.session_state:
    st.session_state.custom_incidents = []

if "verified_overrides" not in st.session_state:
    st.session_state.verified_overrides = {}

if "audit_log" not in st.session_state:
    st.session_state.audit_log = create_initial_audit_log()

if "last_logged_scenario" not in st.session_state:
    st.session_state.last_logged_scenario = None

if "selected_rescue_strategy" not in st.session_state:
    st.session_state.selected_rescue_strategy = get_strategy_names()[2]

if "last_logged_strategy" not in st.session_state:
    st.session_state.last_logged_strategy = st.session_state.selected_rescue_strategy

if "future_rainfall_override" not in st.session_state:
    st.session_state.future_rainfall_override = None

if "future_horizon_min" not in st.session_state:
    st.session_state.future_horizon_min = 30

if "osm_live_rainfall" not in st.session_state:
    st.session_state.osm_live_rainfall = None

if "osm_live_routing" not in st.session_state:
    st.session_state.osm_live_routing = None

if "osm_live_allocation" not in st.session_state:
    st.session_state.osm_live_allocation = None


@st.cache_data(show_spinner=False)
def _cached_osm_payload() -> dict[str, Any] | None:
    try:
        return load_dashboard_payload()
    except OSMDataUnavailableError:
        return None


@st.cache_data(show_spinner=False)
def _cached_corridor_snapshot() -> dict[str, Any] | None:
    return load_corridor_snapshot(SNAPSHOT_PATH)


@st.cache_resource(show_spinner="Loading Central Bengaluru OSM Corridor subgraph (~32,722 nodes)...")
def _cached_corridor_graph():
    return load_corridor()


def _render_kpi_cards(cards: list[dict[str, str]]) -> None:
    cards_html = []
    for card in cards:
        color = html.escape(card.get("color", "#38BDF8"))
        label = html.escape(card.get("label", ""))
        value = html.escape(card.get("value", ""))
        sub = html.escape(card.get("sub", ""))
        cards_html.append(
            f'<div class="kpi-card" style="border-top: 3px solid {color};">'
            f'<div><div class="kpi-label">{label}</div>'
            f'<div class="kpi-value" style="color:{color};">{value}</div></div>'
            f'<div class="kpi-sub">{sub}</div></div>'
        )
    st.markdown(f'<div class="kpi-grid">{"".join(cards_html)}</div>', unsafe_allow_html=True)


def _render_provenance_badges(items: list[tuple[str, str]]) -> None:
    pills = []
    for text, color in items:
        safe_txt = html.escape(text)
        pills.append(
            f'<span class="provenance-pill" '
            f'style="background:{color}22; color:{color}; border:1px solid {color}66;">'
            f"{safe_txt}</span>"
        )
    st.markdown(f'<div class="provenance-bar">{"".join(pills)}</div>', unsafe_allow_html=True)


def get_active_incidents_df(scenario_name: str) -> pd.DataFrame:
    """Return active incidents combined with user-submitted session reports & overrides."""
    base_df = get_synthetic_incidents(scenario_name).copy()
    if st.session_state.custom_incidents:
        custom_df = pd.DataFrame(st.session_state.custom_incidents)
        base_df = pd.concat([custom_df, base_df], ignore_index=True)

    if st.session_state.verified_overrides:
        for idx, row in base_df.iterrows():
            inc_id = row["incident_id"]
            if inc_id in st.session_state.verified_overrides:
                base_df.at[idx, "verified"] = st.session_state.verified_overrides[inc_id]
    return base_df


# ---------------------------------------------------------------------------
# 3. SYNTHETIC MAP & PLOTLY HELPERS (PRESERVED FROM PROTOTYPE)
# ---------------------------------------------------------------------------
def build_eoc_city_map(
    scenario_name: str,
    highlight_road_id: str | None = None,
    roads_override: list[dict] | None = None,
    rescue_routes: list[dict] | None = None,
) -> folium.Map:
    """Build interactive Folium map for Synthetic Prototype Mode."""
    m = folium.Map(
        location=[CITY_CENTER[0], CITY_CENTER[1]],
        zoom_start=13,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    roads = (
        roads_override
        if roads_override is not None
        else get_synthetic_roads(scenario_name, manual_failed_roads=st.session_state.manual_failed_roads)
    )
    hospitals = get_synthetic_hospitals()
    teams = get_synthetic_rescue_teams()
    incidents = get_active_incidents_df(scenario_name)

    for road in roads:
        status = road["status"]
        if status == "BLOCKED":
            color, weight, opacity = "#EF4444", 7, 0.92
        elif status == "WARNING":
            color, weight, opacity = "#F97316", 6, 0.88
        else:
            color, weight, opacity = "#22C55E", 5, 0.85

        dash_array = "8, 8" if status == "BLOCKED" else None
        is_highlighted = highlight_road_id and road["road_id"] == highlight_road_id
        if is_highlighted:
            weight += 4
            opacity = 1.0

        road_coords = road.get("coords") or [
            [SYNTHETIC_JUNCTIONS[road["u"]]["lat"], SYNTHETIC_JUNCTIONS[road["u"]]["lon"]],
            [SYNTHETIC_JUNCTIONS[road["v"]]["lat"], SYNTHETIC_JUNCTIONS[road["v"]]["lon"]],
        ]
        tooltip_html = (
            f"<b>{road['road_id']}: {road['name']}</b><br>"
            f"Status: <b>{status}</b><br>"
            f"Failure Prob: {int(road['failure_prob']*100)}% | Vuln: {road['vulnerability_score']}<br>"
            f"Condition: {road['reason']}"
        )
        if is_highlighted:
            folium.PolyLine(
                locations=road_coords,
                color="#38BDF8",
                weight=weight + 5,
                opacity=0.65,
            ).add_to(m)

        folium.PolyLine(
            locations=road_coords,
            color=color,
            weight=weight,
            opacity=opacity,
            dash_array=dash_array,
            tooltip=tooltip_html,
        ).add_to(m)

    if rescue_routes:
        for route in rescue_routes:
            for seg_coords in route.get("leg1_coords", []):
                folium.PolyLine(
                    locations=seg_coords,
                    color="#A855F7",
                    weight=5,
                    opacity=0.95,
                    dash_array="6, 5",
                    tooltip=(
                        f"<b>DISPATCH ({route.get('unit_id')}) → {route.get('incident_id')}</b><br>"
                        f"Roads: {route.get('leg1_roads')} | ETA: {route.get('eta_min')} min"
                    ),
                ).add_to(m)
            for seg_coords in route.get("leg2_coords", []):
                folium.PolyLine(
                    locations=seg_coords,
                    color="#38BDF8",
                    weight=4,
                    opacity=0.9,
                    dash_array="4, 6",
                    tooltip=(
                        f"<b>EVACUATION ({route.get('incident_id')}) → {route.get('hospital_id')}</b><br>"
                        f"Roads: {route.get('leg2_roads')}"
                    ),
                ).add_to(m)

    for junc_id, info in SYNTHETIC_JUNCTIONS.items():
        if info.get("hospital_id") is None:
            folium.CircleMarker(
                location=[info["lat"], info["lon"]],
                radius=6,
                color="#94A3B8",
                fill=True,
                fill_color="#1E293B",
                fill_opacity=0.95,
                tooltip=f"<b>{junc_id}: {info['name']}</b><br>Est. Residents: {info['population']:,}",
            ).add_to(m)

    for _, hosp in hospitals.iterrows():
        folium.Marker(
            location=[hosp["lat"], hosp["lon"]],
            tooltip=f"<b>{hosp['name']}</b> ({hosp['hospital_id']})<br>ICU Beds: {hosp['icu_beds_free']} | Status: {hosp['status']}",
            icon=folium.Icon(color="blue", icon="plus-sign"),
        ).add_to(m)

    for _, team in teams.iterrows():
        folium.CircleMarker(
            location=[team["lat"], team["lon"]],
            radius=8,
            color="#F8FAFC",
            weight=2,
            fill=True,
            fill_color="#A855F7",
            fill_opacity=0.95,
            tooltip=f"<b>{team['unit_id']}</b> ({team['type']})<br>Status: {team['status']} | Sector: {team['assigned_sector']}",
        ).add_to(m)

    for _, inc in incidents.iterrows():
        urg = inc["urgency"]
        fill_col = "#EF4444" if urg == "CRITICAL" else "#F97316"
        marker_radius = 10 if urg == "CRITICAL" else 8
        folium.CircleMarker(
            location=[inc["lat"], inc["lon"]],
            radius=marker_radius,
            color="#FFFFFF",
            weight=2,
            fill=True,
            fill_color=fill_col,
            fill_opacity=0.95,
            tooltip=f"<b>[{urg}] {inc['title']}</b><br>Sector: {inc['sector']} | Confidence: {int(inc['confidence']*100)}%",
        ).add_to(m)

    return m


def build_road_risk_chart(scenario_name: str, roads_override: list[dict] | None = None) -> go.Figure:
    roads = (
        roads_override
        if roads_override is not None
        else get_synthetic_roads(scenario_name, manual_failed_roads=st.session_state.manual_failed_roads)
    )
    df_r = pd.DataFrame(roads).sort_values("vulnerability_score", ascending=True)
    color_map = {"BLOCKED": "#EF4444", "WARNING": "#F97316", "SAFE": "#22C55E"}
    colors = [color_map.get(s, "#38BDF8") for s in df_r["status"]]
    fig = go.Figure(
        data=[
            go.Bar(
                y=df_r["road_id"] + " (" + df_r["name"].str.split().str[0] + ")",
                x=df_r["vulnerability_score"],
                orientation="h",
                marker_color=colors,
                text=[f"{v} ({s})" for v, s in zip(df_r["vulnerability_score"], df_r["status"])],
                textposition="auto",
            )
        ]
    )
    fig.update_layout(
        title=dict(text="Corridor Flood Vulnerability & Closure Risk (Synthetic)", font=dict(size=14, color="#F8FAFC")),
        paper_bgcolor="#111C33",
        plot_bgcolor="#111C33",
        font=dict(color="#CBD5E1", size=12),
        margin=dict(l=10, r=18, t=42, b=24),
        height=320,
        xaxis=dict(range=[0, 112], gridcolor="#1E293B", title="Vulnerability Score (0–100)"),
        yaxis=dict(gridcolor="#1E293B"),
    )
    return fig


def build_vulnerability_vs_impact_chart(df_roads: pd.DataFrame) -> go.Figure:
    df_sorted = df_roads.sort_values("critical_rank", ascending=False)
    fig = go.Figure()
    fig.add_trace(
        go.Bar(name="Vulnerability Score (0–100)", y=df_sorted["road_id"], x=df_sorted["vulnerability_score"], orientation="h", marker_color="#F97316")
    )
    fig.add_trace(
        go.Bar(name="Population Impact (x100 residents)", y=df_sorted["road_id"], x=(df_sorted["population_impact"] / 100.0).round(1), orientation="h", marker_color="#38BDF8")
    )
    fig.update_layout(
        barmode="group",
        title=dict(text="Road Criticality: Vulnerability vs. Population Impact (Synthetic)", font=dict(size=14, color="#F8FAFC")),
        paper_bgcolor="#111C33",
        plot_bgcolor="#111C33",
        font=dict(color="#CBD5E1", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=15, r=15, t=55, b=25),
        height=330,
        xaxis=dict(gridcolor="#1E293B"),
    )
    return fig


def build_horizon_projection_chart(all_horizons: dict[int, dict]) -> go.Figure:
    labels = [HORIZON_LABELS[h] for h in HORIZONS_MINUTES]
    safe_counts = [all_horizons[h]["safe_count"] for h in HORIZONS_MINUTES]
    warn_counts = [all_horizons[h]["warning_count"] for h in HORIZONS_MINUTES]
    block_counts = [all_horizons[h]["blocked_count"] for h in HORIZONS_MINUTES]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="SAFE Roads", x=labels, y=safe_counts, marker_color="#22C55E"))
    fig.add_trace(go.Bar(name="WARNING Roads", x=labels, y=warn_counts, marker_color="#F97316"))
    fig.add_trace(go.Bar(name="BLOCKED Roads", x=labels, y=block_counts, marker_color="#EF4444"))
    fig.update_layout(
        barmode="stack",
        title=dict(text="Projected Corridor Deterioration Over Time (Synthetic)", font=dict(size=14, color="#F8FAFC")),
        paper_bgcolor="#111C33",
        plot_bgcolor="#111C33",
        font=dict(color="#CBD5E1", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=15, r=15, t=55, b=25),
        height=310,
        yaxis=dict(range=[0, 9], gridcolor="#1E293B", title="Road Corridors"),
    )
    return fig


@st.cache_data(show_spinner=False)
def _get_cached_rainfall_sensitivity(scenario_name: str, manual_failed_tuple: tuple[str, ...]) -> dict[str, list]:
    return compute_rainfall_sensitivity_curve(
        scenario_name,
        manual_failed_roads=set(manual_failed_tuple),
    )


def build_rainfall_sensitivity_chart(
    scenario_name: str,
    current_rain: float,
    manual_failed_roads: set[str],
) -> go.Figure:
    curve = _get_cached_rainfall_sensitivity(scenario_name, tuple(sorted(manual_failed_roads)))
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            name="Hospital Accessibility (%)",
            x=curve["rain_samples"],
            y=curve["access_curve"],
            mode="lines+markers",
            line=dict(color="#38BDF8", width=3),
            marker=dict(size=8),
        )
    )
    fig.add_trace(
        go.Scatter(
            name="Blocked Corridors at T+60 (%)",
            x=curve["rain_samples"],
            y=curve["blocked_pct_curve"],
            mode="lines+markers",
            line=dict(color="#EF4444", width=2, dash="dot"),
            marker=dict(size=7),
        )
    )
    fig.add_vline(
        x=current_rain,
        line_dash="dash",
        line_color="#FACC15",
        annotation_text=f"Selected: {int(current_rain)} mm/hr",
        annotation_font_color="#FACC15",
    )
    fig.update_layout(
        title=dict(text="Rainfall Sensitivity Curve: Network Collapse Threshold", font=dict(size=14, color="#F8FAFC")),
        paper_bgcolor="#111C33",
        plot_bgcolor="#111C33",
        font=dict(color="#CBD5E1", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=15, r=15, t=55, b=28),
        height=310,
        xaxis=dict(gridcolor="#1E293B", title="Rainfall Intensity (mm/hr)"),
        yaxis=dict(range=[0, 110], gridcolor="#1E293B", title="Percentage / Index"),
    )
    return fig


def build_strategy_comparison_chart(df_comp: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    short_names = [s.split("–")[0].strip() for s in df_comp["Strategy"]]
    fig.add_trace(
        go.Bar(name="Avg Dispatch ETA (min)", x=short_names, y=df_comp["Avg Dispatch ETA (min)"], marker_color="#38BDF8", text=df_comp["Avg Dispatch ETA (min)"], textposition="auto")
    )
    fig.add_trace(
        go.Bar(name="Flood-Warning Exposures", x=short_names, y=df_comp["Flood-Warning Road Exposures"], marker_color="#F97316", text=df_comp["Flood-Warning Road Exposures"], textposition="auto")
    )
    fig.add_trace(
        go.Bar(name="Unreachable Incidents", x=short_names, y=df_comp["Unreachable Incidents"], marker_color="#EF4444", text=df_comp["Unreachable Incidents"], textposition="auto")
    )
    fig.update_layout(
        barmode="group",
        title=dict(text="Strategy A vs B vs C Comparison (Synthetic)", font=dict(size=14, color="#F8FAFC")),
        paper_bgcolor="#111C33",
        plot_bgcolor="#111C33",
        font=dict(color="#CBD5E1", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=15, r=15, t=55, b=25),
        height=320,
        yaxis=dict(gridcolor="#1E293B"),
    )
    return fig


def build_benchmark_response_time_chart(df_bench: pd.DataFrame) -> go.Figure:
    short_names = [s.split("–")[0].strip() for s in df_bench["Strategy"]]
    colors = ["#EF4444", "#F97316", "#22C55E"]
    fig = go.Figure(
        data=[
            go.Bar(
                x=short_names,
                y=df_bench["Avg Emergency Response Time (min)"],
                marker_color=colors[: len(short_names)],
                text=[f"{v} min" for v in df_bench["Avg Emergency Response Time (min)"]],
                textposition="auto",
            )
        ]
    )
    fig.update_layout(
        title=dict(text="1. Average Emergency Response Time (Lower = Better)", font=dict(size=13, color="#F8FAFC")),
        paper_bgcolor="#111C33",
        plot_bgcolor="#111C33",
        font=dict(color="#CBD5E1", size=11),
        margin=dict(l=15, r=15, t=42, b=20),
        height=290,
        yaxis=dict(gridcolor="#1E293B", title="Minutes"),
    )
    return fig


def build_benchmark_utilization_chart(df_bench: pd.DataFrame) -> go.Figure:
    short_names = [s.split("–")[0].strip() for s in df_bench["Strategy"]]
    colors = ["#94A3B8", "#38BDF8", "#A855F7"]
    fig = go.Figure(
        data=[
            go.Bar(
                x=short_names,
                y=df_bench["Resource Utilisation (%)"],
                marker_color=colors[: len(short_names)],
                text=[f"{v}%" for v in df_bench["Resource Utilisation (%)"]],
                textposition="auto",
            )
        ]
    )
    fig.update_layout(
        title=dict(text="2. Fleet Resource Utilisation Across Active Incidents (%)", font=dict(size=13, color="#F8FAFC")),
        paper_bgcolor="#111C33",
        plot_bgcolor="#111C33",
        font=dict(color="#CBD5E1", size=11),
        margin=dict(l=15, r=15, t=42, b=20),
        height=290,
        yaxis=dict(range=[0, 115], gridcolor="#1E293B", title="Utilisation (%)"),
    )
    return fig


def build_benchmark_reachability_chart(df_bench: pd.DataFrame, thresh_col_name: str) -> go.Figure:
    short_names = [s.split("–")[0].strip() for s in df_bench["Strategy"]]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(name=thresh_col_name, x=short_names, y=df_bench[thresh_col_name], marker_color="#22C55E", text=df_bench[thresh_col_name], textposition="auto")
    )
    fig.add_trace(
        go.Bar(name="Blocked-Road Violations", x=short_names, y=df_bench["Blocked-Road Assignments"], marker_color="#EF4444", text=df_bench["Blocked-Road Assignments"], textposition="auto")
    )
    fig.update_layout(
        barmode="group",
        title=dict(text=f"3. Incidents Reached Quickly vs. Blocked Violations ({thresh_col_name})", font=dict(size=13, color="#F8FAFC")),
        paper_bgcolor="#111C33",
        plot_bgcolor="#111C33",
        font=dict(color="#CBD5E1", size=11),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=15, r=15, t=55, b=20),
        height=290,
        yaxis=dict(gridcolor="#1E293B", title="Incident Count"),
    )
    return fig


def build_benchmark_hospital_pop_chart(df_bench: pd.DataFrame) -> go.Figure:
    short_names = [s.split("–")[0].strip() for s in df_bench["Strategy"]]
    fig = go.Figure(
        data=[
            go.Bar(
                x=short_names,
                y=df_bench["Population Retaining Hospital Access"],
                marker_color=["#64748B", "#3B82F6", "#22D3EE"][: len(short_names)],
                text=[f"{v:,}" for v in df_bench["Population Retaining Hospital Access"]],
                textposition="auto",
            )
        ]
    )
    fig.update_layout(
        title=dict(text="4. Hospital Accessibility & Safe Access Population (Synthetic)", font=dict(size=13, color="#F8FAFC")),
        paper_bgcolor="#111C33",
        plot_bgcolor="#111C33",
        font=dict(color="#CBD5E1", size=11),
        margin=dict(l=15, r=15, t=42, b=20),
        height=290,
        yaxis=dict(range=[0, 42000], gridcolor="#1E293B", title="Residents"),
    )
    return fig


# ---------------------------------------------------------------------------
# 4. SIDEBAR NAVIGATION, MODE TOGGLE & SCENARIO CONTROLS
# ---------------------------------------------------------------------------
NAV_SECTIONS = [
    "1. RESQ-AI Overview",
    "2. Infrastructure Resilience & Flood Vulnerability",
    "3. Rainfall Simulation",
    "4. Cascading Failures & Facilities",
    "5. Emergency Intelligence",
    "6. Rescue Route Planning",
    "7. Resource Allocation & Strategy Comparison",
    "8. Benchmark & Audit",
]

osm_payload = _cached_osm_payload()
corridor_snapshot = _cached_corridor_snapshot()
external_osm_ready = osm_data_available()

with st.sidebar:
    st.markdown(
        """
        <div style="padding: 8px 0 12px 0; border-bottom: 1px solid #1E293B; margin-bottom: 12px;">
            <div style="font-size: 1.4rem; font-weight: 800; color: #F8FAFC; letter-spacing: 1px;">
                🛡️ RESQ-AI
            </div>
            <div style="font-size: 0.76rem; color: #38BDF8; font-weight: 600; margin-top: 2px;">
                DISASTER INTELLIGENCE & EOC
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    mode_options = ["Real Bengaluru OSM Network", "Synthetic Prototype Mode"]
    default_mode_idx = 0 if (get_mode() == "osm" and osm_payload is not None) else 1
    active_mode_label = st.radio(
        "ACTIVE NETWORK MODE",
        options=mode_options,
        index=default_mode_idx,
        help="Switch seamlessly between Member 3's Real Bengaluru OSM Network and Member 1/2 Synthetic Prototype Mode.",
    )
    is_osm_mode = active_mode_label == "Real Bengaluru OSM Network"

    if is_osm_mode and osm_payload is None:
        st.warning("Member 3 payload JSON missing (`data/processed/member3_dashboard_payload.json`). Reverting to Synthetic Prototype Mode.")
        is_osm_mode = False

    st.markdown("---")
    selected_section = st.radio("NAVIGATION SECTIONS", options=NAV_SECTIONS, index=0)
    st.markdown("---")

    scenario_list = get_scenario_names()
    if "selected_synthetic_scenario" not in st.session_state:
        st.session_state.selected_synthetic_scenario = scenario_list[1]

    if not is_osm_mode:
        st.markdown("**SIMULATION SCENARIO (PROTOTYPE)**")
        cur_scen = st.session_state.selected_synthetic_scenario
        selected_scenario = st.selectbox(
            "Active Disaster Profile",
            options=scenario_list,
            index=scenario_list.index(cur_scen) if cur_scen in scenario_list else 1,
        )
        st.session_state.selected_synthetic_scenario = selected_scenario

        if st.session_state.last_logged_scenario is None:
            st.session_state.last_logged_scenario = selected_scenario
        elif st.session_state.last_logged_scenario != selected_scenario:
            append_audit_event(
                st.session_state.audit_log,
                stage="SIMULATE",
                action_type="Disaster Scenario Switched",
                details=f"Operator changed active profile to '{selected_scenario}'",
            )
            st.session_state.last_logged_scenario = selected_scenario
            st.session_state.future_rainfall_override = None
    else:
        st.markdown("**BENGALURU OSM NETWORK CONTROLS**")
        selected_scenario = st.session_state.selected_synthetic_scenario
        if st.session_state.last_logged_scenario is None:
            st.session_state.last_logged_scenario = selected_scenario
        osm_tile_choice = st.selectbox(
            "Bengaluru Base Map Tiles",
            options=["OpenStreetMap", "CartoDB positron"],
            index=0,
        )

    extra_inc_count = len(st.session_state.custom_incidents)
    extra_crit_count = sum(1 for item in st.session_state.custom_incidents if item.get("urgency") == "CRITICAL")
    metrics = get_overview_metrics(
        selected_scenario,
        manual_failed_roads=st.session_state.manual_failed_roads,
        extra_incidents_count=extra_inc_count,
        extra_critical_count=extra_crit_count,
    )
    active_roads = get_synthetic_roads(selected_scenario, manual_failed_roads=st.session_state.manual_failed_roads)
    total_roads_count = len(active_roads)

    if is_osm_mode:
        live_status = "Configured (Live Corridor Ready)" if external_osm_ready else f"Offline Snapshot Only ({ENV_DATA_DIR} unset)"
        st.markdown(
            f"""
            <div style="background:#111C33; border:1px solid #1E293B; border-radius:8px; padding:10px 12px; font-size:0.77rem;">
                <div style="color:#94A3B8; font-weight:600;">REAL BENGALURU OSM TELEMETRY</div>
                <div style="color:#38BDF8; font-weight:700; margin-top:2px;">🗺️ Precomputed Payload + Geo-Snapshot</div>
                <div style="color:#CBD5E1; margin-top:5px;">
                    City Graph: <b>437,698 nodes</b><br/>
                    Corridor Extract: <b>32,722 nodes</b><br/>
                    Live OSM Data: <b>{html.escape(live_status)}</b><br/>
                    Audit Entries: <b>{len(st.session_state.audit_log)}</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div style="background:#111C33; border:1px solid #1E293B; border-radius:8px; padding:10px 12px; font-size:0.78rem;">
                <div style="color:#94A3B8; font-weight:600;">DATA MODE & SESSION STATE</div>
                <div style="color:#FACC15; font-weight:700; margin-top:2px;">⚠️ Synthetic Prototype Mode</div>
                <div style="color:#CBD5E1; margin-top:4px;">
                    Simulated Rainfall: <b>{metrics['rainfall_mm_hr']} mm/hr</b><br/>
                    Manual Failed Roads: <b>{len(st.session_state.manual_failed_roads)}</b><br/>
                    Session Reports Added: <b>{extra_inc_count}</b><br/>
                    Audit Chain Entries: <b>{len(st.session_state.audit_log)}</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# 5. TOP COMMAND HEADER & CLOSED-LOOP WORKFLOW BANNER
# ---------------------------------------------------------------------------
header_status_label = "● BENGALURU OSM CORRIDOR" if is_osm_mode else f"● {metrics['status_level']}"
header_status_color = "#38BDF8" if is_osm_mode else metrics["status_color"]
context_badge = "Bengaluru OSM (437,698 Nodes / Corridor 32,722)" if is_osm_mode else f"Scenario: {selected_scenario}"

st.markdown(
    f"""
    <div class="eoc-header">
        <div>
            <div class="eoc-title">🛡️ RESQ-AI</div>
            <div class="eoc-subtitle">
                Human-Centric Disaster Intelligence, Infrastructure Resilience & Autonomous Emergency Response Network
            </div>
            <div class="eoc-tagline">
                Predict the failure. Protect the connection. Save the response time.
            </div>
        </div>
        <div style="text-align: right;">
            <div style="font-size:0.72rem; color:#94A3B8; margin-bottom:4px; font-weight:600;">
                ACTIVE COMMAND CONTEXT
            </div>
            <span class="status-badge" style="background-color:{header_status_color}25; color:{header_status_color}; border-color:{header_status_color};">
                {html.escape(header_status_label)}
            </span>
        </div>
    </div>
    <div class="workflow-bar">
        <div class="workflow-steps">
            <b>CLOSED-LOOP WORKFLOW:</b>
            <span>1. OBSERVE</span> →
            <span>2. ESTIMATE</span> →
            <span>3. SIMULATE</span> →
            <span>4. OPTIMIZE</span> →
            <span>5. VERIFY</span> →
            <span>6. REPEAT</span>
        </div>
        <div style="color:#38BDF8; font-weight:600;">
            {html.escape(context_badge)}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# 6. SECTION RENDERERS — REAL BENGALURU OSM MODE
# ---------------------------------------------------------------------------
def _render_osm_section(section: str) -> None:
    assert osm_payload is not None
    df_incidents_now = get_active_incidents_df(selected_scenario)

    if section == NAV_SECTIONS[0]:
        _render_provenance_badges([
            ("Real Bengaluru OSM Road Network", "#38BDF8"),
            ("Vulnerability: Estimated from OSM Tags", "#F97316"),
            ("Facilities: Unverified OSM Records", "#3B82F6"),
            ("Demand: Synthetic Scenario Assumption", "#A855F7"),
        ])
        _render_kpi_cards(get_osm_overview_kpis(osm_payload))

        map_c, side_c = st.columns([1.65, 1.0], gap="large")
        with map_c:
            st.markdown(
                '<div class="section-header">🗺️ BENGALURU CENTRAL CORRIDOR COMMAND MAP (ARTERIALS • FLOOD RISK • FACILITIES • ROUTES)</div>',
                unsafe_allow_html=True,
            )
            if corridor_snapshot is None:
                st.info("Corridor geo-snapshot JSON is absent; displaying Target Hospital & incident anchors only.")
            osm_map = build_bengaluru_osm_map(
                osm_payload,
                corridor_snapshot,
                tile_layer=osm_tile_choice,
                focus="overview",
                incidents_df=df_incidents_now,
            )
            st_folium(osm_map, use_container_width=True, height=540, returned_objects=[])

        with side_c:
            st.markdown(
                '<div class="section-header">🚨 CRITICAL BENGALURU UNDERPASS & ACCESS WARNINGS</div>',
                unsafe_allow_html=True,
            )
            for rec in osm_payload.get("phase8_active_observation_plan", {}).get("recommendations", [])[:4]:
                is_blk = rec.get("condition") == "BLOCKED"
                card_cls = "alert-card-critical" if is_blk else "alert-card-warning"
                col_hex = "#EF4444" if is_blk else "#F97316"
                road_label = rec.get("name") or f"OSM Way {rec.get('road_id')}"
                reason = (rec.get("inspection_reasons") or ["High observation priority"])[0]
                st.markdown(
                    f"""
                    <div class="{card_cls}">
                        <div class="alert-header">
                            <span style="color:{col_hex};">● {html.escape(str(rec.get('condition')))} • Rank #{rec.get('rank')}</span>
                            <span style="color:#94A3B8;">Score {rec.get('observation_priority_score')}</span>
                        </div>
                        <div class="alert-title">{html.escape(str(road_label))} ({html.escape(str(rec.get('highway')))})</div>
                        <div class="alert-detail">{html.escape(str(reason))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.plotly_chart(build_vulnerability_distribution_chart(osm_payload, scope="central_corridor"), width="stretch")

        c_bot1, c_bot2 = st.columns([1.25, 1.0], gap="large")
        with c_bot1:
            st.markdown('<div class="section-header">📋 LIVE SESSION AUDIT STREAM</div>', unsafe_allow_html=True)
            st.dataframe(get_audit_dataframe(st.session_state.audit_log)[["Timestamp", "Stage", "Action", "Details"]].head(8), width="stretch", hide_index=True)
        with c_bot2:
            st.markdown('<div class="section-header">📊 SYSTEM SCALE METADATA</div>', unsafe_allow_html=True)
            p1 = osm_payload.get("phase1_network_validation", {})
            st.dataframe(
                pd.DataFrame([
                    {"Metric": "Full City Nodes", "Value": f"{p1.get('total_nodes', 0):,}"},
                    {"Metric": "Full City Directed Edges", "Value": f"{p1.get('total_directed_edges', 0):,}"},
                    {"Metric": "Unique City OSM Ways", "Value": f"{p1.get('total_unique_road_ways', 0):,}"},
                    {"Metric": "Central Corridor Nodes", "Value": f"{p1.get('central_corridor_nodes', 0):,}"},
                    {"Metric": "Central Corridor Edges", "Value": f"{p1.get('central_corridor_directed_edges', 0):,}"},
                    {"Metric": "Validation Status", "Value": str(p1.get("validation_status", "PASS"))},
                ]),
                width="stretch",
                hide_index=True,
            )

    elif section == NAV_SECTIONS[1]:
        _render_provenance_badges([
            ("Estimated from OSM Tags (highway, tunnel, bridge, surface, lanes)", "#F97316"),
            ("Not direct hydrological flood-depth sensors", "#94A3B8"),
        ])
        scope = st.radio(
            "Select Flood Vulnerability Scope",
            options=["central_corridor", "full_city"],
            format_func=lambda k: "Central Bengaluru Corridor (9,521 Unique Ways)" if k == "central_corridor" else "Full Bengaluru City (135,302 Unique Ways)",
            horizontal=True,
        )
        col_ch, col_tbl = st.columns([1.25, 1.0], gap="large")
        with col_ch:
            st.plotly_chart(build_vulnerability_distribution_chart(osm_payload, scope=scope), width="stretch")
        with col_tbl:
            st.markdown('<div class="section-header">📊 VULNERABILITY TIER DISTRIBUTION</div>', unsafe_allow_html=True)
            st.dataframe(get_vulnerability_summary_df(osm_payload, scope=scope), width="stretch", hide_index=True)
            note = osm_payload.get("phase2_vulnerability", {}).get(scope, {}).get("methodology_note", "")
            if note:
                st.caption(note)

        st.markdown('<div class="section-header">🌊 TOP FLOOD-VULNERABLE BENGALURU ROADS & UNDERPASSES (CORRIDOR EXTRACT)</div>', unsafe_allow_html=True)
        live_graph_for_table = st.session_state.osm_live_rainfall["latest_graph"] if st.session_state.osm_live_rainfall else None
        st.dataframe(get_top_vulnerable_roads_df(corridor_snapshot, live_graph_for_table), width="stretch", hide_index=True)

        m1_arts = load_member1_artifacts()
        with st.expander("📁 Optional Member 1 (16-Node Prototype Pipeline) Reference Artifacts", expanded=False):
            if m1_arts["available"]:
                for fname, df_art in m1_arts["csv_files"].items():
                    st.markdown(f"**{fname}**")
                    st.dataframe(df_art, width="stretch", hide_index=True)
                for ppath in m1_arts["png_files"]:
                    st.image(ppath, caption=Path(ppath).name)
            else:
                st.caption("No generated Member 1 `outputs/` files found in this workspace. Run `python main.py` if standalone 16-node CSV/PNG artifacts are needed.")

    elif section == NAV_SECTIONS[2]:
        _render_provenance_badges([
            ("Hypothetical Rainfall Stress-Test (Not a live weather forecast)", "#FACC15"),
            ("Impact = Rainfall Intensity × Est. Vulnerability (≥70 BLOCKED, ≥40 AT RISK)", "#F97316"),
        ])
        ctrl1, ctrl2, ctrl3 = st.columns([1.2, 1.0, 1.0], gap="large")
        with ctrl1:
            rain_now = st.slider("Corridor Starting Rainfall (mm/hr)", 0, 100, 55, step=5)
        with ctrl2:
            rain_inc = st.slider("Intensity Increase per 15 min", 0, 25, 10, step=5)
        with ctrl3:
            st.markdown("<div style='height:26px;'></div>", unsafe_allow_html=True)
            if external_osm_ready:
                if st.button("🌧️ Run Live Corridor Rainfall Simulation (32,722 Nodes)", width="stretch"):
                    g_corr = _cached_corridor_graph()
                    st.session_state.osm_live_rainfall = run_live_corridor_rainfall(g_corr, rain_now, rain_inc)
                    append_audit_event(
                        st.session_state.audit_log,
                        stage="SIMULATE",
                        action_type="Live Bengaluru Corridor Rainfall Run",
                        details=f"Ran T+0..T+60 progression starting at {rain_now} mm/hr (+{rain_inc}/15m) on 32,722-node corridor.",
                    )
            else:
                st.info(f"Precomputed mode active. Set `{ENV_DATA_DIR}` to enable live corridor re-simulation.")

        live_scenarios = st.session_state.osm_live_rainfall["scenarios"] if st.session_state.osm_live_rainfall else None
        prog_df = get_corridor_progression_df(osm_payload, live_scenarios=live_scenarios)

        c1, c2 = st.columns([1.3, 1.1], gap="large")
        with c1:
            st.plotly_chart(build_corridor_rainfall_progression_chart(prog_df), width="stretch")
        with c2:
            st.markdown('<div class="section-header">⏱️ CENTRAL CORRIDOR PROGRESSION (T+0 TO T+60)</div>', unsafe_allow_html=True)
            st.dataframe(prog_df, width="stretch", hide_index=True)

        full_85 = osm_payload.get("phase3_rainfall_simulation", {}).get("full_city_heavy_rainfall_85", {})
        st.markdown('<div class="section-header">🏙️ FULL-CITY STRESS-TEST SNAPSHOT (85 MM/HR HYPOTHETICAL)</div>', unsafe_allow_html=True)
        fw = full_85.get("unique_road_way_counts", {})
        fk = full_85.get("road_length_km", {})
        _render_kpi_cards([
            {"label": "Stress Rainfall", "value": f"{full_85.get('rainfall_intensity', 85)} mm/hr", "sub": "Hypothetical citywide test", "color": "#FACC15"},
            {"label": "Open Road Ways", "value": f"{fw.get('OPEN', 0):,}", "sub": f"{fk.get('OPEN', 0):,.1f} km passable", "color": "#22C55E"},
            {"label": "At-Risk Road Ways", "value": f"{fw.get('AT RISK', 0):,}", "sub": f"{fk.get('AT RISK', 0):,.1f} km caution", "color": "#F97316"},
            {"label": "Blocked Road Ways", "value": f"{fw.get('BLOCKED', 0):,}", "sub": f"{fk.get('BLOCKED', 0):,.1f} km impassable", "color": "#EF4444"},
            {"label": "Blocked Bridges", "value": f"{full_85.get('blocked_bridge_ways', 0)}", "sub": "OSM bridge ways blocked", "color": "#38BDF8"},
            {"label": "Blocked Tunnels", "value": f"{full_85.get('blocked_tunnel_ways', 0)}", "sub": "Underpasses / tunnels flooded", "color": "#A855F7"},
        ])

    elif section == NAV_SECTIONS[3]:
        _render_provenance_badges([
            ("Unverified OSM Facilities (Crowd-sourced PBF, deduplicated Nodes/Ways/Relations)", "#3B82F6"),
            ("Affected Population: Synthetic Scenario Assumption", "#A855F7"),
        ])
        p4 = osm_payload.get("phase4_cascading_and_facilities", {})
        conn = p4.get("connectivity_impact", {})
        pop_imp = p4.get("population_impact", {})
        if st.session_state.osm_live_routing and "post_connectivity" in st.session_state.osm_live_routing:
            post_comp = st.session_state.osm_live_routing["post_connectivity"]
            base_comp = st.session_state.osm_live_routing["baseline_connectivity"]
            conn_display = {
                "baseline_components": base_comp["num_components"],
                "post_failure_components": post_comp["num_components"],
                "new_components_created": post_comp["num_components"] - base_comp["num_components"],
                "newly_disconnected_node_count": max(0, base_comp["largest_component_size"] - post_comp["largest_component_size"]),
                "failed_unique_road_ways": conn.get("failed_unique_road_ways", 0),
            }
        else:
            conn_display = conn

        _render_kpi_cards([
            {"label": "Baseline Components", "value": f"{conn_display.get('baseline_components', 0)}", "sub": "Weakly connected subgraphs", "color": "#38BDF8"},
            {"label": "Post-Failure Components", "value": f"{conn_display.get('post_failure_components', 0)}", "sub": f"+{conn_display.get('new_components_created', 0)} fragments created", "color": "#EF4444"},
            {"label": "Disconnected Nodes", "value": f"{conn_display.get('newly_disconnected_node_count', 0)}", "sub": "Separated from main cluster", "color": "#F97316"},
            {"label": "Failed Unique Ways", "value": f"{conn.get('failed_unique_road_ways', 0)}", "sub": f"{conn.get('failed_directed_edges', 0)} directed edges closed", "color": "#EF4444"},
            {"label": "Non-Emergency Excluded", "value": f"{p4.get('excluded_non_emergency_shelters', 0)}", "sub": "Gazebos / bus shelters filtered out", "color": "#22C55E"},
            {"label": "Affected Pop. (Synth)", "value": f"{pop_imp.get('total_affected_population', 0):,}", "sub": f"Delayed: {pop_imp.get('delayed_access_population', 0)}", "color": "#A855F7"},
        ])

        impact_df = get_facility_impact_df(osm_payload)
        f_col1, f_col2 = st.columns([1.2, 1.15], gap="large")
        with f_col1:
            st.plotly_chart(build_facility_impact_chart(impact_df), width="stretch")
            st.dataframe(impact_df, width="stretch", hide_index=True)
        with f_col2:
            st.markdown('<div class="section-header">🏥 DEDUPLICATED BENGALURU OSM EMERGENCY FACILITIES (CITYWIDE)</div>', unsafe_allow_html=True)
            st.dataframe(get_facility_counts_df(osm_payload), width="stretch", hide_index=True)
            st.caption(p4.get("verification_disclaimer", ""))

    elif section == NAV_SECTIONS[4]:
        _render_provenance_badges([
            ("Simulated Evidence Mode: evidence.py rule scoring active", "#FACC15"),
            ("Pending from Member 2: image_analysis.py, confidence.py, storage.py (NLP/CV/DB)", "#F97316"),
            ("OSM Bridge: Verified non-duplicate reports snap to nearest Bengaluru nodes", "#38BDF8"),
        ])
        ev_metrics = summarize_evidence_metrics(df_incidents_now)
        _render_kpi_cards([
            {"label": "Active Reports", "value": f"{len(df_incidents_now)}", "sub": f"Session added: {len(st.session_state.custom_incidents)}", "color": "#3B82F6"},
            {"label": "Critical Urgency", "value": f"{ev_metrics['critical_count']}", "sub": "High-priority dispatches", "color": "#EF4444"},
            {"label": "Verified Reports", "value": f"{ev_metrics['verified_count']} / {len(df_incidents_now)}", "sub": "Cleared for OSM routing", "color": "#22C55E"},
            {"label": "Duplicate Warnings", "value": f"{ev_metrics['duplicate_flagged_count']}", "sub": "Simulated checkbox holds", "color": "#F97316"},
            {"label": "Mean Confidence", "value": f"{ev_metrics['mean_confidence_pct']}%", "sub": "Rule-based prototype score", "color": "#A855F7"},
            {"label": "OSM Node Snapper", "value": "LIVE" if external_osm_ready else "PREVIEW", "sub": "incident_bridge ready", "color": "#38BDF8"},
        ])

        rep_col, form_col = st.columns([1.55, 1.0], gap="large")
        with rep_col:
            st.markdown('<div class="section-header">📡 EMERGENCY REPORTS & OSM NODE SNAPPING QUEUE</div>', unsafe_allow_html=True)
            graph_for_snap = _cached_corridor_graph() if external_osm_ready else None
            snapped_df, _ = snap_emergency_reports_to_corridor(df_incidents_now, corridor_graph=graph_for_snap, snapshot=corridor_snapshot)
            cols_show = ["incident_id", "sector", "type", "urgency", "verified", "OSM Node", "Snap (m)", "OSM Dispatch Queue"]
            st.dataframe(snapped_df[cols_show], width="stretch", hide_index=True)

            unverified_ids = df_incidents_now[df_incidents_now["verified"] == False]["incident_id"].tolist()  # noqa: E712
            if unverified_ids:
                vc1, vc2 = st.columns([1.4, 1.0])
                with vc1:
                    inc_verify = st.selectbox("Verify Pending Incident", options=unverified_ids)
                with vc2:
                    st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
                    if st.button("✅ Mark Verified & Allow OSM Dispatch", width="stretch"):
                        st.session_state.verified_overrides[inc_verify] = True
                        append_audit_event(
                            st.session_state.audit_log,
                            stage="VERIFY",
                            action_type="Emergency Report Verified",
                            details=f"Verified {inc_verify} for Bengaluru OSM rescue dispatch.",
                        )
                        st.rerun()

        with form_col:
            st.markdown('<div class="section-header">➕ INGEST EMERGENCY REPORT (MEMBER 2 SIMULATED INTAKE)</div>', unsafe_allow_html=True)
            with st.form("osm_emergency_intake", clear_on_submit=True):
                rep_title = st.text_input("Incident Summary", placeholder="e.g., Ambulance stranded near K R Market")
                rep_sector = st.selectbox("Sector Coordinates", options=list(SECTOR_COORDINATES.keys()))
                rep_type = st.selectbox("Disaster Type", options=["Flash Flood Entrapment", "Medical Evacuation", "Infrastructure Failure", "Road Obstruction"])
                rep_urgency = st.selectbox("Urgency", options=["CRITICAL", "WARNING"])
                sim_dup = st.checkbox("Simulate Duplicate Image Warning (Member 2 Test)", value=False)
                if st.form_submit_button("🚨 Score & Queue Incident", width="stretch"):
                    try:
                        new_inc = score_emergency_report(
                            title=rep_title,
                            sector=rep_sector,
                            disaster_type=rep_type,
                            urgency=rep_urgency,
                            simulate_duplicate=sim_dup,
                            existing_custom_count=len(st.session_state.custom_incidents),
                        )
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        new_id = new_inc["incident_id"]
                        calc_conf = new_inc["confidence"]
                        dup_status = new_inc["duplicate_warning"]
                        st.session_state.custom_incidents.insert(0, new_inc)
                        append_audit_event(
                            st.session_state.audit_log,
                            stage="OBSERVE",
                            action_type="Emergency Report Submitted (OSM Mode)",
                            details=f"{new_id} at {rep_sector} ({rep_type}, Urgency: {rep_urgency}).",
                        )
                        append_audit_event(
                            st.session_state.audit_log,
                            stage="VERIFY",
                            action_type="Confidence Score Calculated",
                            details=(
                                f"{new_id} scored at {int(calc_conf*100)}% confidence | "
                                f"Duplicate Check: {dup_status}"
                            ),
                        )
                        st.rerun()

    elif section == NAV_SECTIONS[5]:
        _render_provenance_badges([
            ("Real Directed One-Way & MultiDiGraph Dijkstra Routing", "#22C55E"),
            ("Phase 8 Active Observation Priorities", "#FACC15"),
            ("Hospital Record: Unverified OSM Entry", "#3B82F6"),
        ])
        p5 = osm_payload.get("phase5_rescue_routing", {})
        target_hosp = p5.get("target_hospital", {})
        rc1, rc2, rc3 = st.columns([1.2, 1.0, 1.1], gap="large")
        with rc1:
            opt_mode = st.selectbox("Optimization Objective", options=["time", "distance"], index=0)
        with rc2:
            rain_route = st.slider("Corridor Flood Level (mm/hr)", 0, 100, 95, step=5)
        with rc3:
            st.markdown("<div style='height:26px;'></div>", unsafe_allow_html=True)
            if external_osm_ready:
                if st.button("🧭 Recalculate Primary & Alternative OSM Routes", width="stretch"):
                    g_corr = _cached_corridor_graph()
                    orig = str(p5.get("dispatch_origin_node", ""))
                    dest = str(target_hosp.get("nearest_node", ""))
                    st.session_state.osm_live_routing = run_live_corridor_routing(
                        g_corr,
                        orig,
                        dest,
                        rainfall_intensity=rain_route,
                        optimize_for=opt_mode,
                    )
                    append_audit_event(
                        st.session_state.audit_log,
                        stage="OPTIMIZE",
                        action_type="Live Bengaluru Rescue Routes Computed",
                        details=f"Computed Primary & Detour paths to {target_hosp.get('name')} @ {rain_route} mm/hr ({opt_mode}).",
                    )
            else:
                st.info(f"Precomputed Phase 5 route active. Set `{ENV_DATA_DIR}` to re-route live.")

        live_rt = st.session_state.osm_live_routing
        map_c, tbl_c = st.columns([1.45, 1.1], gap="large")
        with map_c:
            st.markdown(f'<div class="section-header">🗺️ RESCUE CORRIDORS TO {html.escape(str(target_hosp.get("name", "TARGET HOSPITAL")).upper())}</div>', unsafe_allow_html=True)
            rt_map = build_bengaluru_osm_map(
                osm_payload,
                corridor_snapshot,
                tile_layer=osm_tile_choice,
                focus="routing",
                live_primary_coords=live_rt["primary_coords"] if live_rt else None,
                live_alt_coords=live_rt["alternative_coords"] if live_rt else None,
            )
            st_folium(rt_map, use_container_width=True, height=520, returned_objects=[])
        with tbl_c:
            st.markdown('<div class="section-header">🚑 PRIMARY VS. ALTERNATIVE ROUTE METRICS</div>', unsafe_allow_html=True)
            st.dataframe(get_rescue_routes_df(osm_payload, live_routing=live_rt), width="stretch", hide_index=True)
            st.markdown('<div class="section-header" style="margin-top:14px;">🔭 PHASE 8 ACTIVE OBSERVATION PRIORITIES</div>', unsafe_allow_html=True)
            obs_list = live_rt["observations"] if live_rt else None
            st.dataframe(get_active_observations_df(osm_payload, live_observations=obs_list), width="stretch", hide_index=True)

    elif section == NAV_SECTIONS[6]:
        _render_provenance_badges([
            ("Demand & Catchment Populations: Synthetic Scenario Assumption", "#A855F7"),
            ("Optimized on Real OSM Corridor Distances & Conditions", "#22C55E"),
        ])
        ac1, ac2, ac3 = st.columns([1.2, 1.0, 1.1], gap="large")
        with ac1:
            strat_choice = st.selectbox(
                "Allocation Strategy",
                options=["budget_aware_optimized", "highest_priority_first", "nearest_resource_first"],
                index=0,
            )
        with ac2:
            budget_limit = st.slider("Emergency Dispatch Budget (₹)", 1000, 6000, 3200, step=200)
        with ac3:
            st.markdown("<div style='height:26px;'></div>", unsafe_allow_html=True)
            if external_osm_ready:
                if st.button("⚖️ Optimize Allocation on Snapped Incidents", width="stretch"):
                    g_corr = _cached_corridor_graph()
                    st.session_state.osm_live_allocation = run_live_corridor_allocation(
                        g_corr, df_incidents_now, strategy=strat_choice, total_budget=float(budget_limit)
                    )
                    append_audit_event(
                        st.session_state.audit_log,
                        stage="OPTIMIZE",
                        action_type="Live Corridor Resource Allocation",
                        details=f"Optimized Member 2 verified queue under '{strat_choice}' (Budget ₹{budget_limit}).",
                    )

        live_alloc = st.session_state.osm_live_allocation
        comp_df = get_strategy_comparison_df(osm_payload, live_comparison=live_alloc["comparison"] if live_alloc else None)
        alloc_df, loc_df = get_allocations_df(osm_payload, live_allocation=live_alloc["allocation"] if live_alloc else None)

        ch_c, tb_c = st.columns([1.15, 1.2], gap="large")
        with ch_c:
            st.plotly_chart(build_osm_strategy_comparison_chart(comp_df), width="stretch")
        with tb_c:
            st.markdown('<div class="section-header">🏆 PHASE 7 STRATEGY COMPARISON</div>', unsafe_allow_html=True)
            st.dataframe(comp_df, width="stretch", hide_index=True)
            rec_reason = osm_payload.get("phase7_strategy_comparison", {}).get("recommendation_reason", "")
            if rec_reason:
                st.success(rec_reason)

        b_c1, b_c2 = st.columns(2, gap="large")
        with b_c1:
            st.markdown('<div class="section-header">🚑 PHASE 6 RESOURCE ASSIGNMENTS</div>', unsafe_allow_html=True)
            st.dataframe(alloc_df, width="stretch", hide_index=True)
        with b_c2:
            st.markdown('<div class="section-header">📍 ZONE COVERAGE & UNSERVED DEMAND (SYNTHETIC)</div>', unsafe_allow_html=True)
            st.dataframe(loc_df, width="stretch", hide_index=True)

    else:
        _render_shared_benchmark_and_audit(is_osm=True)


# ---------------------------------------------------------------------------
# 7. SHARED SECTION 8 (BENCHMARK & SHA-256 HASH-CHAINED AUDIT)
# ---------------------------------------------------------------------------
def _render_shared_benchmark_and_audit(is_osm: bool = False) -> None:
    if is_osm and osm_payload is not None:
        st.markdown(
            '<div class="section-header">⚖️ PART 1: BENGALURU OSM RESCUE STRATEGY BENCHMARK SUMMARY</div>',
            unsafe_allow_html=True,
        )
        live_alloc = st.session_state.osm_live_allocation
        comp_df = get_strategy_comparison_df(
            osm_payload,
            live_comparison=live_alloc["comparison"] if live_alloc else None,
        )
        if live_alloc:
            st.caption("Showing live Section 7 corridor resource allocation comparison for the active emergency queue.")
        st.plotly_chart(build_osm_strategy_comparison_chart(comp_df), width="stretch")
        st.dataframe(comp_df, width="stretch", hide_index=True)
    else:
        df_inc_bench = get_active_incidents_df(selected_scenario)
        st.markdown(
            '<div class="section-header">⚖️ PART 1: STRATEGY PERFORMANCE BENCHMARKING (SYNTHETIC SIMULATION)</div>',
            unsafe_allow_html=True,
        )
        b_ctrl1, b_ctrl2 = st.columns([1.2, 1.4], gap="large")
        with b_ctrl1:
            thresh_min = st.slider(
                "Target Response Time Threshold (minutes)",
                min_value=3.0,
                max_value=15.0,
                value=8.0,
                step=1.0,
            )
        with b_ctrl2:
            st.markdown(
                textwrap.dedent(
                    f"""\
                    <div class="kpi-card" style="min-height:auto; border-left:4px solid #38BDF8; padding:10px 14px;">
                    <div class="kpi-label">BENCHMARK METHODOLOGY (IDENTICAL INPUTS)</div>
                    <div style="font-size:0.8rem; color:#CBD5E1; line-height:1.45;">
                    All 3 strategies are evaluated on the exact same synthetic graph (<code>{html.escape(selected_scenario)}</code>),
                    manual road closures (<b>{len(st.session_state.manual_failed_roads)}</b>), and incident queue (<b>{len(df_inc_bench)} reports</b>).
                    </div>
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )
        bench_res = run_benchmark_evaluation(
            scenario_name=selected_scenario,
            incidents_df=df_inc_bench,
            manual_failed_roads=st.session_state.manual_failed_roads,
            response_threshold_min=float(thresh_min),
        )
        df_bench = bench_res["summary_df"]
        sa, sb, sc_row = bench_res["strategy_a"], bench_res["strategy_b"], bench_res["strategy_c"]
        thresh_col = f"Reached <= {int(thresh_min)} min"

        _render_kpi_cards([
            {"label": "Avg Simulated ETA", "value": f"{sc_row['Avg Emergency Response Time (min)']}m", "sub": f"A: {sa['Avg Emergency Response Time (min)']}m | B: {sb['Avg Emergency Response Time (min)']}m", "color": "#22C55E"},
            {"label": "Total Mission Dist.", "value": f"{sc_row['Total Travel Distance (km)']} km", "sub": f"A: {sa['Total Travel Distance (km)']} | B: {sb['Total Travel Distance (km)']}", "color": "#38BDF8"},
            {"label": "Blocked-Road Routes", "value": f"{sc_row['Blocked-Road Assignments']}", "sub": f"Baseline A hits {sa['Blocked-Road Assignments']} blocked", "color": "#22C55E"},
            {"label": thresh_col, "value": f"{sc_row[thresh_col]} / {sc_row['Reached Incidents']}", "sub": f"A: {sa[thresh_col]} | B: {sb[thresh_col]}", "color": "#F97316"},
            {"label": "Safe Hospital Access", "value": f"{sc_row['Hospital Accessibility (%)']}%", "sub": f"{sc_row['Population Retaining Hospital Access']:,} connected", "color": "#3B82F6"},
            {"label": "Resource Utilisation", "value": f"{sc_row['Resource Utilisation (%)']}%", "sub": f"Duplicate holds saved: {bench_res['unverified_held_count']}", "color": "#A855F7"},
        ])

        r1c1, r1c2 = st.columns(2, gap="large")
        with r1c1:
            st.plotly_chart(build_benchmark_response_time_chart(df_bench), width="stretch")
        with r1c2:
            st.plotly_chart(build_benchmark_utilization_chart(df_bench), width="stretch")
        r2c1, r2c2 = st.columns(2, gap="large")
        with r2c1:
            st.plotly_chart(build_benchmark_reachability_chart(df_bench, thresh_col), width="stretch")
        with r2c2:
            st.plotly_chart(build_benchmark_hospital_pop_chart(df_bench), width="stretch")
        st.dataframe(df_bench, width="stretch", hide_index=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div class="section-header">🔐 PART 2: TAMPER-EVIDENT SHA-256 HASH-CHAINED AUDIT LOG (NOT A BLOCKCHAIN)</div>',
        unsafe_allow_html=True,
    )
    audit_check = verify_audit_chain_detailed(st.session_state.audit_log)
    is_chain_ok = audit_check["overall_valid"]
    badge_bg = "#22C55E" if is_chain_ok else "#EF4444"

    aud_c1, aud_c2, aud_c3 = st.columns([1.35, 0.85, 0.85], gap="medium")
    with aud_c1:
        st.markdown(
            f"""
            <div class="kpi-card" style="min-height:auto; border-left:4px solid {badge_bg}; padding:12px 16px;">
                <div class="kpi-label">CRYPTOGRAPHIC SHA-256 AUDIT CHAIN STATUS</div>
                <div style="font-size:1.1rem; font-weight:800; color:{badge_bg}; margin-bottom:4px;">
                    {'✅ ' if is_chain_ok else '🚨 '}{html.escape(audit_check['status_label'])} ({len(st.session_state.audit_log)} Recorded Events)
                </div>
                <div style="font-size:0.8rem; color:#CBD5E1;">{html.escape(audit_check['summary_message'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with aud_c2:
        if st.button("🔍 VERIFY AUDIT INTEGRITY", width="stretch"):
            recheck = verify_audit_chain_detailed(st.session_state.audit_log)
            if recheck["overall_valid"]:
                st.success(f"VERIFIED: {recheck['summary_message']}")
            else:
                st.error(f"INTEGRITY FAILURE: {recheck['summary_message']}")
        if st.button("📋 Log Current Verification Cycle", width="stretch"):
            append_audit_event(
                st.session_state.audit_log,
                stage="REPEAT",
                action_type="RESQ-AI Status Verified",
                details=f"Operator logged status cycle under {'OSM' if is_osm else 'Synthetic'} mode.",
            )
            st.rerun()
    with aud_c3:
        if st.button("🧪 Simulate Tampering on AUD-002 (Demo)", width="stretch"):
            if len(st.session_state.audit_log) >= 2:
                st.session_state.audit_log[1]["details"] = "TAMPERED RECORD: Unauthorized edit to verification score"
                st.rerun()
        if st.button("🔄 Restore Intact Audit Log", width="stretch"):
            st.session_state.audit_log = create_initial_audit_log()
            st.rerun()

    df_audit_full = get_audit_dataframe(st.session_state.audit_log)[
        ["Event ID", "Event Type", "Stage", "Timestamp", "Event Description", "Previous Hash", "Current Hash", "Verification Status"]
    ]
    st.dataframe(df_audit_full, width="stretch", hide_index=True)


# ---------------------------------------------------------------------------
# 8. SECTION RENDERERS — SYNTHETIC PROTOTYPE MODE
# ---------------------------------------------------------------------------
def _render_synthetic_section(section: str) -> None:
    if section == NAV_SECTIONS[0]:
        _render_kpi_cards([
            {"label": "Disaster Status", "value": metrics["status_level"], "sub": f"Rain: {metrics['rainfall_mm_hr']} mm/hr (Sim)", "color": metrics["status_color"]},
            {"label": "Total Incidents", "value": f"{metrics['total_incidents']}", "sub": "Active reports in queue", "color": "#F97316"},
            {"label": "Critical Incidents", "value": f"{metrics['critical_incidents']}", "sub": "Immediate life-safety risk", "color": "#EF4444"},
            {"label": "Blocked Roads", "value": f"{metrics['blocked_roads']} / {total_roads_count}", "sub": "Primary corridors closed", "color": "#EF4444"},
            {"label": "Available Ambulances", "value": f"{metrics['available_ambulances']} / {metrics['total_ambulances']}", "sub": "Ready for dispatch", "color": "#A855F7"},
            {"label": "Affected Population", "value": f"{metrics['affected_population']:,}", "sub": "Estimated in flood zones", "color": "#3B82F6"},
        ])

        map_col, alert_col = st.columns([1.75, 1.0], gap="large")
        with map_col:
            st.markdown('<div class="section-header">🗺️ SYNTHETIC CITY COMMAND MAP (PROTOTYPE DATA — NOT LIVE GIS)</div>', unsafe_allow_html=True)
            st_folium(build_eoc_city_map(selected_scenario, roads_override=active_roads), use_container_width=True, height=540, returned_objects=[])
        with alert_col:
            st.markdown('<div class="section-header">🚨 CRITICAL ALERTS & VERIFICATION WARNINGS</div>', unsafe_allow_html=True)
            for alert in get_critical_alerts(selected_scenario):
                is_crit = alert["severity"] == "CRITICAL"
                cls = "alert-card-critical" if is_crit else "alert-card-warning"
                col = "#EF4444" if is_crit else "#F97316"
                st.markdown(
                    f"""
                    <div class="{cls}">
                        <div class="alert-header"><span style="color:{col};">● {alert['severity']} • {alert['code']}</span><span style="color:#94A3B8;">{alert['time']} (Sim)</span></div>
                        <div class="alert-title">{alert['title']}</div>
                        <div class="alert-detail">{alert['detail']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.plotly_chart(build_road_risk_chart(selected_scenario, roads_override=active_roads), width="stretch")

        act_col, unit_col = st.columns([1.45, 1.0], gap="large")
        with act_col:
            st.markdown('<div class="section-header">📋 RECENT SYSTEM ACTIVITY</div>', unsafe_allow_html=True)
            df_act = get_audit_dataframe(st.session_state.audit_log)[["Timestamp", "Stage", "Action", "Details"]].head(8) if st.session_state.audit_log else get_recent_activity()
            st.dataframe(df_act, width="stretch", hide_index=True)
        with unit_col:
            st.markdown('<div class="section-header">🚑 DEPLOYED RESCUE UNITS (SYNTHETIC)</div>', unsafe_allow_html=True)
            st.dataframe(get_synthetic_rescue_teams()[["unit_id", "type", "status", "assigned_sector"]], width="stretch", hide_index=True)

    elif section == NAV_SECTIONS[1]:
        res_bundle = assess_road_network_resilience(selected_scenario, manual_failed_roads=st.session_state.manual_failed_roads, roads_override=active_roads)
        roads_list = res_bundle["roads_list"]
        df_roads = res_bundle["roads_df"]
        reval = res_bundle["resilience_eval"]
        g_pass = res_bundle["passable_graph"]

        _render_kpi_cards([
            {"label": "NetworkX Graph Nodes", "value": f"{g_pass.number_of_nodes()} Junctions", "sub": "3 Hospital Hubs • 6 Sectors", "color": "#3B82F6"},
            {"label": "Passable Road Edges", "value": f"{g_pass.number_of_edges()} / {len(roads_list)}", "sub": "Active edges in routing graph", "color": "#22C55E"},
            {"label": "Blocked Corridors", "value": f"{len(roads_list) - g_pass.number_of_edges()}", "sub": f"Manual Failures: {len(st.session_state.manual_failed_roads)}", "color": "#EF4444"},
            {"label": "Hospital Reachability", "value": f"{reval['hospital_access_pct']}%", "sub": f"{reval['connected_population']:,} residents connected", "color": "#38BDF8"},
            {"label": "Isolated Population", "value": f"{reval['isolated_population']:,}", "sub": "Sectors without hospital path", "color": "#F97316"},
            {"label": "Graph Connectivity", "value": "INTACT" if reval["is_fully_connected"] else f"{reval['num_connected_components']} SUBGRAPHS", "sub": "Connected components", "color": "#22C55E" if reval["is_fully_connected"] else "#F97316"},
        ])

        sim_col, map_col2 = st.columns([1.05, 1.55], gap="large")
        with sim_col:
            st.markdown('<div class="section-header">🛠️ INTERACTIVE ROAD FAILURE SIMULATOR</div>', unsafe_allow_html=True)
            road_options = [f"{r['road_id']} • {r['name']} [{r['status']}]" for r in roads_list]
            sel_label = st.selectbox("Select Corridor to Stress-Test", options=road_options)
            sel_id = sel_label.split(" • ")[0].strip()
            hyp = simulate_single_road_failure(selected_scenario, road_id=sel_id, existing_failed_roads=st.session_state.manual_failed_roads)
            st.info(f"Closing **{sel_id}** projects Hospital Access to **{hyp['post_failure_access_pct']}%** (Isolated Pop: **{hyp['isolated_population']:,}**).")
            bc1, bc2 = st.columns(2)
            with bc1:
                if st.button(f"💥 Simulate Failure ({sel_id})", width="stretch"):
                    if sel_id not in st.session_state.manual_failed_roads:
                        st.session_state.manual_failed_roads.add(sel_id)
                        append_audit_event(st.session_state.audit_log, stage="ESTIMATE", action_type="Road Marked Unavailable", details=f"Simulated failure on {sel_id}.")
                        st.rerun()
            with bc2:
                if st.button("🔄 Reset Road Failures", width="stretch"):
                    if st.session_state.manual_failed_roads:
                        st.session_state.manual_failed_roads.clear()
                        append_audit_event(st.session_state.audit_log, stage="ESTIMATE", action_type="Road Network Restored", details="Cleared manually simulated road closures.")
                        st.rerun()
            st.plotly_chart(build_vulnerability_vs_impact_chart(df_roads), width="stretch")

        with map_col2:
            st.markdown(f'<div class="section-header">🗺️ ROAD NETWORK MAP (HIGHLIGHTING {sel_id})</div>', unsafe_allow_html=True)
            st_folium(build_eoc_city_map(selected_scenario, highlight_road_id=sel_id, roads_override=roads_list), use_container_width=True, height=500, returned_objects=[])

        tc1, tc2 = st.columns(2, gap="large")
        with tc1:
            st.dataframe(reval["sector_df"], width="stretch", hide_index=True)
        with tc2:
            st.dataframe(res_bundle["critical_rankings_df"], width="stretch", hide_index=True)

        m1_arts = load_member1_artifacts()
        with st.expander("📁 Optional Member 1 (16-Node Pipeline) Outputs Inspector", expanded=False):
            if m1_arts["available"]:
                for fname, df_art in m1_arts["csv_files"].items():
                    st.markdown(f"**{fname}**")
                    st.dataframe(df_art, width="stretch", hide_index=True)
            else:
                st.caption("No Member 1 standalone CSV/PNG artifacts present under `outputs/`.")

    elif section in (NAV_SECTIONS[2], NAV_SECTIONS[3]):
        default_rain = int(st.session_state.future_rainfall_override) if st.session_state.future_rainfall_override is not None else int(metrics["rainfall_mm_hr"])
        cc1, cc2, cc3 = st.columns([1.3, 1.0, 0.9], gap="large")
        with cc1:
            sim_rain = st.slider("Simulated Rainfall Intensity (0–150 mm/hr)", 0, 150, default_rain, step=5)
            st.session_state.future_rainfall_override = sim_rain
        with cc2:
            default_h_idx = (
                HORIZONS_MINUTES.index(st.session_state.future_horizon_min)
                if st.session_state.future_horizon_min in HORIZONS_MINUTES
                else 2
            )
            sel_h = st.selectbox(
                "Select Horizon View",
                options=HORIZONS_MINUTES,
                index=default_h_idx,
                format_func=lambda h: HORIZON_LABELS.get(h, f"T+{h} min"),
            )
            st.session_state.future_horizon_min = sel_h
        with cc3:
            st.markdown("<div style='height:26px;'></div>", unsafe_allow_html=True)
            if st.button("📝 Log Future Projection to Audit Trail", width="stretch"):
                append_audit_event(
                    st.session_state.audit_log,
                    stage="SIMULATE",
                    action_type="Future Projection Evaluated",
                    details=(
                        f"Simulated {sim_rain} mm/hr across T+15/T+30/T+60 horizons "
                        f"(Inspecting {HORIZON_LABELS[sel_h]})."
                    ),
                )
                st.success("Projection logged to SHA-256 Audit Trail.")

        all_horizons = simulate_all_horizons(selected_scenario, rainfall_mm_hr=float(sim_rain), manual_failed_roads=st.session_state.manual_failed_roads)
        h0, h15, h30, h60, hsel = all_horizons[0], all_horizons[15], all_horizons[30], all_horizons[60], all_horizons[sel_h]

        _render_kpi_cards([
            {"label": "Simulated Rainfall", "value": f"{sim_rain} mm/hr", "sub": f"Base: {metrics['rainfall_mm_hr']} mm/hr", "color": "#38BDF8"},
            {"label": "Current (T+0)", "value": f"{h0['blocked_count']} Blocked", "sub": f"Hospital Access: {h0['hospital_access_pct']}%", "color": "#22C55E"},
            {"label": "+15 Min Projection", "value": f"{h15['blocked_count']} Blocked", "sub": f"Access: {h15['hospital_access_pct']}%", "color": "#FACC15"},
            {"label": "+30 Min Projection", "value": f"{h30['blocked_count']} Blocked", "sub": f"Access: {h30['hospital_access_pct']}%", "color": "#F97316"},
            {"label": "+60 Min Projection", "value": f"{h60['blocked_count']} Blocked", "sub": f"Access: {h60['hospital_access_pct']}%", "color": "#EF4444"},
            {"label": "T+60 Isolated Pop.", "value": f"{h60['isolated_population']:,}", "sub": "Cut off at +60m", "color": "#A855F7"},
        ])

        if section == NAV_SECTIONS[2]:
            mc, cc = st.columns([1.4, 1.15], gap="large")
            with mc:
                st_folium(build_eoc_city_map(selected_scenario, roads_override=hsel["roads"]), use_container_width=True, height=500, returned_objects=[])
            with cc:
                st.plotly_chart(build_horizon_projection_chart(all_horizons), width="stretch")
                st.plotly_chart(build_rainfall_sensitivity_chart(selected_scenario, float(sim_rain), st.session_state.manual_failed_roads), width="stretch")
            st.dataframe(build_road_progression_df(all_horizons), width="stretch", hide_index=True)
        else:
            casc = get_cascading_impacts_and_observations(all_horizons)
            c1, c2 = st.columns(2, gap="large")
            with c1:
                st.markdown('<div class="section-header">⚡ CASCADING INFRASTRUCTURE IMPACT (SYNTHETIC)</div>', unsafe_allow_html=True)
                st.dataframe(casc["cascading_df"], width="stretch", hide_index=True)
                st.markdown('<div class="section-header">⏱️ HORIZON ACCESSIBILITY SUMMARY</div>', unsafe_allow_html=True)
                st.dataframe(build_horizon_comparison_df(all_horizons), width="stretch", hide_index=True)
            with c2:
                st.markdown(f'<div class="section-header">🏥 SECTOR-TO-HOSPITAL REACHABILITY ({HORIZON_LABELS[sel_h].upper()})</div>', unsafe_allow_html=True)
                st.dataframe(hsel["sector_df"], width="stretch", hide_index=True)
                st.markdown('<div class="section-header">🔭 ACTIVE OBSERVATION SENSORS (SYNTHETIC)</div>', unsafe_allow_html=True)
                st.dataframe(casc["observations_df"], width="stretch", hide_index=True)

    elif section == NAV_SECTIONS[4]:
        _render_provenance_badges([
            ("Simulated Evidence Mode: evidence.py rule scoring", "#FACC15"),
            ("Pending from Member 2: image_analysis.py, confidence.py, storage.py", "#F97316"),
        ])
        df_inc_all = get_active_incidents_df(selected_scenario)
        ev_metrics = summarize_evidence_metrics(df_inc_all)
        open_count = sum(1 for r in active_roads if r["status"] != "BLOCKED")
        _render_kpi_cards([
            {"label": "Active Reports", "value": f"{len(df_inc_all)}", "sub": f"Added: {len(st.session_state.custom_incidents)}", "color": "#3B82F6"},
            {"label": "Critical Urgency", "value": f"{ev_metrics['critical_count']}", "sub": "Immediate priority", "color": "#EF4444"},
            {"label": "Verified Reports", "value": f"{ev_metrics['verified_count']} / {len(df_inc_all)}", "sub": "Cleared by evidence check", "color": "#22C55E"},
            {"label": "Duplicate Warnings", "value": f"{ev_metrics['duplicate_flagged_count']}", "sub": "Simulated checkbox test", "color": "#F97316"},
            {"label": "Mean Confidence", "value": f"{ev_metrics['mean_confidence_pct']}%", "sub": "Rule-based score", "color": "#A855F7"},
            {"label": "Passable Corridors", "value": f"{open_count} / {len(active_roads)}", "sub": "Available routes", "color": "#22C55E"},
        ])

        rep_col, form_col = st.columns([1.55, 1.0], gap="large")
        with rep_col:
            fc1, fc2 = st.columns(2)
            with fc1:
                u_filt = st.selectbox("Filter by Urgency", options=["ALL", "CRITICAL", "WARNING"], index=0)
            with fc2:
                v_filt = st.selectbox("Filter by Verification", options=["ALL", "Verified Only", "Pending / Unverified Only"], index=0)
            df_filt = filter_incident_reports(df_inc_all, urgency_filter=u_filt, verify_filter=v_filt)
            st.dataframe(df_filt[["incident_id", "reported_at", "sector", "type", "urgency", "confidence", "duplicate_warning", "verified", "title"]], width="stretch", hide_index=True)
            unverified_ids = df_inc_all[df_inc_all["verified"] == False]["incident_id"].tolist()  # noqa: E712
            if unverified_ids:
                vc1, vc2 = st.columns([1.4, 1.0])
                with vc1:
                    inc_to_verify = st.selectbox("Select Unverified Report", options=unverified_ids)
                with vc2:
                    st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
                    if st.button("✅ Mark Selected Report Verified", width="stretch"):
                        st.session_state.verified_overrides[inc_to_verify] = True
                        append_audit_event(st.session_state.audit_log, stage="VERIFY", action_type="Emergency Report Verified", details=f"Manually verified {inc_to_verify}.")
                        st.rerun()

        with form_col:
            with st.form("submit_emergency_report_form", clear_on_submit=True):
                rep_title = st.text_input("Incident Summary", placeholder="e.g., Waterlogged Ambulance Trapped")
                rep_sector = st.selectbox("Incident Sector", options=list(SECTOR_COORDINATES.keys()))
                rep_type = st.selectbox("Disaster Type", options=["Flash Flood Entrapment", "Medical Evacuation", "Infrastructure Failure", "Road Obstruction"])
                rep_urgency = st.selectbox("Urgency Level", options=["CRITICAL", "WARNING"])
                sim_dup = st.checkbox("Simulate Duplicate Image Warning (Member 2 Test)", value=False)
                if st.form_submit_button("🚨 Ingest Emergency Report", width="stretch"):
                    try:
                        new_inc = score_emergency_report(title=rep_title, sector=rep_sector, disaster_type=rep_type, urgency=rep_urgency, simulate_duplicate=sim_dup, existing_custom_count=len(st.session_state.custom_incidents))
                    except ValueError as err:
                        st.error(str(err))
                    else:
                        new_id = new_inc["incident_id"]
                        calc_conf = new_inc["confidence"]
                        dup_status = new_inc["duplicate_warning"]
                        st.session_state.custom_incidents.insert(0, new_inc)
                        append_audit_event(
                            st.session_state.audit_log,
                            stage="OBSERVE",
                            action_type="Emergency Report Received",
                            details=f"{new_id} submitted at {rep_sector} ({rep_type}, Urgency: {rep_urgency}).",
                        )
                        append_audit_event(
                            st.session_state.audit_log,
                            stage="VERIFY",
                            action_type="Confidence Score Calculated",
                            details=(
                                f"{new_id} scored at {int(calc_conf*100)}% confidence | "
                                f"Duplicate Check: {dup_status}"
                            ),
                        )
                        st.rerun()

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
        road_avail_col, prec_col = st.columns([1.2, 1.2], gap="large")
        with road_avail_col:
            st.markdown(
                '<div class="section-header">🛣️ CURRENT ROAD CORRIDOR AVAILABILITY (LIVE NETWORK STATE)</div>',
                unsafe_allow_html=True,
            )
            df_road_avail = pd.DataFrame(active_roads)[
                ["road_id", "name", "u", "v", "status", "reason"]
            ].rename(
                columns={
                    "road_id": "Road ID",
                    "name": "Corridor",
                    "u": "From",
                    "v": "To",
                    "status": "Availability",
                    "reason": "Operational Condition",
                }
            )
            st.dataframe(df_road_avail, width="stretch", hide_index=True)

        with prec_col:
            st.markdown(
                '<div class="section-header">🛡️ STANDARD OPERATING PRECAUTIONS BY DISASTER TYPE</div>',
                unsafe_allow_html=True,
            )
            prec_map = get_precautions_by_disaster_type()
            sel_prec = st.selectbox("Inspect Field Precautions for Disaster Category", options=list(prec_map.keys()))
            bullets_html = "".join(
                f"<li style='margin-bottom:6px;'>{html.escape(item)}</li>"
                for item in prec_map[sel_prec]
            )
            st.markdown(
                textwrap.dedent(
                    f"""\
                    <div class="kpi-card" style="min-height:auto; border-left:4px solid #22C55E;">
                    <div class="kpi-label">FIELD SAFETY PROTOCOL • {html.escape(sel_prec.upper())}</div>
                    <ul style="margin:8px 0 0 18px; padding:0; font-size:0.84rem; color:#E2E8F0; line-height:1.5;">
                    {bullets_html}
                    </ul>
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )

    elif section in (NAV_SECTIONS[5], NAV_SECTIONS[6]):
        df_inc_rescue = get_active_incidents_df(selected_scenario)
        strat_opts = get_strategy_names()
        s_col1, s_col2 = st.columns([1.4, 1.0], gap="large")
        with s_col1:
            chosen_strat = st.selectbox(
                "Select Rescue Dispatch & Routing Strategy",
                options=strat_opts,
                index=strat_opts.index(st.session_state.selected_rescue_strategy) if st.session_state.selected_rescue_strategy in strat_opts else 2,
            )
            st.session_state.selected_rescue_strategy = chosen_strat

            if st.session_state.last_logged_strategy != chosen_strat:
                append_audit_event(
                    st.session_state.audit_log,
                    stage="OPTIMIZE",
                    action_type="Rescue Route Updated & Strategy Selected",
                    details=f"Operator switched active dispatch optimization to '{chosen_strat}'.",
                )
                st.session_state.last_logged_strategy = chosen_strat

        plan_res = allocate_rescue_resources(selected_scenario, df_inc_rescue, strategy_name=chosen_strat, manual_failed_roads=st.session_state.manual_failed_roads)
        df_comp = compare_all_strategies(selected_scenario, df_inc_rescue, manual_failed_roads=st.session_state.manual_failed_roads)

        with s_col2:
            st.markdown(
                textwrap.dedent(
                    f"""\
                    <div class="kpi-card" style="min-height:auto; border-left:4px solid #A855F7; padding:12px 16px;">
                    <div class="kpi-label">{html.escape(str(plan_res['strategy_meta']['short_code']))} • OPTIMIZATION LOGIC</div>
                    <div style="font-size:0.83rem; color:#E2E8F0; line-height:1.45;">
                    {html.escape(str(plan_res['strategy_meta']['description']))}
                    </div>
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )

        _render_kpi_cards([
            {"label": "Selected Strategy", "value": plan_res["strategy_meta"]["short_code"], "sub": f"Weight: {plan_res['strategy_meta']['weight_attr']}", "color": "#A855F7"},
            {"label": "Incidents Reached", "value": f"{plan_res['assigned_count']} / {len(df_inc_rescue)}", "sub": "Valid NetworkX path", "color": "#22C55E"},
            {"label": "Unreachable", "value": f"{plan_res['unreachable_count']}", "sub": "Cut off by closures", "color": "#EF4444"},
            {"label": "Avg Dispatch ETA", "value": f"{plan_res['avg_response_eta_min']} min", "sub": f"Dist: {plan_res['avg_total_distance_km']} km", "color": "#38BDF8"},
            {"label": "Warning Exposures", "value": f"{plan_res['warning_corridor_exposures']}", "sub": "Using flood-warning links", "color": "#F97316"},
            {"label": "Unit Utilisation", "value": f"{plan_res['unit_utilization_pct']}%", "sub": f"Passable: {plan_res['passable_edges_count']}/{plan_res['total_edges_count']}", "color": "#3B82F6"},
        ])

        if section == NAV_SECTIONS[5]:
            mc, rc = st.columns([1.5, 1.05], gap="large")
            with mc:
                st_folium(build_eoc_city_map(selected_scenario, roads_override=active_roads, rescue_routes=plan_res["map_routes"]), use_container_width=True, height=520, returned_objects=[])
            with rc:
                st.markdown('<div class="section-header">🧭 DISPATCH ROUTE PATHS</div>', unsafe_allow_html=True)
                st.dataframe(plan_res["allocations_df"], width="stretch", hide_index=True)
        else:
            cc, tc = st.columns([1.2, 1.15], gap="large")
            with cc:
                st.plotly_chart(build_strategy_comparison_chart(df_comp), width="stretch")
                if st.button("🚑 Confirm & Dispatch Resource Allocation", width="stretch"):
                    append_audit_event(st.session_state.audit_log, stage="OPTIMIZE", action_type="Resource Assigned & Dispatched", details=f"Dispatched {plan_res['assigned_count']} mission(s) under {plan_res['strategy_meta']['short_code']}.")
                    st.success("Dispatch logged to SHA-256 Audit Trail!")
            with tc:
                st.dataframe(df_comp, width="stretch", hide_index=True)
                st.dataframe(plan_res["allocations_df"], width="stretch", hide_index=True)
            uc1, uc2 = st.columns(2, gap="large")
            with uc1:
                st.dataframe(get_synthetic_rescue_teams(), width="stretch", hide_index=True)
            with uc2:
                st.dataframe(get_synthetic_hospitals(), width="stretch", hide_index=True)

    else:
        _render_shared_benchmark_and_audit(is_osm=False)


# Route active section cleanly by mode
if is_osm_mode:
    _render_osm_section(selected_section)
else:
    _render_synthetic_section(selected_section)
