"""
app.py
------
SANJEEVANI — Emergency Operations Centre (EOC) Main Dashboard
Member 4: Dashboard UI, Interactive GIS Mapping, and System Integration.
"""

import html
import textwrap
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium

from sanjeevani.data import (
    CITY_CENTER,
    SYNTHETIC_JUNCTIONS,
    get_scenario_names,
    get_overview_metrics,
    get_synthetic_hospitals,
    get_synthetic_rescue_teams,
    get_synthetic_roads,
    get_synthetic_incidents,
    get_critical_alerts,
    get_recent_activity,
    get_precautions_by_disaster_type,
)
from sanjeevani.resilience import (
    assess_road_network_resilience,
    simulate_single_road_failure,
)
from sanjeevani.dashboard_evidence import (
    SECTOR_COORDINATES,
    score_emergency_report,
    filter_incident_reports,
    summarize_evidence_metrics,
)
from sanjeevani.audit import (
    create_initial_audit_log,
    append_audit_event,
    verify_audit_chain_detailed,
    get_audit_dataframe,
)
from sanjeevani.benchmark import run_benchmark_evaluation
from sanjeevani.twin import (
    HORIZONS_MINUTES,
    HORIZON_LABELS,
    simulate_all_horizons,
    compute_rainfall_sensitivity_curve,
    build_horizon_comparison_df,
    build_road_progression_df,
    get_cascading_impacts_and_observations,
)
from sanjeevani.decision import (
    get_strategy_names,
    allocate_rescue_resources,
    compare_all_strategies,
)

# ---------------------------------------------------------------------------
# 1. PAGE CONFIGURATION
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="SANJEEVANI | Disaster Intelligence & EOC",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# 2. PROFESSIONAL DARK NAVY EOC STYLING (CSS)
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Main Dark Navy Background & Typography */
    .stApp {
        background-color: #0B1120;
        color: #F8FAFC;
        font-family: 'Inter', 'Segoe UI', Roboto, Helvetica, sans-serif;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0F172A;
        border-right: 1px solid #1E293B;
    }

    /* Reduce top padding for command-center look */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2.5rem;
        max-width: 100%;
    }

    /* Header Banner */
    .eoc-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        border: 1px solid #334155;
        border-left: 5px solid #3B82F6;
        border-radius: 10px;
        padding: 18px 24px;
        margin-bottom: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 16px;
    }
    .eoc-title {
        font-size: 1.65rem;
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

    /* Status Pill in Header */
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

    /* Workflow Bar */
    .workflow-bar {
        background-color: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 8px;
        padding: 10px 18px;
        margin-bottom: 22px;
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

    /* Responsive 6-Card KPI Grid (prevents awkward text wrapping & keeps equal heights) */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(6, minmax(0, 1fr));
        gap: 14px;
        margin-bottom: 24px;
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

    /* KPI Metric Cards */
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

    /* Alert Cards */
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

    /* Section Card Wrapper */
    .section-header {
        font-size: 1.05rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid #1E293B;
    }

    /* Legend Badges */
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

    /* Make Folium iframe stretch cleanly across full column width */
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
# 2B. STREAMLIT SESSION STATE INITIALISATION
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
    st.session_state.selected_rescue_strategy = get_strategy_names()[2]  # Default to Strategy C

if "last_logged_strategy" not in st.session_state:
    st.session_state.last_logged_strategy = st.session_state.selected_rescue_strategy

if "future_rainfall_override" not in st.session_state:
    st.session_state.future_rainfall_override = None

if "future_horizon_min" not in st.session_state:
    st.session_state.future_horizon_min = 30


def get_active_incidents_df(scenario_name: str) -> pd.DataFrame:
    """Return base synthetic incidents combined with user-submitted session incidents."""
    base_df = get_synthetic_incidents(scenario_name).copy()
    if st.session_state.custom_incidents:
        custom_df = pd.DataFrame(st.session_state.custom_incidents)
        base_df = pd.concat([custom_df, base_df], ignore_index=True)

    # Apply any manual verification overrides from Section 3
    if st.session_state.verified_overrides:
        for idx, row in base_df.iterrows():
            inc_id = row["incident_id"]
            if inc_id in st.session_state.verified_overrides:
                base_df.at[idx, "verified"] = st.session_state.verified_overrides[inc_id]
    return base_df


# ---------------------------------------------------------------------------
# 3. HELPER FUNCTIONS FOR MAP & VISUALISATIONS
# ---------------------------------------------------------------------------
def build_eoc_city_map(
    scenario_name: str,
    highlight_road_id: str | None = None,
    roads_override: list[dict] | None = None,
    rescue_routes: list[dict] | None = None,
) -> folium.Map:
    """
    Build the interactive Folium GIS Command Map using colour-coded entities:
      - RED (#EF4444): Critical emergencies & blocked roads
      - ORANGE (#F97316): Warnings & vulnerable roads
      - GREEN (#22C55E): Safe / available road corridors
      - BLUE (#3B82F6): Hospitals & emergency medical centres
      - PURPLE (#A855F7): Rescue teams & ambulances
    """
    m = folium.Map(
        location=CITY_CENTER,
        zoom_start=13,
        tiles="CartoDB dark_matter",
        control_scale=True,
    )

    # 1. Draw Road Network Corridors (Green / Orange / Red)
    roads = (
        roads_override
        if roads_override is not None
        else get_synthetic_roads(
            scenario_name,
            manual_failed_roads=st.session_state.manual_failed_roads,
        )
    )
    color_map = {
        "SAFE": "#22C55E",     # Green
        "WARNING": "#F97316",  # Orange
        "BLOCKED": "#EF4444",  # Red
    }

    for road in roads:
        r_status = road["status"]
        r_color = color_map.get(r_status, "#3B82F6")
        dash_pattern = "8, 8" if r_status == "BLOCKED" else None
        is_highlighted = road["road_id"] == highlight_road_id

        popup_html = f"""
        <div style="font-family:sans-serif; min-width:210px;">
            <b>{road['road_id']}: {road['name']}</b><br/>
            <b>Nodes:</b> {road['u']} ↔ {road['v']} ({road['distance_km']} km)<br/>
            <b>Status:</b> <span style="color:{r_color};font-weight:bold;">{r_status}</span><br/>
            <b>Failure Prob:</b> {int(road['failure_prob']*100)}% | <b>Vuln Score:</b> {road['vulnerability_score']}/100<br/>
            <b>Pop. Impact:</b> {road['population_impact']:,}<br/>
            <b>Note:</b> {road['reason']}<br/>
            <i>(Synthetic Prototype Data)</i>
        </div>
        """
        folium.PolyLine(
            locations=road["coords"],
            color="#38BDF8" if is_highlighted else r_color,
            weight=8 if is_highlighted else (6 if r_status == "BLOCKED" else 5),
            opacity=0.95,
            dash_array=dash_pattern,
            tooltip=f"{road['road_id']} ({road['u']}↔{road['v']}) • {road['name']} [{r_status}]",
            popup=folium.Popup(popup_html, max_width=290),
        ).add_to(m)

    # 1B. Overlay Suggested Rescue Routes if provided (Section 5)
    if rescue_routes:
        for rt in rescue_routes:
            for seg in rt.get("leg1_coords", []):
                folium.PolyLine(
                    locations=seg,
                    color="#A855F7",
                    weight=6,
                    opacity=0.95,
                    dash_array="6, 10",
                    tooltip=f"🚑 Dispatch Route ({rt['unit_id']} → {rt['incident_id']}): {rt['leg1_roads']} [ETA {rt['eta_min']}m]",
                ).add_to(m)
            for seg in rt.get("leg2_coords", []):
                folium.PolyLine(
                    locations=seg,
                    color="#38BDF8",
                    weight=5,
                    opacity=0.9,
                    dash_array="4, 8",
                    tooltip=f"🏥 Evac Route ({rt['incident_id']} → {rt['hospital_id']}): {rt['leg2_roads']}",
                ).add_to(m)

    # 1B. Draw NetworkX Junction Nodes (subtle markers)
    for j_id, j_attr in SYNTHETIC_JUNCTIONS.items():
        folium.CircleMarker(
            location=[j_attr["lat"], j_attr["lon"]],
            radius=5,
            color="#94A3B8",
            fill=True,
            fill_color="#1E293B",
            fill_opacity=0.9,
            tooltip=f"📍 {j_attr['name']} (Pop: {j_attr['population']:,})",
        ).add_to(m)

    # 2. Draw Hospitals (BLUE)
    hospitals = get_synthetic_hospitals()
    for _, hosp in hospitals.iterrows():
        folium.CircleMarker(
            location=[hosp["lat"], hosp["lon"]],
            radius=9,
            color="#3B82F6",
            fill=True,
            fill_color="#3B82F6",
            fill_opacity=0.9,
            tooltip=f"🏥 {hosp['hospital_id']}: {hosp['name']} (Free ICU: {hosp['icu_beds_free']})",
            popup=folium.Popup(
                f"<b>{hosp['name']}</b><br>ID: {hosp['hospital_id']}<br>"
                f"Free ICU Beds: {hosp['icu_beds_free']}<br>Status: {hosp['status']}<br>"
                f"<i>(Synthetic Prototype Data)</i>",
                max_width=250,
            ),
        ).add_to(m)

    # 3. Draw Rescue Teams & Ambulances (PURPLE)
    teams = get_synthetic_rescue_teams()
    for _, unit in teams.iterrows():
        folium.CircleMarker(
            location=[unit["lat"], unit["lon"]],
            radius=8,
            color="#A855F7",
            fill=True,
            fill_color="#A855F7",
            fill_opacity=0.9,
            tooltip=f"🚑 {unit['unit_id']}: {unit['type']} [{unit['status']}]",
            popup=folium.Popup(
                f"<b>{unit['unit_id']}</b><br>Type: {unit['type']}<br>"
                f"Status: {unit['status']}<br>Sector: {unit['assigned_sector']}<br>"
                f"<i>(Synthetic Prototype Data)</i>",
                max_width=250,
            ),
        ).add_to(m)

    # 4. Draw Emergency Incidents (RED for Critical, ORANGE for Warning)
    incidents = get_active_incidents_df(scenario_name)
    for _, inc in incidents.iterrows():
        inc_color = "#EF4444" if inc["urgency"] == "CRITICAL" else "#F97316"
        safe_title = html.escape(str(inc["title"]))
        safe_type = html.escape(str(inc["type"]))
        folium.CircleMarker(
            location=[inc["lat"], inc["lon"]],
            radius=10 if inc["urgency"] == "CRITICAL" else 8,
            color=inc_color,
            fill=True,
            fill_color=inc_color,
            fill_opacity=0.95,
            tooltip=f"⚠️ {inc['incident_id']} [{inc['urgency']}]: {safe_title}",
            popup=folium.Popup(
                f"<b>{inc['incident_id']}: {safe_title}</b><br>"
                f"Urgency: <b style='color:{inc_color};'>{inc['urgency']}</b><br>"
                f"Type: {safe_type}<br>"
                f"Evidence Confidence: {int(inc['confidence']*100)}%<br>"
                f"Duplicate Check: {inc.get('duplicate_warning', 'Clear')}<br>"
                f"Verified: {'Yes' if inc['verified'] else 'Pending Check'}<br>"
                f"<i>(Synthetic Prototype Data)</i>",
                max_width=260,
            ),
        ).add_to(m)

    return m


def build_road_risk_chart(
    scenario_name: str,
    roads_override: list[dict] | None = None,
) -> go.Figure:
    """Build a compact Plotly bar chart showing synthetic road failure probability."""
    roads = (
        roads_override
        if roads_override is not None
        else get_synthetic_roads(
            scenario_name,
            manual_failed_roads=st.session_state.manual_failed_roads,
        )
    )
    df_roads = pd.DataFrame(roads)

    color_lookup = {
        "SAFE": "#22C55E",
        "WARNING": "#F97316",
        "BLOCKED": "#EF4444",
    }
    bar_colors = [color_lookup.get(s, "#3B82F6") for s in df_roads["status"]]

    fig = go.Figure(
        go.Bar(
            x=[round(p * 100, 1) for p in df_roads["failure_prob"]],
            y=df_roads["road_id"] + " (" + df_roads["status"] + ")",
            orientation="h",
            marker_color=bar_colors,
            text=[f"{int(p * 100)}%" for p in df_roads["failure_prob"]],
            textposition="outside",
        )
    )
    fig.update_layout(
        title=dict(
            text="Synthetic Road Failure Probability (%)",
            font=dict(size=14, color="#F8FAFC"),
        ),
        paper_bgcolor="#111C33",
        plot_bgcolor="#111C33",
        font=dict(color="#CBD5E1", size=11),
        margin=dict(l=10, r=35, t=38, b=20),
        height=265,
        xaxis=dict(range=[0, 115], gridcolor="#1E293B", title="Failure Risk (%)"),
        yaxis=dict(autorange="reversed"),
    )
    return fig


def build_vulnerability_vs_impact_chart(df_roads: pd.DataFrame) -> go.Figure:
    """Build a Plotly chart comparing road vulnerability score and affected population."""
    color_lookup = {
        "SAFE": "#22C55E",
        "WARNING": "#F97316",
        "BLOCKED": "#EF4444",
    }
    bar_colors = [color_lookup.get(s, "#3B82F6") for s in df_roads["status"]]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df_roads["road_id"],
            y=df_roads["vulnerability_score"],
            name="Vulnerability Score (0-100)",
            marker_color=bar_colors,
            text=df_roads["vulnerability_score"],
            textposition="outside",
        )
    )
    fig.update_layout(
        title=dict(
            text="Road Infrastructure Vulnerability Score by Corridor (Synthetic)",
            font=dict(size=14, color="#F8FAFC"),
        ),
        paper_bgcolor="#111C33",
        plot_bgcolor="#111C33",
        font=dict(color="#CBD5E1", size=11),
        margin=dict(l=15, r=15, t=42, b=25),
        height=310,
        yaxis=dict(range=[0, 112], gridcolor="#1E293B", title="Vulnerability Score"),
        xaxis=dict(title="Synthetic Road Segment ID"),
    )
    return fig


