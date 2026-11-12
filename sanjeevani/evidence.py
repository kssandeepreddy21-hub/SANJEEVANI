"""
sanjeevani.evidence
-------------------
Core Emergency Report Processing and Evidence Intelligence module for SANJEEVANI (Member 2).

Key Features:
- Rule-based entity extraction (Disaster Type, Urgency, Affected Count, Location, Incident Summary).
- Dynamic unique Report ID generation (replaces hardcoded IDs).
- Automatic ISO 8601 report timestamp generation.
- Photographic evidence inspection and perceptual duplicate matching.
- Multi-factor explainable confidence scoring.
- Life-safety-first triage prioritization.
- Seamless compatibility with Member 4 (Streamlit) and other modules.
"""

from datetime import datetime, timezone
import itertools
import os
import re
from typing import Dict, Any, Optional, List

from .image_analysis import analyze_image, ImageRegistry
from .confidence import (
    calculate_report_freshness,
    detect_contradictions,
    check_corroboration,
    evaluate_confidence,
    calculate_priority,
)
from .storage import (
    save_report_json,
    save_evidence_image,
    DEFAULT_REPORTS_DIR,
    DEFAULT_IMAGES_DIR,
)


# Global atomic counter for unique sequential report IDs
_report_counter = itertools.count(1)


def generate_report_id(prefix: str = "R", use_timestamp: bool = False) -> str:
    """
    Generates a unique, non-hardcoded report ID.

    Examples:
        - Sequential: 'R001', 'R002'
        - Timestamped: 'R-20261112-0001'

    Args:
        prefix (str): Prefix letter (default 'R' for Report).
        use_timestamp (bool): If True, prepends YYYYMMDD date.

    Returns:
        str: Unique report ID.
    """
    seq_num = next(_report_counter)
    if use_timestamp:
        today_str = datetime.now().strftime("%Y%m%d")
        return f"{prefix}-{today_str}-{seq_num:04d}"
    return f"{prefix}{seq_num:03d}"


def reset_report_counter(start_value: int = 1) -> None:
    """
    Resets the sequential report ID counter (useful for test suites).
    """
    global _report_counter
    _report_counter = itertools.count(start_value)


# FUNCTION 1: LOCATION EXTRACTION

def extract_location(text: Optional[str]) -> Optional[str]:
    """
    Extracts designated disaster locations, zones, or areas from report text.

    Supports:
    - Standard Zone patterns: 'Zone Z2', 'Zone A1', 'Zone 4'
    - Administrative sectors: 'Sector 5', 'Ward 12', 'Block C'
    - General named areas: 'District Central', 'Area Downtown'

    Args:
        text (str): Raw report text.

    Returns:
        str or None: Extracted location in Title Case, or None if not found.
    """
    if not text:
        return None

    # Priority 1: Official SANJEEVANI Zone notation (e.g., Zone Z2, Zone A3)
    zone_pattern = r"\bZone\s+[A-Z0-9]+\b"
    match = re.search(zone_pattern, text, re.IGNORECASE)
    if match:
        return match.group(0).title()

    # Priority 2: Sector / Ward / Block / District
    admin_pattern = r"\b(?:Sector|Ward|Block|District|Area)\s+[A-Za-z0-9-]+\b"
    match = re.search(admin_pattern, text, re.IGNORECASE)
    if match:
        return match.group(0).title()

    # Priority 3: Landmark / near phrase (e.g., "near Central Bridge")
    landmark_pattern = r"\bnear\s+([A-Z][a-zA-Z0-9\s]+?)(?:[\.,;]|\s+is|\s+are|\s+water|\s+fire|\b)"
    match = re.search(landmark_pattern, text)
    if match:
        extracted = match.group(1).strip().title()
        if len(extracted.split()) <= 4:
            return extracted

    return None


# FUNCTION 2: DISASTER TYPE IDENTIFICATION

