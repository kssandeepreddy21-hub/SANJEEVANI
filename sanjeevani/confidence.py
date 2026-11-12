"""
sanjeevani.confidence
--------------------
Evidence confidence scoring, report freshness, contradiction detection,
independent corroboration, and life-safety triage prioritization module
for RESQ-AI / SANJEEVANI (Member 2).

Key Technical Concepts Explained:
1. Explainable Confidence Scoring:
   Instead of an opaque black-box neural network, each scoring factor is an explicit,
   deterministic point adjustment with a transparent explanation breakdown
   (supporting evidence, evidence against, and missing information).

2. Life-Safety-First Prioritization:
   In emergency response triage, human life safety strictly supersedes documentation
   confidence. If a citizen reports trapped, drowning, or injured victims, that report
   MUST be dispatched with CRITICAL priority regardless of whether the confidence score
   is low (e.g. anonymous reporter, unverified photo, or contradictory chatter).

3. Independent Corroboration:
   Distinguishes between independent textual/eyewitness corroboration and independent
   photographic corroboration. Re-sent messages, identical copied chatter, and reused
   or duplicate photographs do NOT count as independent evidence.

4. Source Independence Detection:
   Identifies known vs anonymous sources. Anonymous reports cannot be presumed independent
   without corroborating evidence.

5. Contradiction Detection:
   Differentiates ongoing disasters, resolved incidents, and explicit reports of normal
   conditions to avoid false contradiction alerts from simple keyword overlaps.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set
import re

from .image_analysis import compute_hamming_distance, SIMILARITY_THRESHOLD_DEFAULT


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
    "independent_image_corroboration": 10,
    "penalty_duplicate_image": 25,
    "penalty_visually_similar_image": 15,
    "penalty_contradiction": 30,
    "penalty_stale_report": 15,
    "penalty_missing_location": 20,
    "penalty_unknown_disaster": 15,
}

# Negation and resolution phrases for status classification
RESOLVED_PHRASES = [
    "fire extinguished",
    "fire is extinguished",
    "fire put out",
    "fire has been put out",
    "water receded",
    "water has receded",
    "flood receded",
    "drained",
    "situation under control",
    "under control",
    "rescued and safe",
    "all rescued"
]

NO_DISASTER_PHRASES = [
    "no flooding",
    "no flood",
    "no fire",
    "roads are completely clear",
    "roads are clear",
    "road is clear",
    "all clear",
    "safe and normal",
    "normal and safe",
    "no damage",
    "false alarm",
    "not affected",
    "no incident",
    "normal conditions",
    "everything is normal"
]

ONGOING_DISASTER_PHRASES = [
    "trapped",
    "drowning",
    "injured",
    "buried",
    "stranded",
    "water entering",
    "water rising",
    "water submerged",
    "rising rapidly",
    "rising fast",
    "inundated",
    "inundation",
    "overflowing",
    "burning",
    "flames",
    "smoke",
    "blaze",
    "collapsed",
    "landslide",
    "mudslide",
    "earthquake",
    "building collapse",
    "heavy rainfall",
    "flooding",
    "flood",
    "fire"
]


def is_anonymous_source(source_id: Optional[str], source_type: Optional[str] = None) -> bool:
    """
    Standardizes identification of anonymous or unauthenticated sources.

    Rules:
    - Official agencies, verified first responders, and registered citizens are authenticated tiers.
    - Unauthenticated citizens, missing IDs with citizen tier, or explicit 'anonymous' IDs are anonymous.

    Args:
        source_id: Unique reporter handle or ID string.
        source_type: Trust tier string ('citizen', 'official', etc.).

    Returns:
        bool: True if source identity is anonymous/unknown; False if identified.
    """
    st = str(source_type).strip().lower() if source_type else "citizen"
    # Authenticated trust tiers are treated as verified unless explicitly labeled anonymous
    if st in ("official", "disaster_management", "police", "fire_dept", "first_responder", "paramedic", "volunteer", "registered_citizen", "resident"):
        if source_id:
            sid = str(source_id).strip().lower()
            if sid in ("anonymous", "anonymous_citizen"):
                return True
        return False

    if not source_id:
        return True
    sid = str(source_id).strip().lower()
    if sid in ("anonymous", "anonymous_citizen", "unknown", "none", ""):
        return True
    if st in ("anonymous", "unknown"):
        return True
    return False


def classify_report_status(text: Optional[str]) -> str:
    """
    Determines whether a report describes an ONGOING disaster, a RESOLVED disaster,
    an explicit assertion of NO_DISASTER (clear/normal), or is UNCERTAIN.

    Prevents false contradiction flags from sentences like:
    'The fire is extinguished and everyone is safe.'

    Returns:
        str: 'ONGOING' | 'RESOLVED' | 'NO_DISASTER' | 'UNCERTAIN'
    """
    if not text:
        return "UNCERTAIN"

    clean_text = text.lower()

    # 1. Check explicit NO_DISASTER declarations first
    for phrase in NO_DISASTER_PHRASES:
        if re.search(rf"\b{re.escape(phrase)}\b", clean_text):
            return "NO_DISASTER"

    # 2. Check RESOLVED declarations next (overrides individual mentions of 'fire' or 'flood')
    for phrase in RESOLVED_PHRASES:
        if re.search(rf"\b{re.escape(phrase)}\b", clean_text):
            return "RESOLVED"

    # 3. Check for ONGOING disaster indicators
    for phrase in ONGOING_DISASTER_PHRASES:
        if re.search(rf"\b{re.escape(phrase)}\b", clean_text):
            return "ONGOING"

    return "UNCERTAIN"


def parse_iso_timestamp(timestamp_str: Optional[str]) -> Optional[datetime]:
    """
    Parses an ISO 8601 timestamp string into a Python datetime object.
    Supports timezone-aware and timezone-naive formats.
    """
    if not timestamp_str:
        return None
    try:
        clean_str = timestamp_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_str)
    except Exception:
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

    Rules:
    - 6-hour default threshold for stale classification.
    - Handles missing timestamps without crashing.
    - Gracefully handles timezone-aware and naive datetimes.
    - Safely handles future timestamps (clock skew treated as fresh: 0.0 minutes).
    - An older report must NOT be assumed false; disasters may still be ongoing.

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

    # Match timezones safely
    if report_dt.tzinfo is not None:
        now_dt = current_time or datetime.now(timezone.utc)
        if now_dt.tzinfo is None:
            now_dt = now_dt.replace(tzinfo=timezone.utc)
    else:
        now_dt = current_time or datetime.now()
        if now_dt.tzinfo is not None:
            report_dt = report_dt.replace(tzinfo=now_dt.tzinfo)

    delta = now_dt - report_dt
    total_seconds = delta.total_seconds()

    # Safely handle future timestamps / clock skew
    if total_seconds < 0:
        age_minutes = 0.0
        age_hours = 0.0
        is_stale = False
        explanation = "Report timestamp is current (or slightly future due to minor clock skew; treated as fresh)."
    else:
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
    Identifies reports describing conflicting information about the same location.

    Distinguishes:
    - Ongoing disaster vs No disaster reported (Direct Status Contradiction).
    - Ongoing disaster vs Disaster resolved (Status Discrepancy).
    - Does NOT trigger false contradictions when both indicate resolved or normal conditions.

    Rules:
    - Never automatically assumes either report is correct.
    - Never automatically deletes or dismisses contradictory reports.
    - Flags contradictions for human verification while preserving life-safety triage.

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
    cur_text = current_report.get("raw_text") or ""
    cur_id = current_report.get("report_id", "Current")
    cur_type = (current_report.get("disaster_type") or "Unknown").lower()

    if not cur_loc:
        return contradictions  # Cannot assert contradiction without matching location

    cur_status = classify_report_status(cur_text)

    for prev in historical_reports:
        prev_id = prev.get("report_id", "Unknown")
        if prev_id == cur_id:
            continue

        prev_loc = prev.get("location")
        if not prev_loc or prev_loc.strip().lower() != cur_loc.strip().lower():
            continue  # Must be at the exact same location/zone

        prev_text = prev.get("raw_text") or ""
        prev_type = (prev.get("disaster_type") or "Unknown").lower()
        prev_status = classify_report_status(prev_text)

        # Ensure disaster types are compatible or general
        type_compatible = (
            cur_type == prev_type or
            cur_type == "unknown" or
            prev_type == "unknown" or
            cur_status in ("NO_DISASTER", "RESOLVED") or
            prev_status in ("NO_DISASTER", "RESOLVED")
        )
        if not type_compatible:
            continue

        # Condition A: ONGOING vs NO_DISASTER (Direct Contradiction)
        if (cur_status == "ONGOING" and prev_status == "NO_DISASTER") or (cur_status == "NO_DISASTER" and prev_status == "ONGOING"):
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

        # Condition B: ONGOING vs RESOLVED (Status Discrepancy)
        elif (cur_status == "ONGOING" and prev_status == "RESOLVED") or (cur_status == "RESOLVED" and prev_status == "ONGOING"):
            contradictions.append({
                "conflicting_report_id": prev_id,
                "location": cur_loc,
                "current_text": current_report.get("raw_text"),
                "conflicting_text": prev.get("raw_text"),
                "conflict_type": "Disaster Status Conflict (Ongoing vs Resolved)",
                "explanation": (
                    f"Status discrepancy between Report {cur_id} and Report {prev_id} "
                    f"regarding '{cur_loc}'. One report reports active disaster conditions while the other "
                    f"reports the incident is resolved/cleared. Flagged for human verification; neither report is dismissed."
                )
            })

    return contradictions


def check_corroboration(
    current_report: Dict[str, Any],
    historical_reports: Optional[List[Dict[str, Any]]] = None,
    current_image_analysis: Optional[Dict[str, Any]] = None,
    duplicate_info: Optional[Dict[str, Any]] = None,
    similarity_threshold: int = SIMILARITY_THRESHOLD_DEFAULT
) -> Dict[str, Any]:
    """
    Checks for independent eyewitness and photographic corroboration across historical reports.

    Explicitly Distinguishes:
    A. Independent Textual / Eyewitness Corroboration:
       Different verified/identified sources reporting the same disaster at the same location.
    B. Independent Photographic Corroboration:
       Distinct, non-duplicate photographs verifying the event.
    C. Duplicate Chatter:
       Same source re-submitting or identical copied text.
    D. Duplicate / Visually Similar Images:
       Same photo re-shared across reports (does NOT count as photographic confirmation).
    E. Anonymous / Unknown Independence:
       Reports from anonymous sources where independence cannot be confirmed or disproven.

    Returns:
        Dict[str, Any] with detailed, explainable corroboration breakdown.
    """
    result: Dict[str, Any] = {
        "is_corroborated": False,
        "corroborating_report_ids": [],
        "duplicate_chatter_ids": [],
        "independent_textual_reports": [],
        "independent_image_reports": [],
        "duplicate_image_report_ids": [],
        "visually_similar_report_ids": [],
        "unknown_independence_report_ids": [],
        "explanation": "No corroborating reports found."
    }

    if not historical_reports:
        return result

    cur_id = current_report.get("report_id", "Current")
    cur_loc = current_report.get("location")
    cur_type = current_report.get("disaster_type")
    cur_source_id = current_report.get("source_id")
    cur_source_type = current_report.get("source_type", "citizen")
    cur_text = (current_report.get("raw_text") or "").strip().lower()

    if not cur_loc or not cur_type or cur_type == "Unknown":
        result["explanation"] = "Cannot corroborate report lacking specific location or disaster type."
        return result

    is_cur_anon = is_anonymous_source(cur_source_id, cur_source_type)

    # Extract current image features
    img_meta = current_image_analysis or current_report.get("evidence") or current_report.get("image_analysis") or {}
    cur_sha = img_meta.get("image_sha256")
    cur_phash = img_meta.get("perceptual_hash")
    cur_has_valid_img = bool(img_meta.get("image_valid") or img_meta.get("is_valid"))

    # Incorporate duplicate_info if provided from registry
    if duplicate_info and duplicate_info.get("is_duplicate"):
        matched_id = duplicate_info.get("matched_report_id")
        dup_type = duplicate_info.get("duplicate_type")
        if dup_type == "EXACT" and matched_id:
            result["duplicate_image_report_ids"].append(matched_id)
        elif dup_type == "VISUALLY_SIMILAR" and matched_id:
            result["visually_similar_report_ids"].append(matched_id)

    for prev in historical_reports:
        prev_id = prev.get("report_id", "Unknown")
        if prev_id == cur_id:
            continue

        prev_loc = prev.get("location")
        prev_type = prev.get("disaster_type")
        prev_source_id = prev.get("source_id")
        prev_source_type = prev.get("source_type", "citizen")
        prev_text = (prev.get("raw_text") or "").strip().lower()

        # Match location and disaster type
        if not (prev_loc and prev_loc.strip().lower() == cur_loc.strip().lower() and
                prev_type and prev_type.strip().lower() == cur_type.strip().lower()):
            continue

        # --- 1. Evaluate Source Independence & Textual Chatter ---
        is_prev_anon = is_anonymous_source(prev_source_id, prev_source_type)
        is_identical_text = (prev_text == cur_text and len(cur_text) > 5)
        is_same_source = (not is_cur_anon and not is_prev_anon and prev_source_id == cur_source_id)

        if is_same_source or is_identical_text:
            if prev_id not in result["duplicate_chatter_ids"]:
                result["duplicate_chatter_ids"].append(prev_id)
        elif is_cur_anon or is_prev_anon:
            # Anonymous source: independence cannot be confirmed
            if prev_id not in result["unknown_independence_report_ids"]:
                result["unknown_independence_report_ids"].append(prev_id)
        else:
            # Distinct identified sources with independent text
            if prev_id not in result["independent_textual_reports"]:
                result["independent_textual_reports"].append(prev_id)

        # --- 2. Evaluate Photographic Evidence Independence ---
        prev_ev = prev.get("evidence") or prev.get("image_analysis") or {}
        prev_sha = prev.get("image_sha256") or prev_ev.get("image_sha256")
        prev_phash = prev.get("perceptual_hash") or prev_ev.get("perceptual_hash")
        prev_has_valid_img = bool(prev.get("image_valid") or prev_ev.get("image_valid") or prev_ev.get("is_valid"))

        if cur_has_valid_img and prev_has_valid_img and cur_sha and prev_sha:
            if cur_sha == prev_sha:
                # Exact file duplicate
                if prev_id not in result["duplicate_image_report_ids"]:
                    result["duplicate_image_report_ids"].append(prev_id)
            else:
                # Check perceptual similarity
                dist = None
                if cur_phash and prev_phash:
                    try:
                        dist = compute_hamming_distance(cur_phash, prev_phash)
                    except Exception:
                        dist = None

                if dist is not None and dist <= similarity_threshold:
                    if prev_id not in result["visually_similar_report_ids"]:
                        result["visually_similar_report_ids"].append(prev_id)
                else:
                    # Genuinely independent image
                    if (prev_id not in result["duplicate_chatter_ids"] and
                            prev_id not in result["duplicate_image_report_ids"] and
                            prev_id not in result["visually_similar_report_ids"]):
                        if prev_id in result["independent_textual_reports"]:
                            if prev_id not in result["independent_image_reports"]:
                                result["independent_image_reports"].append(prev_id)

    # Corroborating reports include all independent textual or photographic reports
    corroborating_set = set(result["independent_textual_reports"]) | set(result["independent_image_reports"])
    result["corroborating_report_ids"] = sorted(list(corroborating_set))
    result["is_corroborated"] = len(result["corroborating_report_ids"]) > 0

    # Build human-readable, explainable summary
    explanation_parts = []
    if result["independent_textual_reports"]:
        explanation_parts.append(
            f"Corroborated by {len(result['independent_textual_reports'])} independent report(s) "
            f"({', '.join(result['independent_textual_reports'])}) at {cur_loc}."
        )

    if result["independent_image_reports"]:
        explanation_parts.append(
            f"Independent photographic corroboration confirmed with report(s) ({', '.join(result['independent_image_reports'])})."
        )

    if result["duplicate_image_report_ids"]:
        explanation_parts.append(
            f"Note: Duplicate image detected matching report {', '.join(result['duplicate_image_report_ids'])}; "
            f"does NOT count as independent photographic corroboration."
        )

    if result["visually_similar_report_ids"]:
        explanation_parts.append(
            f"Note: Visually similar image detected matching report {', '.join(result['visually_similar_report_ids'])}; "
            f"flagged for review."
        )

    if result["unknown_independence_report_ids"] and not result["independent_textual_reports"]:
        explanation_parts.append(
            f"Matching report(s) ({', '.join(result['unknown_independence_report_ids'])}) found at {cur_loc}, "
            f"but source independence is unknown (anonymous/unverified source). Does not count as confirmed independent corroboration."
        )

    if result["duplicate_chatter_ids"] and not result["corroborating_report_ids"]:
        explanation_parts.append(
            f"Identical messages or repeated submissions from the same source detected ({', '.join(result['duplicate_chatter_ids'])}). "
            f"These do NOT count as independent corroboration."
        )

    if explanation_parts:
        result["explanation"] = " ".join(explanation_parts)

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
    - Source credibility tier
    - Location completeness
    - Disaster type validity
    - Affected population details
    - Photographic evidence validity
    - Independent textual corroboration bonus (capped to prevent inflation)
    - Independent photographic corroboration bonus
    - Duplicate & visually similar image penalties
    - Contradiction penalty
    - Freshness penalty

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
    source_id = report.get("source_id")

    if is_anonymous_source(source_id, source_type):
        supporting.append("Source is unverified or anonymous (0 bonus points).")
    elif source_type in ("official", "disaster_management", "police", "fire_dept"):
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
        supporting.append("Source is an unverified citizen (0 bonus points).")

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
        supporting.append(
            f"Specific casualty/affected count reported: {affected['count']} {affected.get('unit', 'people')} (+{pts} points)."
        )
    else:
        missing.append("Specific number of affected people")

    # 5. Image Evidence & Duplicate Check
    if image_analysis and image_analysis.get("is_valid"):
        pts = w.get("has_valid_image", 15)
        score += pts
        supporting.append(f"Valid photographic evidence attached and verified via image analysis (+{pts} points).")

        # Duplicate image inspection
        if duplicate_info and duplicate_info.get("is_duplicate"):
            dup_type = duplicate_info.get("duplicate_type")
            if dup_type == "EXACT":
                dup_pts = w.get("penalty_duplicate_image", 25)
                score -= dup_pts
                against.append(
                    f"Image duplicate warning: photo matches previously submitted report {duplicate_info.get('matched_report_id')} "
                    f"({dup_type} duplicate). Flagged for human verification (-{dup_pts} points)."
                )
            elif dup_type == "VISUALLY_SIMILAR":
                dup_pts = w.get("penalty_visually_similar_image", 15)
                score -= dup_pts
                against.append(
                    f"Visually similar image warning: photo is perceptually similar (Hamming distance {duplicate_info.get('hamming_distance')}) "
                    f"to report {duplicate_info.get('matched_report_id')}. Flagged for human verification (-{dup_pts} points)."
                )
    else:
        missing.append("Photographic evidence")
        if image_analysis and image_analysis.get("error"):
            against.append(f"Image inspection error: {image_analysis.get('error')}")

    # 6. Corroboration Scoring
    if corroboration:
        indep_text = corroboration.get("independent_textual_reports", [])
        indep_img = corroboration.get("independent_image_reports", [])
        unknown_src = corroboration.get("unknown_independence_report_ids", [])

        # Textual corroboration bonus (capped once, preventing inflation from multiple messages)
        if indep_text:
            pts = w.get("independent_corroboration", 15)
            score += pts
            supporting.append(f"Independent corroboration from external report(s) {', '.join(indep_text)} (+{pts} points).")

        # Photographic corroboration bonus
        is_dup_img = bool(duplicate_info and duplicate_info.get("is_duplicate"))
        if indep_img and not is_dup_img:
            pts = w.get("independent_image_corroboration", 10)
            score += pts
            supporting.append(f"Independent photographic corroboration from external report(s) {', '.join(indep_img)} (+{pts} points).")

        # Anonymous / unverified sources notification
        if unknown_src and not indep_text:
            against.append(
                f"Matching report(s) from unverified/anonymous source(s) ({', '.join(unknown_src)}); "
                f"independence cannot be confirmed (0 corroboration points)."
            )

    # 7. Contradictions Penalty
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
    elif duplicate_info and duplicate_info.get("duplicate_type") == "EXACT":
        status = "Flagged for Review (Duplicate Image)"
    elif duplicate_info and duplicate_info.get("duplicate_type") == "VISUALLY_SIMILAR":
        status = "Flagged for Review (Visually Similar Image)"
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
    - Urgency to save human lives STRICTLY takes precedence over evidence confidence.
    - A report describing trapped, drowning, or injured victims MUST receive CRITICAL
      priority regardless of low confidence, duplicate photos, or contradictory reports.
    - Low evidence confidence triggers rapid field verification, never inaction or demotion.

    Priority Levels:
    - CRITICAL: Immediate life danger (trapped, drowning, injured victims, high casualty indicators).
    - HIGH: Severe hazard, rising hazard with high affected count, or high urgency.
    - MEDIUM: Water rising, blocked routes, moderate property risk, no trapped lives.
    - LOW: Minor rainfall, waterlogging, resolved or informational reports.
    - NEEDS REVIEW: Conflicting reports or low completeness requiring human review before operational deployment.

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

    # Indicators of immediate life hazard
    life_threat_words = [
        "trapped", "drowning", "injured", "buried", "stranded", "casualt",
        "life-threatening", "dying", "people trapped", "children injured"
    ]
    has_life_threat = any(w in raw_text for w in life_threat_words)

    # Condition 1: Direct life safety threat -> ALWAYS CRITICAL
    if has_life_threat or (urgency == "High" and affected_count and affected_count > 0):
        reasons.append("Immediate life safety hazard detected (trapped/injured indicators present).")
        if affected_count:
            reasons.append(f"{affected_count} {affected.get('unit', 'people')} directly impacted.")
        if conf_score < 50:
            reasons.append(
                f"Confidence is low ({conf_score}%), but priority remains CRITICAL to prevent loss of life. "
                f"Rescue triage prioritizes life safety over documentation certainty."
            )
        if contradictions:
            reasons.append(
                "Contradictory status reports exist, but immediate life hazard indicators take precedence. "
                "Dispatched with CRITICAL urgency while verifying ground conditions."
            )
        return {"priority": "CRITICAL", "reasons": reasons}

    # Condition 2: Conflicting reports without immediate life threat
    if contradictions:
        reasons.append(
            "Contradictory reports exist regarding this incident with no immediate trapped life indicators. "
            "Requires human clarification."
        )
        return {"priority": "NEEDS REVIEW", "reasons": reasons}

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
        reasons.append("Urgency is Medium (infrastructure/road blocked or rising water).")
        return {"priority": "MEDIUM", "reasons": reasons}

    # Condition 6: Low Urgency
    if urgency == "Low":
        reasons.append("Urgency is Low (minor disturbance, no immediate threat to life).")
        return {"priority": "LOW", "reasons": reasons}

    # Condition 7: Unknown urgency / Low completeness
    if conf_score < 40:
        reasons.append("Urgency is unspecified and information completeness is low. Requires human review.")
        return {"priority": "NEEDS REVIEW", "reasons": reasons}

    reasons.append("Moderate priority default based on available incident data.")
    return {"priority": "MEDIUM", "reasons": reasons}