def build_horizon_projection_chart(all_horizons: dict[int, dict]) -> go.Figure:
    """Build a stacked bar + line chart showing Safe/Warning/Blocked roads and Hospital Access across T+0..T+60."""
    labels = [all_horizons[h]["horizon_label"] for h in HORIZONS_MINUTES]
    safe_vals = [all_horizons[h]["safe_count"] for h in HORIZONS_MINUTES]
    warn_vals = [all_horizons[h]["warning_count"] for h in HORIZONS_MINUTES]
    block_vals = [all_horizons[h]["blocked_count"] for h in HORIZONS_MINUTES]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="SAFE Corridors",
            x=labels,
            y=safe_vals,
            marker_color="#22C55E",
            text=safe_vals,
            textposition="inside",
        )
    )
    fig.add_trace(
        go.Bar(
            name="WARNING Corridors",
            x=labels,
            y=warn_vals,
            marker_color="#F97316",
            text=warn_vals,
            textposition="inside",
        )
    )
    fig.add_trace(
        go.Bar(
            name="BLOCKED Corridors",
            x=labels,
            y=block_vals,
            marker_color="#EF4444",
            text=block_vals,
            textposition="inside",
        )
    )
    fig.update_layout(
        barmode="stack",
        title=dict(
            text="Projected Road Corridor Availability Across Time Horizons (Synthetic)",
            font=dict(size=14, color="#F8FAFC"),
        ),
        paper_bgcolor="#111C33",
        plot_bgcolor="#111C33",
        font=dict(color="#CBD5E1", size=11),
        margin=dict(l=15, r=15, t=42, b=25),
        height=320,
        yaxis=dict(gridcolor="#1E293B", title="Number of Road Corridors"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


@st.cache_data(show_spinner=False)
def _get_cached_rainfall_sensitivity(
    scenario_name: str,
    manual_failed_tuple: tuple[str, ...],
) -> dict:
    """Cached wrapper for the 7-step T+60 rainfall sensitivity curve."""
    return compute_rainfall_sensitivity_curve(
        scenario_name=scenario_name,
        manual_failed_roads=set(manual_failed_tuple),
    )


def build_rainfall_sensitivity_chart(
    scenario_name: str,
    current_rain: float,
    manual_failed_roads: set[str],
) -> go.Figure:
    """Build a rainfall intensity curve showing how T+60 blocked roads & hospital access vary from 0 to 150 mm/hr."""
    curve = _get_cached_rainfall_sensitivity(
        scenario_name=scenario_name,
        manual_failed_tuple=tuple(sorted(manual_failed_roads)),
    )
    rain_samples = curve["rain_samples"]
    access_curve = curve["access_curve"]
    blocked_pct_curve = curve["blocked_pct_curve"]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=rain_samples,
            y=access_curve,
            mode="lines+markers",
            name="T+60 Hospital Access (%)",
            line=dict(color="#38BDF8", width=3),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=rain_samples,
            y=blocked_pct_curve,
            mode="lines+markers",
            name="T+60 Blocked Roads (%)",
            line=dict(color="#EF4444", width=3, dash="dot"),
        )
    )
    fig.add_vline(
        x=current_rain,
        line_width=2,
        line_dash="dash",
        line_color="#FACC15",
        annotation_text=f"Selected: {int(current_rain)} mm/hr",
        annotation_position="top right",
    )
    fig.update_layout(
        title=dict(
            text="Rainfall Intensity Sensitivity Curve at T+60 min (0–150 mm/hr)",
            font=dict(size=14, color="#F8FAFC"),
        ),
        paper_bgcolor="#111C33",
        plot_bgcolor="#111C33",
        font=dict(color="#CBD5E1", size=11),
        margin=dict(l=15, r=15, t=42, b=25),
        height=320,
        xaxis=dict(gridcolor="#1E293B", title="Simulated Rainfall Intensity (mm/hr)"),
        yaxis=dict(range=[0, 108], gridcolor="#1E293B", title="Percentage (%)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def build_strategy_comparison_chart(df_comp: pd.DataFrame) -> go.Figure:
    """Build a Plotly grouped bar chart comparing Strategy A, B, and C."""
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Avg Dispatch ETA (min)",
            x=df_comp["Strategy"],
            y=df_comp["Avg Dispatch ETA (min)"],
            marker_color="#38BDF8",
            text=df_comp["Avg Dispatch ETA (min)"],
            textposition="outside",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Avg Mission Distance (km)",
            x=df_comp["Strategy"],
            y=df_comp["Avg Mission Distance (km)"],
            marker_color="#A855F7",
            text=df_comp["Avg Mission Distance (km)"],
            textposition="outside",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Flood-Warning Road Exposures",
            x=df_comp["Strategy"],
            y=df_comp["Flood-Warning Road Exposures"],
            marker_color="#F97316",
            text=df_comp["Flood-Warning Road Exposures"],
            textposition="outside",
        )
    )
    fig.update_layout(
        barmode="group",
        title=dict(
            text="Strategy A vs. Strategy B vs. Strategy C Performance Comparison (Synthetic)",
            font=dict(size=14, color="#F8FAFC"),
        ),
        paper_bgcolor="#111C33",
        plot_bgcolor="#111C33",
        font=dict(color="#CBD5E1", size=11),
        margin=dict(l=15, r=15, t=42, b=25),
        height=310,
        yaxis=dict(gridcolor="#1E293B", title="Metric Value"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def build_benchmark_response_time_chart(df_bench: pd.DataFrame) -> go.Figure:
    """Plotly chart 1: Average Emergency Response Time & Total Travel Distance."""
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Avg Response Time (min)",
            x=df_bench["Short Name"],
            y=df_bench["Avg Emergency Response Time (min)"],
            marker_color=["#EF4444", "#38BDF8", "#22C55E"],
            text=df_bench["Avg Emergency Response Time (min)"],
            textposition="outside",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Total Travel Distance (km)",
            x=df_bench["Short Name"],
            y=df_bench["Total Travel Distance (km)"],
            marker_color=["#F97316", "#A855F7", "#3B82F6"],
            text=df_bench["Total Travel Distance (km)"],
            textposition="outside",
        )
    )
    fig.update_layout(
        barmode="group",
        title=dict(
            text="1. Avg Simulated Response Time (min) & Total Travel Distance (km)",
            font=dict(size=13, color="#F8FAFC"),
        ),
        paper_bgcolor="#111C33",
        plot_bgcolor="#111C33",
        font=dict(color="#CBD5E1", size=11),
        margin=dict(l=15, r=15, t=42, b=20),
        height=290,
        yaxis=dict(gridcolor="#1E293B"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def build_benchmark_utilization_chart(df_bench: pd.DataFrame) -> go.Figure:
    """Plotly chart 2: Emergency Resource Utilisation & Blocked-Road Assignments."""
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Resource Utilisation (%)",
            x=df_bench["Short Name"],
            y=df_bench["Resource Utilisation (%)"],
            marker_color="#A855F7",
            text=[f"{v}%" for v in df_bench["Resource Utilisation (%)"]],
            textposition="outside",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Blocked-Road Assignments",
            x=df_bench["Short Name"],
            y=df_bench["Blocked-Road Assignments"],
            marker_color="#EF4444",
            text=df_bench["Blocked-Road Assignments"],
            textposition="outside",
        )
    )
    fig.update_layout(
        barmode="group",
        title=dict(
            text="2. Emergency Resource Utilisation (%) & Blocked-Road Assignments",
            font=dict(size=13, color="#F8FAFC"),
        ),
        paper_bgcolor="#111C33",
        plot_bgcolor="#111C33",
        font=dict(color="#CBD5E1", size=11),
        margin=dict(l=15, r=15, t=42, b=20),
        height=290,
        yaxis=dict(range=[0, 118], gridcolor="#1E293B"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def build_benchmark_reachability_chart(
    df_bench: pd.DataFrame,
    thresh_col: str,
) -> go.Figure:
    """Plotly chart 3: Incident Reachability & Threshold Compliance Comparison."""
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Reached Incidents",
            x=df_bench["Short Name"],
            y=df_bench["Reached Incidents"],
            marker_color="#22C55E",
            text=df_bench["Reached Incidents"],
            textposition="outside",
        )
    )
    fig.add_trace(
        go.Bar(
            name=thresh_col,
            x=df_bench["Short Name"],
            y=df_bench[thresh_col],
            marker_color="#38BDF8",
            text=df_bench[thresh_col],
            textposition="outside",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Unreachable Incidents",
            x=df_bench["Short Name"],
            y=df_bench["Unreachable Incidents"],
            marker_color="#EF4444",
            text=df_bench["Unreachable Incidents"],
            textposition="outside",
        )
    )
    fig.update_layout(
        barmode="group",
        title=dict(
            text="3. Incident Reachability & Response Threshold Comparison (Synthetic)",
            font=dict(size=13, color="#F8FAFC"),
        ),
        paper_bgcolor="#111C33",
        plot_bgcolor="#111C33",
        font=dict(color="#CBD5E1", size=11),
        margin=dict(l=15, r=15, t=42, b=20),
        height=290,
        yaxis=dict(gridcolor="#1E293B", title="Incident Count"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def build_benchmark_hospital_pop_chart(df_bench: pd.DataFrame) -> go.Figure:
    """Plotly chart 4: Hospital Accessibility (%) & Population Retaining Safe Hospital Access."""
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Population Retaining Safe Hospital Access",
            x=df_bench["Short Name"],
            y=df_bench["Population Retaining Hospital Access"],
            marker_color=["#F97316", "#38BDF8", "#22C55E"],
            text=[
                f"{pop:,} ({pct}%)"
                for pop, pct in zip(
                    df_bench["Population Retaining Hospital Access"],
                    df_bench["Hospital Accessibility (%)"],
                )
            ],
            textposition="outside",
        )
    )
    fig.update_layout(
        title=dict(
            text="4. Hospital Accessibility & Population Retaining Safe Access (Synthetic)",
            font=dict(size=13, color="#F8FAFC"),
        ),
        paper_bgcolor="#111C33",
        plot_bgcolor="#111C33",
        font=dict(color="#CBD5E1", size=11),
        margin=dict(l=15, r=15, t=42, b=20),
        height=290,
        yaxis=dict(range=[0, 42000], gridcolor="#1E293B", title="Residents"),
    )
    return fig


