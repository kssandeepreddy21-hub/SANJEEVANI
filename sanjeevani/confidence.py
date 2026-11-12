"""
sanjeevani.confidence
--------------------
Evidence confidence scoring, report freshness, contradiction detection,
independent corroboration, and life-safety triage prioritization module.

Key Technical Concepts Explained:
1. Explainable Confidence Scoring:
   Instead of a black-box model, each score factor is an explicit point addition
   or subtraction with a transparent explanation list (supporting evidence,
   evidence against, and missing information).

2. Life-Safety-First Prioritization:
   In emergency response triage, urgency and evidence confidence must remain distinct.
   If a citizen reports people trapped in floodwaters, that report MUST receive CRITICAL
   or HIGH priority for immediate inspection, even if the confidence score is low
   (e.g., anonymous reporter without an image). The cost of ignoring a real trapped
   human life is catastrophic.

3. Independent Corroboration:
   Two reports corroborate each other ONLY if they originate from distinct sources
   with independent wording. Re-sent or copied messages from the same user are duplicate
   chatter and do not count as independent confirmation.

4. Contradiction Detection:
   When one report claims an ongoing disaster at a location and another claims normal
   conditions or complete resolution, neither is assumed correct. The conflict is
   explicitly flagged for human decision-makers.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import re


# Configurable weights for scoring factors
DEFAULT_CONFIDENCE_WEIGHTS = {
    "base_score": 40,
    "source_official": 25,
    "source_first_responder": 20,
    "source_registered_citizen": 10,
    "source_anonymous": 0,
    "has_valid_location": 15,
    "has_disaster_type": 10,
    "has_affected_count": 10,
    "has_valid_image": 15,
    "independent_corroboration": 15,
    "penalty_duplicate_image": 25,
    "penalty_contradiction": 30,
    "penalty_stale_report": 15,
    "penalty_missing_location": 20,
    "penalty_unknown_disaster": 15,
}

# Negation and resolution keywords for contradiction detection
NEGATION_KEYWORDS = [
    "no flooding",
    "no flood",
    "water receded",
    "water has receded",
    "no fire",
    "fire extinguished",
    "fire put out",
    "safe",
    "all clear",
    "normal",
    "drained",
    "no damage",
    "false alarm",
    "not affected",
    "situation under control"
]

AFFIRMATIVE_DISASTER_KEYWORDS = [
    "flood",
    "flooding",
    "water rising",
    "submerged",
    "water entering",
    "fire",
    "burning",
    "flames",
    "smoke",
    "trapped",
    "drowning",
    "collapsed",
    "landslide",
    "earthquake"
]


def parse_iso_timestamp(timestamp_str: Optional[str]) -> Optional[datetime]:
    """
    Parses an ISO 8601 timestamp string into a Python datetime object.
    Supports with or without timezone.
    """
    if not timestamp_str:
        return None
    try:
        # Handles 'Z' or standard ISO strings
        clean_str = timestamp_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_str)
    except Exception:
        # Fallback for unexpected formats
        try:
            return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None


def calculate_report_freshness(
    report_time_str: Optional[str],
    current_time: Optional[datetime] = None,
    stale_threshold_hours: float = 6.0
) -> Dict[str, Any]:
    """
    Calculates how old an emergency report is based on its timestamp.

    Important:
    An old report must not be assumed false. It may describe an incident
    that is still active or recovering.

    Args:
        report_time_str: ISO timestamp string of the report.
        current_time: Reference time (defaults to datetime.now()).
        stale_threshold_hours: Hours after which a report is flagged stale.

    Returns:
        Dict[str, Any] with age_minutes, age_hours, is_stale, and explanation.
    """
    report_dt = parse_iso_timestamp(report_time_str)

    if report_dt is None:
        return {
            "age_minutes": None,
            "age_hours": None,
            "is_stale": False,
            "explanation": "No valid timestamp available to calculate freshness.",
            "note": "Timestamp missing; freshness could not be determined."
        }

    now_dt = current_time or datetime.now(report_dt.tzinfo if report_dt.tzinfo else None)

    # Avoid naive vs aware mismatch
    if report_dt.tzinfo is not None and now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=report_dt.tzinfo)
    elif report_dt.tzinfo is None and now_dt.tzinfo is not None:
        report_dt = report_dt.replace(tzinfo=now_dt.tzinfo)

    delta = now_dt - report_dt
    total_seconds = max(0.0, delta.total_seconds())
    age_minutes = round(total_seconds / 60.0, 1)
    age_hours = round(total_seconds / 3600.0, 2)

    is_stale = age_hours > stale_threshold_hours

    if is_stale:
        explanation = (
            f"Report is {age_hours} hours old (exceeds freshness threshold of {stale_threshold_hours} hours). "
            f"Note: An older report must NOT be assumed false; the disaster may still be ongoing."
        )
    else:
        explanation = f"Report is fresh ({age_minutes} minutes old)."

    return {
        "age_minutes": age_minutes,
        "age_hours": age_hours,
        "is_stale": is_stale,
        "explanation": explanation,
        "note": "Freshness measures time since report submission, not the ongoing status of the emergency."
    }


def detect_contradictions(
    current_report: Dict[str, Any],
    historical_reports: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Identifies reports describing conflicting information about the same location and incident.

    Example:
    Report A: 'Severe flooding near Zone Z2.'
    Report B: 'No flooding reported near Zone Z2.'

    Rules:
    - Flags possible contradictions for human verification.
    - Never automatically decides which report is correct.

    Args:
        current_report: The report currently being analyzed.
        historical_reports: List of prior processed reports.

    Returns:
        List[Dict[str, Any]]: Detected contradiction notices.
    """
    contradictions: List[Dict[str, Any]] = []

    if not historical_reports:
        return contradictions

    cur_loc = current_report.get("location")
    cur_text = (current_report.get("raw_text") or "").lower()
    cur_id = current_report.get("report_id", "Current")

    if not cur_loc:
        return contradictions  # Cannot match contradiction without known location

    # Determine if current report is asserting or negating
    cur_has_negation = any(neg in cur_text for neg in NEGATION_KEYWORDS)
    cur_has_affirmation = any(aff in cur_text for aff in AFFIRMATIVE_DISASTER_KEYWORDS)

    for prev in historical_reports:
        prev_loc = prev.get("location")
        prev_id = prev.get("report_id", "Unknown")

        if prev_id == cur_id:
            continue

        # Location match (case-insensitive)
        if prev_loc and prev_loc.strip().lower() == cur_loc.strip().lower():
            prev_text = (prev.get("raw_text") or "").lower()
            prev_has_negation = any(neg in prev_text for neg in NEGATION_KEYWORDS)
            prev_has_affirmation = any(aff in prev_text for aff in AFFIRMATIVE_DISASTER_KEYWORDS)

            # Contradiction condition: one affirms disaster, the other negates it
            is_conflicting = (cur_has_negation and prev_has_affirmation) or (cur_has_affirmation and prev_has_negation)

            if is_conflicting:
                contradictions.append({
                    "conflicting_report_id": prev_id,
                    "location": cur_loc,
                    "current_text": current_report.get("raw_text"),
                    "conflicting_text": prev.get("raw_text"),
                    "conflict_type": "Direct Status Contradiction",
                    "explanation": (
                        f"Potential contradiction between Report {cur_id} and Report {prev_id} "
                        f"regarding '{cur_loc}'. One report indicates disaster conditions while the other "
                        f"indicates normal/cleared status. Flagged for human verification; neither report is dismissed."
                    )
                })

    return contradictions


