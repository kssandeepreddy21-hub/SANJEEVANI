"""
sanjeevani/evidence.py
----------------------
Member 2 Interface: Emergency Report Analysis & Evidence Intelligence.
Provides clean, modular functions for sanitizing incoming emergency reports,
calculating synthetic evidence confidence scores, flagging duplicate media,
and filtering/summarizing incident queues for Section 3 (Live Response).
"""

from datetime import datetime
import html
import pandas as pd

from sanjeevani.data import CITY_CENTER


SECTOR_COORDINATES = {
    "Sector 4 Lowlands": (12.9655, 77.5920),
    "Central Riverfront": (12.9740, 77.5975),
    "North District": (12.9865, 77.5865),
    "South Valley": (12.9575, 77.6020),
    "East Basin": (12.9695, 77.6095),
    "West Connector": (12.9705, 77.5860),
}


def score_emergency_report(
    title: str,
    sector: str,
    disaster_type: str,
    urgency: str,
    simulate_duplicate: bool = False,
    existing_custom_count: int = 0,
) -> dict:
    """
    Validate, sanitize, and score a newly submitted emergency report.
    Escapes HTML characters in user-supplied title to prevent broken markup or XSS.
    """
    raw_title = (title or "").strip()
    if not raw_title:
        raise ValueError("Incident description/title cannot be empty.")

    safe_title = html.escape(raw_title)
    new_id = f"INC-{906 + max(0, int(existing_custom_count))}"
    base_lat, base_lon = SECTOR_COORDINATES.get(sector, CITY_CENTER)
    offset = 0.0012 * (max(0, int(existing_custom_count)) + 1)

    if simulate_duplicate:
        calc_conf = 0.31
        dup_status = "⚠️ FLAGGED: Duplicate Image Hash Match"
        is_verified = False
    else:
        calc_conf = 0.93 if urgency == "CRITICAL" else 0.84
        dup_status = "Clear (Unique Image)"
        is_verified = True

    return {
        "incident_id": new_id,
        "title": safe_title,
        "type": disaster_type,
        "urgency": urgency if urgency in ("CRITICAL", "WARNING") else "WARNING",
        "confidence": calc_conf,
        "lat": round(base_lat + offset, 4),
        "lon": round(base_lon - offset, 4),
        "sector": sector if sector in SECTOR_COORDINATES else "Central Riverfront",
        "reported_at": datetime.now().strftime("%H:%M"),
        "verified": is_verified,
        "duplicate_warning": dup_status,
    }


def filter_incident_reports(
    incidents_df: pd.DataFrame,
    urgency_filter: str = "ALL",
    verify_filter: str = "ALL",
) -> pd.DataFrame:
    """Filter incident reports safely by urgency and verification status."""
    if incidents_df is None or incidents_df.empty:
        return pd.DataFrame(
            columns=[
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
        )

    df_filtered = incidents_df.copy()
    if urgency_filter != "ALL" and "urgency" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["urgency"] == urgency_filter]

    if "verified" in df_filtered.columns:
        if verify_filter == "Verified Only":
            df_filtered = df_filtered[df_filtered["verified"] == True]  # noqa: E712
        elif verify_filter == "Pending / Unverified Only":
            df_filtered = df_filtered[df_filtered["verified"] == False]  # noqa: E712

    return df_filtered


def summarize_evidence_metrics(incidents_df: pd.DataFrame) -> dict:
    """Compute top-level evidence intelligence KPI metrics safely."""
    if incidents_df is None or incidents_df.empty:
        return {
            "total_reports": 0,
            "critical_count": 0,
            "verified_count": 0,
            "duplicate_flagged_count": 0,
            "mean_confidence_pct": 0.0,
        }

    total_reports = len(incidents_df)
    crit_count = (
        int((incidents_df["urgency"] == "CRITICAL").sum())
        if "urgency" in incidents_df.columns
        else 0
    )
    verified_count = (
        int(incidents_df["verified"].sum())
        if "verified" in incidents_df.columns
        else 0
    )
    dup_count = (
        int(incidents_df["duplicate_warning"].astype(str).str.contains("FLAGGED").sum())
        if "duplicate_warning" in incidents_df.columns
        else 0
    )
    avg_conf = (
        round(float(incidents_df["confidence"].mean()) * 100.0, 1)
        if "confidence" in incidents_df.columns
        else 0.0
    )

    return {
        "total_reports": total_reports,
        "critical_count": crit_count,
        "verified_count": verified_count,
        "duplicate_flagged_count": dup_count,
        "mean_confidence_pct": avg_conf,
    }