# ---------------------------------------------------------------------------
# 4. SIDEBAR NAVIGATION & SCENARIO CONTROLS
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div style="padding: 8px 0 12px 0; border-bottom: 1px solid #1E293B; margin-bottom: 14px;">
            <div style="font-size: 1.35rem; font-weight: 800; color: #F8FAFC; letter-spacing: 1px;">
                🛡️ SANJEEVANI
            </div>
            <div style="font-size: 0.76rem; color: #38BDF8; font-weight: 600; margin-top: 2px;">
                COMMAND & CONTROL NETWORK
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    selected_section = st.radio(
        "NAVIGATION SECTIONS",
        options=[
            "1. Overview",
            "2. Resilience Lab",
            "3. Live Response",
            "4. Future Intelligence",
            "5. Rescue Planning",
            "6. Benchmark & Audit",
        ],
        index=0,
    )

    st.markdown("---")
    st.markdown("**SIMULATION SCENARIO (PROTOTYPE)**")
    scenario_list = get_scenario_names()
    selected_scenario = st.selectbox(
        "Active Disaster Profile",
        options=scenario_list,
        index=1,  # Default to Severe Urban Flood
    )

    # Record scenario change in audit log if user switched it
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

    extra_inc_count = len(st.session_state.custom_incidents)
    extra_crit_count = sum(
        1 for item in st.session_state.custom_incidents if item.get("urgency") == "CRITICAL"
    )
    metrics = get_overview_metrics(
        selected_scenario,
        manual_failed_roads=st.session_state.manual_failed_roads,
        extra_incidents_count=extra_inc_count,
        extra_critical_count=extra_crit_count,
    )
    active_roads = get_synthetic_roads(
        selected_scenario,
        manual_failed_roads=st.session_state.manual_failed_roads,
    )
    total_roads_count = len(active_roads)

    st.markdown(
        f"""
        <div style="background:#111C33; border:1px solid #1E293B; border-radius:8px; padding:10px 12px; margin-top:8px; font-size:0.78rem;">
            <div style="color:#94A3B8; font-weight:600;">DATA MODE & SESSION STATE</div>
            <div style="color:#FACC15; font-weight:700; margin-top:2px;">
                ⚠️ Synthetic Prototype Data
            </div>
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
# 5. TOP COMMAND HEADER & WORKFLOW BANNER
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="eoc-header">
        <div>
            <div class="eoc-title">🛡️ SANJEEVANI</div>
            <div class="eoc-subtitle">
                Human-Centric Disaster Intelligence, Infrastructure Resilience & Autonomous Emergency Response Network
            </div>
            <div class="eoc-tagline">
                Predict the failure. Protect the connection. Save the response time.
            </div>
        </div>
        <div style="text-align: right;">
            <div style="font-size:0.72rem; color:#94A3B8; margin-bottom:4px; font-weight:600;">
                CURRENT SYSTEM STATUS (SIMULATED)
            </div>
            <span class="status-badge" style="background-color:{metrics['status_color']}25; color:{metrics['status_color']}; border-color:{metrics['status_color']};">
                ● {metrics['status_level']}
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
            Scenario: {selected_scenario}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# 6. SECTION ROUTING
# ---------------------------------------------------------------------------
if selected_section == "1. Overview":
    # --- KPI ROW (6 CARDS IN RESPONSIVE EQUAL-HEIGHT CSS GRID) ---
    kpi_html = textwrap.dedent(
        f"""\
        <div class="kpi-grid">
        <div class="kpi-card" style="border-top: 3px solid {metrics['status_color']};">
        <div>
        <div class="kpi-label">Disaster Status</div>
        <div class="kpi-status-text" style="color:{metrics['status_color']};">{metrics['status_level']}</div>
        </div>
        <div class="kpi-sub">Rain: {metrics['rainfall_mm_hr']} mm/hr (Sim)</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #F97316;">
        <div>
        <div class="kpi-label">Total Incidents</div>
        <div class="kpi-value">{metrics['total_incidents']}</div>
        </div>
        <div class="kpi-sub">Active reports in queue</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #EF4444;">
        <div>
        <div class="kpi-label">Critical Incidents</div>
        <div class="kpi-value" style="color:#EF4444;">{metrics['critical_incidents']}</div>
        </div>
        <div class="kpi-sub">Immediate life-safety risk</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #EF4444;">
        <div>
        <div class="kpi-label">Blocked Roads</div>
        <div class="kpi-value" style="color:#F97316;">{metrics['blocked_roads']} / {total_roads_count}</div>
        </div>
        <div class="kpi-sub">Primary corridors closed</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #A855F7;">
        <div>
        <div class="kpi-label">Available Ambulances</div>
        <div class="kpi-value" style="color:#A855F7;">{metrics['available_ambulances']} / {metrics['total_ambulances']}</div>
        </div>
        <div class="kpi-sub">Ready for dispatch</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #3B82F6;">
        <div>
        <div class="kpi-label">Affected Population</div>
        <div class="kpi-value">{metrics['affected_population']:,}</div>
        </div>
        <div class="kpi-sub">Estimated in flood zones</div>
        </div>
        </div>
        """
    )
    st.markdown(kpi_html, unsafe_allow_html=True)

    # --- MAIN BODY: CITY MAP (LEFT) + CRITICAL ALERTS & RISK CHART (RIGHT) ---
    map_col, alert_col = st.columns([1.75, 1.0], gap="large")

    with map_col:
        st.markdown(
            """
            <div class="section-header">
                🗺️ SYNTHETIC CITY COMMAND MAP (PROTOTYPE DATA — NOT LIVE GIS)
            </div>
            <div class="legend-bar">
                <span class="legend-pill" style="background:#EF444425; color:#EF4444; border:1px solid #EF4444;">
                    ● RED: Critical / Blocked Road
                </span>
                <span class="legend-pill" style="background:#F9731625; color:#F97316; border:1px solid #F97316;">
                    ● ORANGE: Warning / Vulnerable
                </span>
                <span class="legend-pill" style="background:#22C55E25; color:#22C55E; border:1px solid #22C55E;">
                    ● GREEN: Safe Road
                </span>
                <span class="legend-pill" style="background:#3B82F625; color:#3B82F6; border:1px solid #3B82F6;">
                    ● BLUE: Hospital
                </span>
                <span class="legend-pill" style="background:#A855F725; color:#A855F7; border:1px solid #A855F7;">
                    ● PURPLE: Rescue / Ambulance
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        city_map = build_eoc_city_map(
            selected_scenario,
            roads_override=active_roads,
        )
        st_folium(
            city_map,
            use_container_width=True,
            height=540,
            returned_objects=[],
        )

    with alert_col:
        st.markdown(
            '<div class="section-header">🚨 CRITICAL ALERTS & VERIFICATION WARNINGS</div>',
            unsafe_allow_html=True,
        )

        alerts = get_critical_alerts(selected_scenario)
        for alert in alerts:
            is_crit = alert["severity"] == "CRITICAL"
            card_class = "alert-card-critical" if is_crit else "alert-card-warning"
            badge_color = "#EF4444" if is_crit else "#F97316"

            st.markdown(
                f"""
                <div class="{card_class}">
                    <div class="alert-header">
                        <span style="color:{badge_color};">● {alert['severity']} • {alert['code']}</span>
                        <span style="color:#94A3B8;">{alert['time']} (Sim)</span>
                    </div>
                    <div class="alert-title">{alert['title']}</div>
                    <div class="alert-detail">{alert['detail']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
        # Compact Plotly chart below alerts
        risk_fig = build_road_risk_chart(
            selected_scenario,
            roads_override=active_roads,
        )
        st.plotly_chart(risk_fig, width="stretch")

    st.markdown("<div style='height: 22px;'></div>", unsafe_allow_html=True)

    # --- BOTTOM ROW: RECENT ACTIVITY & INFRASTRUCTURE STATUS ---
    act_col, unit_col = st.columns([1.45, 1.0], gap="large")

    with act_col:
        st.markdown(
            '<div class="section-header">📋 RECENT SYSTEM ACTIVITY (LIVE SESSION AUDIT STREAM)</div>',
            unsafe_allow_html=True,
        )
        if st.session_state.audit_log:
            df_activity = get_audit_dataframe(st.session_state.audit_log)[
                ["Timestamp", "Stage", "Action", "Details"]
            ].head(8)
        else:
            df_activity = get_recent_activity()
        st.dataframe(df_activity, width="stretch", hide_index=True)

    with unit_col:
        st.markdown(
            '<div class="section-header">🚑 DEPLOYED RESCUE UNITS & HOSPITALS (SYNTHETIC)</div>',
            unsafe_allow_html=True,
        )
        df_units = get_synthetic_rescue_teams()[
            ["unit_id", "type", "status", "assigned_sector"]
        ]
        st.dataframe(df_units, width="stretch", hide_index=True)

elif selected_section == "2. Resilience Lab":
    # -----------------------------------------------------------------------
    # SECTION 2: RESILIENCE LAB (Member 1 Interface & NetworkX Simulation)
    # -----------------------------------------------------------------------
    res_bundle = assess_road_network_resilience(
        selected_scenario,
        manual_failed_roads=st.session_state.manual_failed_roads,
        roads_override=active_roads,
    )
    roads_list = res_bundle["roads_list"]
    df_roads = res_bundle["roads_df"]
    resilience_eval = res_bundle["resilience_eval"]
    G_passable = res_bundle["passable_graph"]

    # Top Summary Metrics for Resilience Lab
    res_kpi_html = textwrap.dedent(
        f"""\
        <div class="kpi-grid">
        <div class="kpi-card" style="border-top: 3px solid #3B82F6;">
        <div>
        <div class="kpi-label">NetworkX Graph Nodes</div>
        <div class="kpi-value">{G_passable.number_of_nodes()} Junctions</div>
        </div>
        <div class="kpi-sub">3 Hospital Hubs • 6 Sectors</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #22C55E;">
        <div>
        <div class="kpi-label">Passable Road Edges</div>
        <div class="kpi-value" style="color:#22C55E;">{G_passable.number_of_edges()} / {len(roads_list)}</div>
        </div>
        <div class="kpi-sub">Active edges in routing graph</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #EF4444;">
        <div>
        <div class="kpi-label">Blocked Corridors</div>
        <div class="kpi-value" style="color:#EF4444;">{len(roads_list) - G_passable.number_of_edges()}</div>
        </div>
        <div class="kpi-sub">Manual Failures: {len(st.session_state.manual_failed_roads)}</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #38BDF8;">
        <div>
        <div class="kpi-label">Hospital Reachability</div>
        <div class="kpi-value" style="color:#38BDF8;">{resilience_eval['hospital_access_pct']}%</div>
        </div>
        <div class="kpi-sub">{resilience_eval['connected_population']:,} residents connected</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #F97316;">
        <div>
        <div class="kpi-label">Isolated Population</div>
        <div class="kpi-value" style="color:#F97316;">{resilience_eval['isolated_population']:,}</div>
        </div>
        <div class="kpi-sub">Sectors without passable hospital path</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #A855F7;">
        <div>
        <div class="kpi-label">Graph Connectivity</div>
        <div class="kpi-status-text" style="color:{'#22C55E' if resilience_eval['is_fully_connected'] else '#F97316'};">
        {'INTACT' if resilience_eval['is_fully_connected'] else f"{resilience_eval['num_connected_components']} SUBGRAPHS"}
        </div>
        </div>
        <div class="kpi-sub">NetworkX connected components</div>
        </div>
        </div>
        """
    )
    st.markdown(res_kpi_html, unsafe_allow_html=True)

    # Interactive Road Failure Simulator & Map Row
    sim_col, map_col2 = st.columns([1.05, 1.55], gap="large")

    with sim_col:
        st.markdown(
            '<div class="section-header">🛠️ INTERACTIVE ROAD FAILURE SIMULATOR (NETWORKX)</div>',
            unsafe_allow_html=True,
        )
        road_options = [
            f"{r['road_id']} • {r['name']} [{r['status']}]" for r in roads_list
        ]
        selected_road_label = st.selectbox(
            "Select a Synthetic Road Corridor to Stress-Test",
            options=road_options,
        )
        selected_road_id = selected_road_label.split(" • ")[0].strip()
        selected_road_obj = next(
            (r for r in roads_list if r["road_id"] == selected_road_id),
            roads_list[0],
        )

        # Preview connectivity impact if this specific road is forced to fail
        hypothetical_sim = simulate_single_road_failure(
            selected_scenario,
            road_id=selected_road_id,
            existing_failed_roads=st.session_state.manual_failed_roads,
        )

        st.markdown(
            textwrap.dedent(
                f"""\
                <div class="kpi-card" style="min-height:auto; margin-bottom:14px; border-left:4px solid #38BDF8;">
                <div class="kpi-label">SELECTED CORRIDOR TELEMETRY (SYNTHETIC)</div>
                <div style="font-size:1.0rem; font-weight:700; color:#F8FAFC; margin-bottom:6px;">
                {selected_road_obj['road_id']}: {selected_road_obj['name']}
                </div>
                <div style="font-size:0.82rem; color:#CBD5E1; line-height:1.55;">
                • <b>NetworkX Edge:</b> <code>{selected_road_obj['u']} ↔ {selected_road_obj['v']}</code> ({selected_road_obj['distance_km']} km)<br/>
                • <b>Current Status:</b> <b>{selected_road_obj['status']}</b> (Failure Prob: {int(selected_road_obj['failure_prob']*100)}%)<br/>
                • <b>Vulnerability Score:</b> {selected_road_obj['vulnerability_score']} / 100 (Criticality Rank #{selected_road_obj['critical_rank']})<br/>
                • <b>Direct Population Impact:</b> {selected_road_obj['population_impact']:,} residents<br/>
                • <b>Pre-Positioning Recommendation:</b> {selected_road_obj['preposition_Zone']}<br/>
                • <b>Projected Hospital Access if Closed:</b> {hypothetical_sim['post_failure_access_pct']}% (Isolated Pop: {hypothetical_sim['isolated_population']:,})
                </div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button(
                f"💥 Simulate Failure ({selected_road_id})",
                width="stretch",
            ):
                if selected_road_id not in st.session_state.manual_failed_roads:
                    st.session_state.manual_failed_roads.add(selected_road_id)
                    append_audit_event(
                        st.session_state.audit_log,
                        stage="ESTIMATE",
                        action_type="Road Marked Unavailable",
                        details=(
                            f"Simulated failure on {selected_road_id} ({selected_road_obj['name']}). "
                            f"Edge {selected_road_obj['u']}↔{selected_road_obj['v']} removed from passable NetworkX graph."
                        ),
                    )
                    st.rerun()
                else:
                    st.warning(f"{selected_road_id} is already marked as BLOCKED in this session.")

        with btn_c2:
            if st.button("🔄 Reset Simulated Road Failures", width="stretch"):
                if st.session_state.manual_failed_roads:
                    count_reset = len(st.session_state.manual_failed_roads)
                    st.session_state.manual_failed_roads.clear()
                    append_audit_event(
                        st.session_state.audit_log,
                        stage="ESTIMATE",
                        action_type="Road Network Restored",
                        details=f"Cleared {count_reset} manually simulated road closure(s) back to scenario baseline.",
                    )
                    st.rerun()

        if st.session_state.manual_failed_roads:
            st.success(
                "Active Manual Road Failures in Session: "
                + ", ".join(sorted(st.session_state.manual_failed_roads))
            )

        vuln_fig = build_vulnerability_vs_impact_chart(df_roads)
        st.plotly_chart(vuln_fig, width="stretch")

    with map_col2:
        st.markdown(
            f'<div class="section-header">🗺️ ROAD NETWORK & CONNECTIVITY MAP (HIGHLIGHTING {selected_road_id})</div>',
            unsafe_allow_html=True,
        )
        res_map = build_eoc_city_map(
            selected_scenario,
            highlight_road_id=selected_road_id,
            roads_override=roads_list,
        )
        st_folium(res_map, use_container_width=True, height=510, returned_objects=[])

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    # Bottom Tables: Hospital Accessibility & Critical Road Rankings
    t_col1, t_col2 = st.columns([1.15, 1.15], gap="large")
    with t_col1:
        st.markdown(
            '<div class="section-header">🏥 SECTOR-TO-HOSPITAL ACCESSIBILITY & SAFE ROUTES (NETWORKX)</div>',
            unsafe_allow_html=True,
        )
        st.dataframe(resilience_eval["sector_df"], width="stretch", hide_index=True)

    with t_col2:
        st.markdown(
            '<div class="section-header">📊 CRITICAL ROAD RANKINGS & RESOURCE PRE-POSITIONING</div>',
            unsafe_allow_html=True,
        )
        st.dataframe(res_bundle["critical_rankings_df"], width="stretch", hide_index=True)

elif selected_section == "3. Live Response":
    # -----------------------------------------------------------------------
    # SECTION 3: LIVE RESPONSE (Member 2 Interface: Reports & Evidence Scoring)
    # -----------------------------------------------------------------------
    df_inc_all = get_active_incidents_df(selected_scenario)
    roads_now = active_roads

    ev_metrics = summarize_evidence_metrics(df_inc_all)
    crit_count = ev_metrics["critical_count"]
    verified_count = ev_metrics["verified_count"]
    dup_count = ev_metrics["duplicate_flagged_count"]
    avg_conf = ev_metrics["mean_confidence_pct"]
    open_roads_count = sum(1 for r in roads_now if r["status"] != "BLOCKED")

    live_kpi_html = textwrap.dedent(
        f"""\
        <div class="kpi-grid">
        <div class="kpi-card" style="border-top: 3px solid #3B82F6;">
        <div>
        <div class="kpi-label">Active Reports</div>
        <div class="kpi-value">{len(df_inc_all)}</div>
        </div>
        <div class="kpi-sub">Session added: {len(st.session_state.custom_incidents)}</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #EF4444;">
        <div>
        <div class="kpi-label">Critical Urgency</div>
        <div class="kpi-value" style="color:#EF4444;">{crit_count}</div>
        </div>
        <div class="kpi-sub">Immediate dispatch priority</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #22C55E;">
        <div>
        <div class="kpi-label">Verified Reports</div>
        <div class="kpi-value" style="color:#22C55E;">{verified_count} / {len(df_inc_all)}</div>
        </div>
        <div class="kpi-sub">Cleared by evidence check</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #F97316;">
        <div>
        <div class="kpi-label">Duplicate Warnings</div>
        <div class="kpi-value" style="color:#F97316;">{dup_count}</div>
        </div>
        <div class="kpi-sub">Flagged recycled/fake media</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #A855F7;">
        <div>
        <div class="kpi-label">Mean Confidence</div>
        <div class="kpi-value" style="color:#A855F7;">{avg_conf}%</div>
        </div>
        <div class="kpi-sub">Synthetic evidence score</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #22C55E;">
        <div>
        <div class="kpi-label">Passable Corridors</div>
        <div class="kpi-value" style="color:#22C55E;">{open_roads_count} / {len(roads_now)}</div>
        </div>
        <div class="kpi-sub">Available for field response</div>
        </div>
        </div>
        """
    )
    st.markdown(live_kpi_html, unsafe_allow_html=True)

    # Top Row: Emergency Report Table & New Report Intake Form
    rep_col, form_col = st.columns([1.55, 1.0], gap="large")

    with rep_col:
        st.markdown(
            '<div class="section-header">📡 INCOMING EMERGENCY REPORTS & EVIDENCE INTELLIGENCE (SYNTHETIC)</div>',
            unsafe_allow_html=True,
        )

        f_col1, f_col2 = st.columns(2)
        with f_col1:
            urgency_filter = st.selectbox(
                "Filter by Urgency",
                options=["ALL", "CRITICAL", "WARNING"],
                index=0,
            )
        with f_col2:
            verify_filter = st.selectbox(
                "Filter by Verification Status",
                options=["ALL", "Verified Only", "Pending / Unverified Only"],
                index=0,
            )

        df_filtered = filter_incident_reports(
            df_inc_all,
            urgency_filter=urgency_filter,
            verify_filter=verify_filter,
        )

        df_display = df_filtered[
            [
                "incident_id",
                "reported_at",
                "sector",
                "type",
                "urgency",
                "confidence",
                "duplicate_warning",
                "verified",
                "title",
            ]
        ].copy()
        df_display["confidence"] = (df_display["confidence"] * 100).round(0).astype(int).astype(str) + "%"
        df_display["verified"] = df_display["verified"].map(
            lambda v: "✅ Verified" if v else "⚠️ Pending Review"
        )
        df_display = df_display.rename(
            columns={
                "incident_id": "ID",
                "reported_at": "Time",
                "sector": "Location / Sector",
                "type": "Disaster Type",
                "urgency": "Urgency",
                "confidence": "Confidence",
                "duplicate_warning": "Image Duplicate Check",
                "verified": "Verification",
                "title": "Report Summary",
            }
        )
        st.dataframe(df_display, width="stretch", hide_index=True)

        # Quick operator verification action bar
        unverified_ids = df_inc_all[df_inc_all["verified"] == False]["incident_id"].tolist()  # noqa: E712
        if unverified_ids:
            v_c1, v_c2 = st.columns([1.4, 1.0])
            with v_c1:
                inc_to_verify = st.selectbox(
                    "Select Unverified Report for Manual Review",
                    options=unverified_ids,
                )
            with v_c2:
                st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
                if st.button("✅ Mark Selected Report Verified", width="stretch"):
                    st.session_state.verified_overrides[inc_to_verify] = True
                    append_audit_event(
                        st.session_state.audit_log,
                        stage="VERIFY",
                        action_type="Emergency Report Verified",
                        details=f"Operator manually verified {inc_to_verify} after reviewing duplicate warning.",
                    )
                    st.rerun()

    with form_col:
        st.markdown(
            '<div class="section-header">➕ SUBMIT SAMPLE EMERGENCY REPORT (SIMULATED INTAKE)</div>',
            unsafe_allow_html=True,
        )

        with st.form("submit_emergency_report_form", clear_on_submit=True):
            rep_title = st.text_input(
                "Incident Description / Summary",
                placeholder="e.g., Waterlogged Ambulance Trapped Near Clinic",
            )
            rep_sector = st.selectbox(
                "Incident Location / Sector",
                options=list(SECTOR_COORDINATES.keys()),
            )
            rep_type = st.selectbox(
                "Disaster Type",
                options=[
                    "Flash Flood Entrapment",
                    "Medical Evacuation",
                    "Infrastructure Failure",
                    "Road Obstruction",
                ],
            )
            rep_urgency = st.selectbox(
                "Urgency Level",
                options=["CRITICAL", "WARNING"],
            )
            sim_duplicate = st.checkbox(
                "Simulate Duplicate / Recycled Image Detection Warning (Member 2 Test)",
                value=False,
            )
            submitted = st.form_submit_button(
                "🚨 Ingest Emergency Report & Score Evidence",
                width="stretch",
            )

            if submitted:
                try:
                    new_inc = score_emergency_report(
                        title=rep_title,
                        sector=rep_sector,
                        disaster_type=rep_type,
                        urgency=rep_urgency,
                        simulate_duplicate=sim_duplicate,
                        existing_custom_count=len(st.session_state.custom_incidents),
                    )
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
                    st.success(
                        f"Report {new_id} ingested! Confidence: {int(calc_conf*100)}% ({dup_status})."
                    )
                    st.rerun()

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    # Bottom Row: Current Road Availability & Relevant Precautions
    road_avail_col, prec_col = st.columns([1.2, 1.2], gap="large")

    with road_avail_col:
        st.markdown(
            '<div class="section-header">🛣️ CURRENT ROAD CORRIDOR AVAILABILITY (LIVE NETWORK STATE)</div>',
            unsafe_allow_html=True,
        )
        df_road_avail = pd.DataFrame(roads_now)[
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
        precautions_map = get_precautions_by_disaster_type()
        selected_prec_type = st.selectbox(
            "Inspect Field Precautions for Disaster Category",
            options=list(precautions_map.keys()),
        )
        bullets_html = "".join(
            f"<li style='margin-bottom:6px;'>{item}</li>"
            for item in precautions_map[selected_prec_type]
        )
        st.markdown(
            textwrap.dedent(
                f"""\
                <div class="kpi-card" style="min-height:auto; border-left:4px solid #22C55E;">
                <div class="kpi-label">FIELD SAFETY PROTOCOL • {selected_prec_type.upper()}</div>
                <ul style="margin:8px 0 0 18px; padding:0; font-size:0.84rem; color:#E2E8F0; line-height:1.5;">
                {bullets_html}
                </ul>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

elif selected_section == "4. Future Intelligence":
    # -----------------------------------------------------------------------
    # SECTION 4: FUTURE INTELLIGENCE (Member 3 Digital Twin Projections)
    # -----------------------------------------------------------------------
    st.markdown(
        '<div class="section-header">🌧️ SYNTHETIC DIGITAL TWIN — RAINFALL & FUTURE PROJECTION CONTROLS</div>',
        unsafe_allow_html=True,
    )

    ctrl_c1, ctrl_c2, ctrl_c3 = st.columns([1.3, 1.0, 0.9], gap="large")
    with ctrl_c1:
        default_rain = (
            int(st.session_state.future_rainfall_override)
            if st.session_state.future_rainfall_override is not None
            else int(metrics["rainfall_mm_hr"])
        )
        sim_rainfall = st.slider(
            "Simulated Rainfall Intensity (0–150 mm/hr)",
            min_value=0,
            max_value=150,
            value=default_rain,
            step=5,
            help="Adjust synthetic rainfall intensity to evaluate T+15m, T+30m, and T+60m infrastructure projections.",
        )
        st.session_state.future_rainfall_override = sim_rainfall
    with ctrl_c2:
        default_h_idx = (
            HORIZONS_MINUTES.index(st.session_state.future_horizon_min)
            if st.session_state.future_horizon_min in HORIZONS_MINUTES
            else 2
        )
        selected_horizon = st.selectbox(
            "Select Map & Telemetry Horizon View",
            options=HORIZONS_MINUTES,
            index=default_h_idx,
            format_func=lambda h: HORIZON_LABELS.get(h, f"T+{h} min"),
        )
        st.session_state.future_horizon_min = selected_horizon
    with ctrl_c3:
        st.markdown("<div style='height:26px;'></div>", unsafe_allow_html=True)
        if st.button("📝 Log Future Projection to Audit Trail", width="stretch"):
            append_audit_event(
                st.session_state.audit_log,
                stage="SIMULATE",
                action_type="Future Projection Evaluated",
                details=(
                    f"Simulated {sim_rainfall} mm/hr across T+15/T+30/T+60 horizons "
                    f"(Inspecting {HORIZON_LABELS[selected_horizon]})."
                ),
            )
            st.success("Projection logged to SHA-256 Audit Trail.")

    all_horizons = simulate_all_horizons(
        selected_scenario,
        rainfall_mm_hr=float(sim_rainfall),
        manual_failed_roads=st.session_state.manual_failed_roads,
    )
    h0 = all_horizons[0]
    h15 = all_horizons[15]
    h30 = all_horizons[30]
    h60 = all_horizons[60]
    h_sel = all_horizons[selected_horizon]

    # Top 6 KPI Cards Comparing Current (T+0) vs T+15, T+30, T+60 Projections
    fut_kpi_html = textwrap.dedent(
        f"""\
        <div class="kpi-grid">
        <div class="kpi-card" style="border-top: 3px solid #38BDF8;">
        <div>
        <div class="kpi-label">Simulated Rainfall</div>
        <div class="kpi-value" style="color:#38BDF8;">{sim_rainfall} mm/hr</div>
        </div>
        <div class="kpi-sub">Scenario Base: {metrics['rainfall_mm_hr']} mm/hr</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #22C55E;">
        <div>
        <div class="kpi-label">Current (T+0 min)</div>
        <div class="kpi-value">{h0['blocked_count']} Blocked</div>
        </div>
        <div class="kpi-sub">Hospital Access: {h0['hospital_access_pct']}%</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #FACC15;">
        <div>
        <div class="kpi-label">+15 Min Projection</div>
        <div class="kpi-value" style="color:#FACC15;">{h15['blocked_count']} Blocked</div>
        </div>
        <div class="kpi-sub">Hospital Access: {h15['hospital_access_pct']}% (Sim)</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #F97316;">
        <div>
        <div class="kpi-label">+30 Min Projection</div>
        <div class="kpi-value" style="color:#F97316;">{h30['blocked_count']} Blocked</div>
        </div>
        <div class="kpi-sub">Hospital Access: {h30['hospital_access_pct']}% (Sim)</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #EF4444;">
        <div>
        <div class="kpi-label">+60 Min Projection</div>
        <div class="kpi-value" style="color:#EF4444;">{h60['blocked_count']} Blocked</div>
        </div>
        <div class="kpi-sub">Hospital Access: {h60['hospital_access_pct']}% (Sim)</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #A855F7;">
        <div>
        <div class="kpi-label">T+60 Isolated Pop.</div>
        <div class="kpi-value" style="color:#A855F7;">{h60['isolated_population']:,}</div>
        </div>
        <div class="kpi-sub">Potentially cut off at +60m</div>
        </div>
        </div>
        """
    )
    st.markdown(fut_kpi_html, unsafe_allow_html=True)

    # Map + Horizon Charts Row
    f_map_col, f_chart_col = st.columns([1.45, 1.15], gap="large")

    with f_map_col:
        st.markdown(
            f'<div class="section-header">🗺️ PROJECTED INFRASTRUCTURE MAP — {HORIZON_LABELS[selected_horizon].upper()} ({sim_rainfall} MM/HR)</div>',
            unsafe_allow_html=True,
        )
        proj_map = build_eoc_city_map(
            selected_scenario,
            roads_override=h_sel["roads"],
        )
        st_folium(proj_map, use_container_width=True, height=520, returned_objects=[])

    with f_chart_col:
        st.markdown(
            '<div class="section-header">📈 TIME-HORIZON & RAINFALL SENSITIVITY CHARTS (SYNTHETIC)</div>',
            unsafe_allow_html=True,
        )
        horizon_fig = build_horizon_projection_chart(all_horizons)
        st.plotly_chart(horizon_fig, width="stretch")

        rain_fig = build_rainfall_sensitivity_chart(
            selected_scenario,
            current_rain=float(sim_rainfall),
            manual_failed_roads=st.session_state.manual_failed_roads,
        )
        st.plotly_chart(rain_fig, width="stretch")

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Horizon Summary Table & Road-by-Road Progression Table
    p_col1, p_col2 = st.columns([1.15, 1.15], gap="large")
    with p_col1:
        st.markdown(
            '<div class="section-header">⏱️ HORIZON SUMMARY: T+0 (CURRENT) VS. +15M / +30M / +60M (SIMULATED)</div>',
            unsafe_allow_html=True,
        )
        df_horizons = build_horizon_comparison_df(all_horizons)
        st.dataframe(df_horizons, width="stretch", hide_index=True)

        st.markdown(
            f'<div class="section-header" style="margin-top:14px;">🏥 PROJECTED HOSPITAL ACCESSIBILITY AT {HORIZON_LABELS[selected_horizon].upper()}</div>',
            unsafe_allow_html=True,
        )
        st.dataframe(h_sel["sector_df"], width="stretch", hide_index=True)

    with p_col2:
        st.markdown(
            '<div class="section-header">🛣️ ROAD-BY-ROAD CLOSURE PROGRESSION (T+0 → T+60 MIN)</div>',
            unsafe_allow_html=True,
        )
        df_prog = build_road_progression_df(all_horizons)
        st.dataframe(df_prog, width="stretch", hide_index=True)

        casc_data = get_cascading_impacts_and_observations(all_horizons)
        st.markdown(
            '<div class="section-header" style="margin-top:14px;">⚡ CASCADING INFRASTRUCTURE IMPACT (SYNTHETIC)</div>',
            unsafe_allow_html=True,
        )
        st.dataframe(casc_data["cascading_df"], width="stretch", hide_index=True)

        st.markdown(
            '<div class="section-header" style="margin-top:14px;">🔭 ACTIVE OBSERVATION RECOMMENDATIONS (FIELD / DRONE SENSORS)</div>',
            unsafe_allow_html=True,
        )
        st.dataframe(casc_data["observations_df"], width="stretch", hide_index=True)

elif selected_section == "5. Rescue Planning":
    # -----------------------------------------------------------------------
    # SECTION 5: RESCUE PLANNING (Member 3 Routing & Strategy A/B/C Comparison)
    # -----------------------------------------------------------------------
    df_inc_rescue = get_active_incidents_df(selected_scenario)
    strategy_options = get_strategy_names()

    st.markdown(
        '<div class="section-header">🧭 AUTONOMOUS RESCUE ROUTING & STRATEGY SELECTION (NETWORKX)</div>',
        unsafe_allow_html=True,
    )

    s_col1, s_col2 = st.columns([1.4, 1.0], gap="large")
    with s_col1:
        chosen_strategy = st.selectbox(
            "Select Active Rescue Dispatch & Routing Strategy",
            options=strategy_options,
            index=strategy_options.index(st.session_state.selected_rescue_strategy)
            if st.session_state.selected_rescue_strategy in strategy_options
            else 2,
        )
        st.session_state.selected_rescue_strategy = chosen_strategy

        if st.session_state.last_logged_strategy != chosen_strategy:
            append_audit_event(
                st.session_state.audit_log,
                stage="OPTIMIZE",
                action_type="Rescue Route Updated & Strategy Selected",
                details=f"Operator switched active dispatch optimization to '{chosen_strategy}'.",
            )
            st.session_state.last_logged_strategy = chosen_strategy

    plan_result = allocate_rescue_resources(
        scenario_name=selected_scenario,
        incidents_df=df_inc_rescue,
        strategy_name=chosen_strategy,
        manual_failed_roads=st.session_state.manual_failed_roads,
    )
    df_strategy_comp = compare_all_strategies(
        scenario_name=selected_scenario,
        incidents_df=df_inc_rescue,
        manual_failed_roads=st.session_state.manual_failed_roads,
    )

    with s_col2:
        st.markdown(
            textwrap.dedent(
                f"""\
                <div class="kpi-card" style="min-height:auto; border-left:4px solid #A855F7; padding:12px 16px;">
                <div class="kpi-label">{plan_result['strategy_meta']['short_code']} • OPTIMIZATION LOGIC</div>
                <div style="font-size:0.83rem; color:#E2E8F0; line-height:1.45;">
                {plan_result['strategy_meta']['description']}
                </div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

    # Top 6 KPI Cards for Rescue Planning
    resc_kpi_html = textwrap.dedent(
        f"""\
        <div class="kpi-grid">
        <div class="kpi-card" style="border-top: 3px solid #A855F7;">
        <div>
        <div class="kpi-label">Selected Strategy</div>
        <div class="kpi-status-text" style="color:#A855F7;">{plan_result['strategy_meta']['short_code']}</div>
        </div>
        <div class="kpi-sub">Weight: {plan_result['strategy_meta']['weight_attr']}</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #22C55E;">
        <div>
        <div class="kpi-label">Incidents Reached</div>
        <div class="kpi-value" style="color:#22C55E;">{plan_result['assigned_count']} / {len(df_inc_rescue)}</div>
        </div>
        <div class="kpi-sub">Valid passable NetworkX path</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #EF4444;">
        <div>
        <div class="kpi-label">Unreachable</div>
        <div class="kpi-value" style="color:#EF4444;">{plan_result['unreachable_count']}</div>
        </div>
        <div class="kpi-sub">Cut off by road closures</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #38BDF8;">
        <div>
        <div class="kpi-label">Avg Dispatch ETA</div>
        <div class="kpi-value" style="color:#38BDF8;">{plan_result['avg_response_eta_min']} min</div>
        </div>
        <div class="kpi-sub">Avg Distance: {plan_result['avg_total_distance_km']} km</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #F97316;">
        <div>
        <div class="kpi-label">Warning Exposures</div>
        <div class="kpi-value" style="color:#F97316;">{plan_result['warning_corridor_exposures']}</div>
        </div>
        <div class="kpi-sub">Routes using flood-warning roads</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #3B82F6;">
        <div>
        <div class="kpi-label">Unit Utilisation</div>
        <div class="kpi-value" style="color:#3B82F6;">{plan_result['unit_utilization_pct']}%</div>
        </div>
        <div class="kpi-sub">Passable Edges: {plan_result['passable_edges_count']}/{plan_result['total_edges_count']}</div>
        </div>
        </div>
        """
    )
    st.markdown(resc_kpi_html, unsafe_allow_html=True)

    # Interactive Rescue Route Map + Strategy Comparison Chart
    r_map_col, r_comp_col = st.columns([1.5, 1.1], gap="large")

    with r_map_col:
        st.markdown(
            f'<div class="section-header">🗺️ INTERACTIVE RESCUE ROUTE MAP — {plan_result["strategy_meta"]["short_code"]} (AVOIDING BLOCKED ROADS)</div>',
            unsafe_allow_html=True,
        )
        rescue_map = build_eoc_city_map(
            selected_scenario,
            roads_override=active_roads,
            rescue_routes=plan_result["map_routes"],
        )
        st_folium(rescue_map, use_container_width=True, height=520, returned_objects=[])

    with r_comp_col:
        st.markdown(
            '<div class="section-header">📊 STRATEGY A vs. B vs. C PERFORMANCE COMPARISON</div>',
            unsafe_allow_html=True,
        )
        comp_fig = build_strategy_comparison_chart(df_strategy_comp)
        st.plotly_chart(comp_fig, width="stretch")

        st.dataframe(df_strategy_comp, width="stretch", hide_index=True)

        if st.button("🚑 Confirm & Dispatch Active Resource Allocation", width="stretch"):
            append_audit_event(
                st.session_state.audit_log,
                stage="OPTIMIZE",
                action_type="Resource Assigned & Routes Dispatched",
                details=(
                    f"Dispatched {plan_result['assigned_count']} mission(s) under {plan_result['strategy_meta']['short_code']} "
                    f"(Avg ETA: {plan_result['avg_response_eta_min']} min, Unreachable: {plan_result['unreachable_count']})."
                ),
            )
            st.success(
                f"Dispatch orders logged to SHA-256 Audit Trail under {plan_result['strategy_meta']['short_code']}!"
            )

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Full Resource Allocation Table & Available Fleet Table
    st.markdown(
        '<div class="section-header">📋 EMERGENCY RESOURCE ALLOCATION & SUGGESTED RESCUE ROUTES (UPDATED FOR ROAD CLOSURES)</div>',
        unsafe_allow_html=True,
    )
    st.dataframe(plan_result["allocations_df"], width="stretch", hide_index=True)

    u_col1, u_col2 = st.columns(2, gap="large")
    with u_col1:
        st.markdown(
            '<div class="section-header" style="margin-top:12px;">🚑 AVAILABLE AMBULANCES & RESCUE TEAMS (SYNTHETIC)</div>',
            unsafe_allow_html=True,
        )
        st.dataframe(get_synthetic_rescue_teams(), width="stretch", hide_index=True)
    with u_col2:
        st.markdown(
            '<div class="section-header" style="margin-top:12px;">🏥 RECEIVING HOSPITALS & ICU CAPACITY (SYNTHETIC)</div>',
            unsafe_allow_html=True,
        )
        st.dataframe(get_synthetic_hospitals(), width="stretch", hide_index=True)

else:
    # -----------------------------------------------------------------------
    # SECTION 6: BENCHMARK & AUDIT (Performance Evaluation & SHA-256 Chain)
    # -----------------------------------------------------------------------
    df_inc_bench = get_active_incidents_df(selected_scenario)

    st.markdown(
        '<div class="section-header">⚖️ PART 1: STRATEGY PERFORMANCE BENCHMARKING (SYNTHETIC SIMULATION EVALUATION)</div>',
        unsafe_allow_html=True,
    )

    b_ctrl1, b_ctrl2 = st.columns([1.2, 1.4], gap="large")
    with b_ctrl1:
        thresh_min = st.slider(
            "Target Response Time Threshold for Serious Incidents (minutes)",
            min_value=3.0,
            max_value=15.0,
            value=8.0,
            step=1.0,
            help="Evaluate how many incidents are reached within this simulated time threshold across Strategies A, B, and C.",
        )
    with b_ctrl2:
        st.markdown(
            textwrap.dedent(
                f"""\
                <div class="kpi-card" style="min-height:auto; border-left:4px solid #38BDF8; padding:10px 14px;">
                <div class="kpi-label">BENCHMARK METHODOLOGY (IDENTICAL INPUTS • NO FABRICATED GAINS)</div>
                <div style="font-size:0.8rem; color:#CBD5E1; line-height:1.45;">
                All 3 strategies are evaluated on the exact same synthetic graph (<code>{selected_scenario}</code>),
                active manual road closures (<b>{len(st.session_state.manual_failed_roads)}</b>),
                and incident queue (<b>{len(df_inc_bench)} reports</b>). All values are calculated directly from NetworkX shortest paths.
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
    sa = bench_res["strategy_a"]
    sb = bench_res["strategy_b"]
    sc_row = bench_res["strategy_c"]
    thresh_col_name = f"Reached <= {int(thresh_min)} min"

    # Baseline (Strategy A) vs SANJEEVANI (Strategy C) Comparison Cards
    bench_kpi_html = textwrap.dedent(
        f"""\
        <div class="kpi-grid">
        <div class="kpi-card" style="border-top: 3px solid #22C55E;">
        <div>
        <div class="kpi-label">Avg Simulated ETA</div>
        <div class="kpi-value" style="color:#22C55E;">{sc_row['Avg Emergency Response Time (min)']}m</div>
        </div>
        <div class="kpi-sub">Baseline A: {sa['Avg Emergency Response Time (min)']}m | B: {sb['Avg Emergency Response Time (min)']}m</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #38BDF8;">
        <div>
        <div class="kpi-label">Total Mission Dist.</div>
        <div class="kpi-value" style="color:#38BDF8;">{sc_row['Total Travel Distance (km)']} km</div>
        </div>
        <div class="kpi-sub">Baseline A: {sa['Total Travel Distance (km)']} km | B: {sb['Total Travel Distance (km)']} km</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #EF4444;">
        <div>
        <div class="kpi-label">Blocked-Road Routes</div>
        <div class="kpi-value" style="color:#22C55E;">{sc_row['Blocked-Road Assignments']}</div>
        </div>
        <div class="kpi-sub">Baseline A encounters: {sa['Blocked-Road Assignments']} blocked</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #F97316;">
        <div>
        <div class="kpi-label">{thresh_col_name}</div>
        <div class="kpi-value" style="color:#F97316;">{sc_row[thresh_col_name]} / {sc_row['Reached Incidents']}</div>
        </div>
        <div class="kpi-sub">Baseline A: {sa[thresh_col_name]} | Strategy B: {sb[thresh_col_name]}</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #3B82F6;">
        <div>
        <div class="kpi-label">Safe Hospital Access</div>
        <div class="kpi-value" style="color:#3B82F6;">{sc_row['Hospital Accessibility (%)']}%</div>
        </div>
        <div class="kpi-sub">{sc_row['Population Retaining Hospital Access']:,} residents connected</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #A855F7;">
        <div>
        <div class="kpi-label">Resource Utilisation</div>
        <div class="kpi-value" style="color:#A855F7;">{sc_row['Resource Utilisation (%)']}%</div>
        </div>
        <div class="kpi-sub">Duplicate Holds Saved: {bench_res['unverified_held_count']}</div>
        </div>
        </div>
        """
    )
    st.markdown(bench_kpi_html, unsafe_allow_html=True)

    # 2x2 Plotly Benchmark Charts Grid
    ch_r1_c1, ch_r1_c2 = st.columns(2, gap="large")
    with ch_r1_c1:
        st.plotly_chart(
            build_benchmark_response_time_chart(df_bench),
            width="stretch",
        )
    with ch_r1_c2:
        st.plotly_chart(
            build_benchmark_utilization_chart(df_bench),
            width="stretch",
        )

    ch_r2_c1, ch_r2_c2 = st.columns(2, gap="large")
    with ch_r2_c1:
        st.plotly_chart(
            build_benchmark_reachability_chart(df_bench, thresh_col_name),
            width="stretch",
        )
    with ch_r2_c2:
        st.plotly_chart(
            build_benchmark_hospital_pop_chart(df_bench),
            width="stretch",
        )

    st.markdown(
        '<div class="section-header" style="margin-top:8px;">📊 COMPLETE STRATEGY BENCHMARK COMPARISON TABLE (SYNTHETIC SIMULATION)</div>',
        unsafe_allow_html=True,
    )
    st.dataframe(df_bench, width="stretch", hide_index=True)

    st.markdown("<div style='height: 22px;'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # PART 2: SHA-256 HASH-CHAINED AUDIT DASHBOARD
    # -----------------------------------------------------------------------
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
            textwrap.dedent(
                f"""\
                <div class="kpi-card" style="min-height:auto; border-left:4px solid {badge_bg}; padding:12px 16px;">
                <div class="kpi-label">CRYPTOGRAPHIC SHA-256 AUDIT CHAIN STATUS</div>
                <div style="font-size:1.1rem; font-weight:800; color:{badge_bg}; margin-bottom:4px;">
                {'✅ ' if is_chain_ok else '🚨 '}{audit_check['status_label']} ({len(st.session_state.audit_log)} Recorded Events)
                </div>
                <div style="font-size:0.8rem; color:#CBD5E1;">
                {audit_check['summary_message']}
                </div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

    with aud_c2:
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        if st.button("🔍 VERIFY AUDIT INTEGRITY", width="stretch"):
            recheck = verify_audit_chain_detailed(st.session_state.audit_log)
            if recheck["overall_valid"]:
                st.success(f"VERIFIED: {recheck['summary_message']}")
            else:
                st.error(f"INTEGRITY FAILURE: {recheck['summary_message']}")

        if st.button("📋 Record Risk & Final Status Cycle", width="stretch"):
            append_audit_event(
                st.session_state.audit_log,
                stage="ESTIMATE",
                action_type="Risk Assessment Generated",
                details=f"Evaluated scenario '{selected_scenario}' (Hospital Access: {sc_row['Hospital Accessibility (%)']}%).",
            )
            append_audit_event(
                st.session_state.audit_log,
                stage="REPEAT",
                action_type="Final Response Status",
                details=(
                    f"Benchmark verified: Strategy C ETA {sc_row['Avg Emergency Response Time (min)']}m, "
                    f"Reached {sc_row['Reached Incidents']}/{bench_res['total_incidents']} incidents."
                ),
            )
            st.rerun()

    with aud_c3:
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        if st.button("🧪 Simulate Tampering on AUD-002 (Demo)", width="stretch"):
            if len(st.session_state.audit_log) >= 2:
                st.session_state.audit_log[1]["details"] = (
                    "TAMPERED RECORD: Unauthorized edit to incident verification score"
                )
                st.rerun()

        if st.button("🔄 Restore Intact Audit Log", width="stretch"):
            st.session_state.audit_log = create_initial_audit_log()
            st.rerun()

    df_audit_full = get_audit_dataframe(st.session_state.audit_log)[
        [
            "Event ID",
            "Event Type",
            "Stage",
            "Timestamp",
            "Event Description",
            "Previous Hash",
            "Current Hash",
            "Verification Status",
        ]
    ]
    st.dataframe(df_audit_full, width="stretch", hide_index=True)