def check_corroboration(
    current_report: Dict[str, Any],
    historical_reports: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Checks if independent reports corroborate the incident at the same location.

    Rules:
    - Multiple reports from the SAME source or copied messages do NOT count as independent corroboration.
    - Reports from different sources supporting the same disaster type at the same location DO corroborate.

    Returns:
        Dict[str, Any] with corroboration details.
    """
    result = {
        "is_corroborated": False,
        "corroborating_report_ids": [],
        "duplicate_chatter_ids": [],
        "explanation": "No corroborating reports found."
    }

    if not historical_reports:
        return result

    cur_loc = current_report.get("location")
    cur_type = current_report.get("disaster_type")
    cur_source = current_report.get("source_id", "anonymous")
    cur_text = (current_report.get("raw_text") or "").strip().lower()
    cur_id = current_report.get("report_id", "Current")

    if not cur_loc or cur_type == "Unknown":
        result["explanation"] = "Cannot corroborate report lacking specific location or disaster type."
        return result

    corroborating_ids = []
    duplicate_chatter_ids = []

    for prev in historical_reports:
        prev_id = prev.get("report_id", "Unknown")
        if prev_id == cur_id:
            continue

        prev_loc = prev.get("location")
        prev_type = prev.get("disaster_type")
        prev_source = prev.get("source_id", "anonymous")
        prev_text = (prev.get("raw_text") or "").strip().lower()

        # Check location and disaster type match
        if (prev_loc and prev_loc.strip().lower() == cur_loc.strip().lower() and
                prev_type and prev_type.lower() == cur_type.lower()):

            # Check if it's the exact same source or verbatim copied text
            is_same_source = (prev_source == cur_source and cur_source != "anonymous")
            is_identical_text = (prev_text == cur_text and len(cur_text) > 5)

            if is_same_source or is_identical_text:
                duplicate_chatter_ids.append(prev_id)
            else:
                corroborating_ids.append(prev_id)

    if corroborating_ids:
        result["is_corroborated"] = True
        result["corroborating_report_ids"] = corroborating_ids
        result["duplicate_chatter_ids"] = duplicate_chatter_ids
        result["explanation"] = (
            f"Corroborated by {len(corroborating_ids)} independent report(s) "
            f"({', '.join(corroborating_ids)}) at {cur_loc}."
        )
    elif duplicate_chatter_ids:
        result["duplicate_chatter_ids"] = duplicate_chatter_ids
        result["explanation"] = (
            f"Identical messages or repeated submissions from the same source detected ({', '.join(duplicate_chatter_ids)}). "
            f"These do NOT count as independent corroboration."
        )

    return result


def evaluate_confidence(
    report: Dict[str, Any],
    image_analysis: Optional[Dict[str, Any]] = None,
    duplicate_info: Optional[Dict[str, Any]] = None,
    freshness: Optional[Dict[str, Any]] = None,
    corroboration: Optional[Dict[str, Any]] = None,
    contradictions: Optional[List[Dict[str, Any]]] = None,
    weights: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Computes an explainable confidence score and verification status for an emergency report.

    Transparent Breakdown:
    - Base score
    - Source credibility
    - Location completeness
    - Disaster type validity
    - Affected population details
    - Photographic evidence validity
    - Independent corroboration bonus
    - Duplicate image penalties
    - Contradiction penalties
    - Freshness penalties

    Returns:
        Dict[str, Any] with score, verification_status, supporting_evidence,
        evidence_against, missing_information, and uncertainty_note.
    """
    w = weights or DEFAULT_CONFIDENCE_WEIGHTS
    score = w.get("base_score", 40)

    supporting: List[str] = [f"Baseline report structure evaluated (+{score} points)."]
    against: List[str] = []
    missing: List[str] = []

    # 1. Source Reliability
    source_type = (report.get("source_type") or "citizen").lower()
    if source_type in ("official", "disaster_management", "police", "fire_dept"):
        pts = w.get("source_official", 25)
        score += pts
        supporting.append(f"Source verified as official agency/responder (+{pts} points).")
    elif source_type in ("first_responder", "paramedic", "volunteer"):
        pts = w.get("source_first_responder", 20)
        score += pts
        supporting.append(f"Source is a verified field responder (+{pts} points).")
    elif source_type in ("registered_citizen", "resident"):
        pts = w.get("source_registered_citizen", 10)
        score += pts
        supporting.append(f"Source is an authenticated citizen (+{pts} points).")
    else:
        supporting.append("Source is unverified or anonymous (0 bonus points).")

    # 2. Location
    loc = report.get("location")
    if loc:
        pts = w.get("has_valid_location", 15)
        score += pts
        supporting.append(f"Specific disaster location identified: '{loc}' (+{pts} points).")
    else:
        pts = w.get("penalty_missing_location", 20)
        score -= pts
        against.append(f"Missing specific location coordinates or zone (-{pts} points).")
        missing.append("Specific location / zone")

    # 3. Disaster Type
    dtype = report.get("disaster_type", "Unknown")
    if dtype and dtype != "Unknown":
        pts = w.get("has_disaster_type", 10)
        score += pts
        supporting.append(f"Recognized disaster type: '{dtype}' (+{pts} points).")
    else:
        pts = w.get("penalty_unknown_disaster", 15)
        score -= pts
        against.append(f"Disaster type could not be determined from report text (-{pts} points).")
        missing.append("Disaster classification")

    # 4. Affected Count
    affected = report.get("affected") or {}
    if affected.get("count") is not None:
        pts = w.get("has_affected_count", 10)
        score += pts
        supporting.append(f"Specific casualty/affected count reported: {affected['count']} {affected.get('unit', 'people')} (+{pts} points).")
    else:
        missing.append("Specific number of affected people")

    # 5. Image Evidence & Duplicate Check
    if image_analysis and image_analysis.get("is_valid"):
        pts = w.get("has_valid_image", 15)
        score += pts
        supporting.append(f"Valid photographic evidence attached and verified via image analysis (+{pts} points).")

        # Check duplicate image warning
        if duplicate_info and duplicate_info.get("is_duplicate"):
            dup_pts = w.get("penalty_duplicate_image", 25)
            score -= dup_pts
            dup_type = duplicate_info.get("duplicate_type")
            against.append(
                f"Image duplicate warning: photo matches previously submitted report {duplicate_info.get('matched_report_id')} "
                f"({dup_type} duplicate). Flagged for human verification (-{dup_pts} points)."
            )
    else:
        missing.append("Photographic evidence")
        if image_analysis and image_analysis.get("error"):
            against.append(f"Image inspection error: {image_analysis.get('error')}")

    # 6. Independent Corroboration
    if corroboration and corroboration.get("is_corroborated"):
        pts = w.get("independent_corroboration", 15)
        score += pts
        corr_ids = ", ".join(corroboration.get("corroborating_report_ids", []))
        supporting.append(f"Independent corroboration from external report(s) {corr_ids} (+{pts} points).")

    # 7. Contradictions
    if contradictions:
        pts = w.get("penalty_contradiction", 30)
        score -= pts
        conflicting_ids = ", ".join(c.get("conflicting_report_id", "N/A") for c in contradictions)
        against.append(f"Contradictory reports exist for this location from {conflicting_ids} (-{pts} points).")

    # 8. Freshness Penalty
    if freshness and freshness.get("is_stale"):
        pts = w.get("penalty_stale_report", 15)
        score -= pts
        against.append(f"Report is older than {freshness.get('age_hours')} hours; temporal uncertainty (-{pts} points).")

    # Clamp score between 0 and 100
    final_score = max(0, min(100, score))

    # Determine Verification Status
    if contradictions:
        status = "Flagged for Review (Contradiction)"
    elif duplicate_info and duplicate_info.get("is_duplicate"):
        status = "Flagged for Review (Duplicate Image)"
    elif final_score >= 80:
        status = "Verified"
    elif final_score >= 50:
        status = "Pending Verification"
    else:
        status = "Unverified"

    return {
        "score": final_score,
        "verification_status": status,
        "supporting_evidence": supporting,
        "evidence_against": against,
        "missing_information": missing,
        "uncertainty_note": (
            "Confidence score reflects information completeness, source reliability, and photographic consistency. "
            "It does NOT provide definitive proof of truth. High uncertainty must prompt on-ground inspection."
        )
    }


def calculate_priority(
    report: Dict[str, Any],
    confidence: Dict[str, Any],
    contradictions: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Computes an explainable triage priority for the emergency report.

    Life-Safety Guarantee:
    - Urgency to save human lives takes precedence over verification confidence.
    - A report describing trapped people MUST NOT be demoted to LOW priority
      simply because confidence is low or unverified.

    Priority Levels:
    - CRITICAL: Immediate life danger (trapped, drowning, fire with victims, large affected count).
    - HIGH: Severe hazard or high urgency, or moderate affected count.
    - MEDIUM: Water rising, blocked routes, moderate property risk, no trapped lives.
    - LOW: Minor rainfall, waterlogging, resolved or informational.
    - NEEDS REVIEW: Conflicting reports requiring human resolution before operational deployment.

    Returns:
        Dict[str, Any] with priority (str) and reasons (List[str]).
    """
    urgency = (report.get("urgency") or "Unknown").title()
    affected = report.get("affected") or {}
    affected_count = affected.get("count")
    disaster_type = (report.get("disaster_type") or "Unknown").title()
    raw_text = (report.get("raw_text") or "").lower()
    conf_score = confidence.get("score", 0)

    reasons: List[str] = []

    # Life-threatening indicators
    life_threat_words = ["trapped", "drowning", "injured", "buried", "stranded", "casualt", "life-threatening"]
    has_life_threat = any(w in raw_text for w in life_threat_words)

    # Condition 1: Conflicting reports
    if contradictions and not has_life_threat:
        reasons.append(
            "Contradictory reports exist regarding this incident with no immediate trapped life indicators. "
            "Requires human clarification."
        )
        return {"priority": "NEEDS REVIEW", "reasons": reasons}

    # Condition 2: Trapped people or direct life danger -> CRITICAL
    if has_life_threat or (urgency == "High" and affected_count and affected_count > 0):
        reasons.append(f"Immediate life safety hazard detected (trapped/injured indicators present).")
        if affected_count:
            reasons.append(f"{affected_count} {affected.get('unit', 'people')} directly impacted.")
        if conf_score < 50:
            reasons.append(
                f"Confidence is low ({conf_score}%), but priority remains CRITICAL to prevent loss of life. "
                f"Rescue triage prioritizes life safety over documentation certainty."
            )
        return {"priority": "CRITICAL", "reasons": reasons}

    # Condition 3: High Urgency
    if urgency == "High":
        reasons.append(f"Urgency is High for disaster '{disaster_type}'.")
        return {"priority": "HIGH", "reasons": reasons}

    # Condition 4: Medium Urgency with significant affected count
    if urgency == "Medium" and affected_count and affected_count >= 10:
        reasons.append(f"Urgency is Medium, but high affected population ({affected_count} people) escalates priority.")
        return {"priority": "HIGH", "reasons": reasons}

    # Condition 5: Medium Urgency
    if urgency == "Medium":
        reasons.append(f"Urgency is Medium (infrastructure/road blocked or rising water).")
        return {"priority": "MEDIUM", "reasons": reasons}

    # Condition 6: Low Urgency
    if urgency == "Low":
        reasons.append(f"Urgency is Low (minor disturbance, no immediate threat to life).")
        return {"priority": "LOW", "reasons": reasons}

    # Condition 7: Unknown urgency / Missing info
    if conf_score < 40:
        reasons.append("Urgency is unspecified and information completeness is low. Requires human review.")
        return {"priority": "NEEDS REVIEW", "reasons": reasons}

    reasons.append("Moderate priority default based on available incident data.")
    return {"priority": "MEDIUM", "reasons": reasons}