def detect_disaster_type(text: Optional[str]) -> str:
    """
    Identifies the type of natural or human-induced disaster from report keywords.

    Categories:
    - Flood, Fire, Earthquake, Landslide, Cyclone, Tsunami, Building Collapse.

    Args:
        text (str): Raw report text.

    Returns:
        str: Detected disaster type (e.g. 'Flood') or 'Unknown'.
    """
    if not text:
        return "Unknown"

    text_lower = text.lower()

    disaster_keywords = {
        "Flood": [
            "flood",
            "flooding",
            "water entering",
            "water submerged",
            "water rising",
            "water level",
            "inundated",
            "inundation",
            "overflowing",
            "drowning",
            "heavy rainfall",
            "heavy rain",
            "waterlogging",
            "rainfall"
        ],
        "Fire": [
            "fire",
            "burning",
            "flames",
            "smoke",
            "blaze",
            "wildfire",
            "explosion"
        ],
        "Earthquake": [
            "earthquake",
            "tremor",
            "ground shaking",
            "aftershock",
            "seismic"
        ],
        "Landslide": [
            "landslide",
            "mudslide",
            "soil collapse",
            "rockfall",
            "debris flow"
        ],
        "Cyclone": [
            "cyclone",
            "hurricane",
            "typhoon",
            "strong winds",
            "gale",
            "storm surge"
        ],
        "Building Collapse": [
            "building collapse",
            "structural collapse",
            "bridge collapse",
            "roof collapsed"
        ],
        "Tsunami": [
            "tsunami",
            "tidal wave"
        ]
    }

    for disaster, keywords in disaster_keywords.items():
        for keyword in keywords:
            # Word boundary check for short words to prevent false positives
            if re.search(rf"\b{re.escape(keyword)}\b", text_lower):
                return disaster

    return "Unknown"


# FUNCTION 3: URGENCY DETECTION

def detect_urgency(text: Optional[str]) -> str:
    """
    Categorizes the emergency urgency level based on life-safety threat indicators.

    Urgency Levels:
    - High: Life-threatening, trapped, drowning, injured, severe danger.
    - Medium: Rising water, blocked roads, property risk, heavy rainfall.
    - Low: Minor waterlogging, light rainfall, safe, normal.
    - Unknown: When no indicators are present.

    Args:
        text (str): Raw report text.

    Returns:
        str: 'High', 'Medium', 'Low', or 'Unknown'.
    """
    if not text:
        return "Unknown"

    text_lower = text.lower()

    high_keywords = [
        "trapped",
        "drowning",
        "injured",
        "stranded",
        "collapsed",
        "life-threatening",
        "emergency",
        "dying",
        "critical",
        "casualties",
        "help needed immediately",
        "urgent"
    ]

    medium_keywords = [
        "water rising",
        "road blocked",
        "roads blocked",
        "flooding",
        "heavy rainfall",
        "submerged",
        "power cut",
        "power outage",
        "rising fast"
    ]

    low_keywords = [
        "light rainfall",
        "minor waterlogging",
        "normal",
        "receded",
        "safe",
        "drained",
        "calm",
        "no damage"
    ]

    # Check high urgency first
    for word in high_keywords:
        if re.search(rf"\b{re.escape(word)}\b", text_lower):
            return "High"

    # Check medium urgency next
    for word in medium_keywords:
        if re.search(rf"\b{re.escape(word)}\b", text_lower):
            return "Medium"

    # Check low urgency
    for word in low_keywords:
        if re.search(rf"\b{re.escape(word)}\b", text_lower):
            return "Low"

    return "Unknown"


# FUNCTION 4: AFFECTED POPULATION EXTRACTION

def extract_affected_count(text: Optional[str]) -> Dict[str, Any]:
    """
    Extracts the estimated number of impacted individuals or families.

    Examples:
    - '15 people are trapped' -> {'count': 15, 'unit': 'people'}
    - '3 families stranded'   -> {'count': 3, 'unit': 'families'}

    Args:
        text (str): Raw report text.

    Returns:
        Dict[str, Any]: {'count': int or None, 'unit': str or None}
    """
    if not text:
        return {"count": None, "unit": None}

    pattern = r"\b(\d+)\s+(people|persons|families|children|residents|victims|citizens|individuals)\b"
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        return {
            "count": int(match.group(1)),
            "unit": match.group(2).lower()
        }

    return {
        "count": None,
        "unit": None
    }


# FUNCTION 5: INCIDENT SUMMARY EXTRACTION

def extract_incident_summary(text: Optional[str], disaster_type: str = "Unknown") -> str:
    """
    Produces a concise incident description from the raw text.

    Args:
        text (str): Raw emergency message.
        disaster_type (str): Identified disaster classification.

    Returns:
        str: Clean summary sentence.
    """
    if not text or not text.strip():
        return "No incident details provided."

    clean_text = text.strip()
    # If text has multiple sentences, take the first informative sentence
    sentences = re.split(r"[.!?]\s*", clean_text)
    if sentences and sentences[0]:
        return sentences[0].strip()

    return clean_text


# FUNCTION 6: COMPLETE REPORT PROCESSING PIPELINE

def process_emergency_report(
    raw_text: str,
    image_path: Optional[str] = None,
    source_id: str = "anonymous_citizen",
    source_type: str = "citizen",
    report_time: Optional[str] = None,
    report_id: Optional[str] = None,
    registry: Optional[ImageRegistry] = None,
    historical_reports: Optional[List[Dict[str, Any]]] = None,
    save_record: bool = False,
    archive_image: bool = False,
    reports_dir: Optional[str] = None,
    images_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    End-to-end processing pipeline for emergency reports and evidence intelligence.

    Combines:
    1. Text analysis (Disaster type, location, urgency, affected count, incident summary).
    2. Image analysis (Validation, SHA-256, Perceptual Hash, format, dimensions).
    3. Perceptual duplicate detection (Hamming distance comparison).
    4. Report freshness calculation.
    5. Independent corroboration detection.
    6. Contradiction identification against historical records.
    7. Multi-factor explainable confidence scoring.
    8. Life-safety-first triage prioritization.
    9. Optional persistence to data/reports/ and image archiving.

    Returns:
        Dict[str, Any]: Standardized JSON-compatible dictionary.
    """
    # 1. Unique Report ID
    actual_report_id = report_id or generate_report_id(prefix="R")

    # 2. Timestamp (ISO 8601)
    actual_report_time = report_time or datetime.now().isoformat(timespec="seconds")

    # 3. Text Entity Extraction
    location = extract_location(raw_text)
    disaster_type = detect_disaster_type(raw_text)
    urgency = detect_urgency(raw_text)
    affected = extract_affected_count(raw_text)
    incident = extract_incident_summary(raw_text, disaster_type=disaster_type)

    # 4. Image Analysis & Perceptual Hashing
    img_data = analyze_image(image_path)
    duplicate_info = {
        "is_duplicate": False,
        "duplicate_type": None,
        "matched_report_id": None,
        "hamming_distance": None,
        "explanation": "No image provided or registry check bypassed."
    }

    if img_data["is_valid"] and registry is not None:
        duplicate_info = registry.check_duplicate(
            sha256_hash=img_data["image_sha256"],
            phash_str=img_data["perceptual_hash"]
        )
        # Register this image into registry for future comparisons
        registry.register(
            report_id=actual_report_id,
            sha256_hash=img_data["image_sha256"],
            phash_str=img_data["perceptual_hash"],
            file_name=img_data["file_name"]
        )

    # 5. Temporal Freshness
    freshness = calculate_report_freshness(actual_report_time)

    # 6. Historical Checks: Corroboration & Contradictions
    interim_report = {
        "report_id": actual_report_id,
        "raw_text": raw_text,
        "location": location,
        "disaster_type": disaster_type,
        "source_id": source_id,
        "source_type": source_type,
        "affected": affected,
        "urgency": urgency,
        "report_time": actual_report_time
    }

    contradictions = detect_contradictions(interim_report, historical_reports)
    corroboration = check_corroboration(interim_report, historical_reports)

    # 7. Confidence Scoring
    confidence = evaluate_confidence(
        report=interim_report,
        image_analysis=img_data,
        duplicate_info=duplicate_info,
        freshness=freshness,
        corroboration=corroboration,
        contradictions=contradictions
    )

    # 8. Report Prioritization
    priority_info = calculate_priority(
        report=interim_report,
        confidence=confidence,
        contradictions=contradictions
    )

    # 9. Build Final Structured Output (JSON-compatible)
    final_output = {
        "report_id": actual_report_id,
        "raw_text": raw_text,
        "disaster_type": disaster_type,
        "location": location,
        "incident": incident,
        "urgency": urgency,
        "affected": affected,
        "source_id": source_id,
        "source_type": source_type,
        "report_time": actual_report_time,
        "freshness": freshness,
        "evidence": {
            "image_available": img_data["image_available"],
            "image_valid": img_data["is_valid"],
            "image_path": img_data.get("image_path"),
            "image_sha256": img_data.get("image_sha256"),
            "perceptual_hash": img_data.get("perceptual_hash"),
            "dimensions": img_data.get("dimensions"),
            "format": img_data.get("format"),
            "file_size_kb": img_data.get("file_size_kb"),
            "possible_duplicate": duplicate_info.get("is_duplicate", False),
            "duplicate_type": duplicate_info.get("duplicate_type"),
            "similarity_distance": duplicate_info.get("hamming_distance"),
            "matched_report_id": duplicate_info.get("matched_report_id"),
            "duplicate_explanation": duplicate_info.get("explanation"),
            "disclaimer": img_data.get("disclaimer")
        },
        "corroboration": corroboration,
        "contradictions": contradictions,
        "confidence": confidence,
        "priority": priority_info["priority"],
        "priority_reasons": priority_info["reasons"],
        "storage": {
            "saved_json_path": None,
            "archived_image_path": None
        }
    }

    # Optional permanent archiving of evidence image
    if archive_image and image_path and img_data.get("is_valid"):
        archived_img = save_evidence_image(
            source_image_path=image_path,
            report_id=actual_report_id,
            images_dir=images_dir or DEFAULT_IMAGES_DIR
        )
        final_output["storage"]["archived_image_path"] = archived_img

    # Optional persistent storage of JSON report
    if save_record:
        saved_path = save_report_json(
            report=final_output,
            reports_dir=reports_dir or DEFAULT_REPORTS_DIR
        )
        final_output["storage"]["saved_json_path"] = saved_path

    return final_output


# CLI INTERACTIVE RECEIVE FUNCTION (Maintains backward compatibility with user's original file)

def receive_report() -> Dict[str, Any]:
    """
    Interactive command-line function to receive, parse, and analyze an emergency report.
    Keeps the user's initial workflow running with enhanced capabilities.
    """
    print("===================================")
    print("       SANJEEVANI EMERGENCY")
    print("    REPORT & EVIDENCE SYSTEM")
    print("===================================")

    report_text = input("\nEnter emergency report: ")
    image_input = input("Enter image path (leave blank if none): ").strip()
    image_path = image_input if image_input else None

    report = process_emergency_report(
        raw_text=report_text,
        image_path=image_path
    )

    return report


# MAIN PROGRAM EXECUTION

if __name__ == "__main__":
    emergency_report = receive_report()

    print("\n========== ANALYSED REPORT ==========")
    for key, value in emergency_report.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for sub_key, sub_val in value.items():
                print(f"  {sub_key}: {sub_val}")
        else:
            print(f"{key}: {value}")
