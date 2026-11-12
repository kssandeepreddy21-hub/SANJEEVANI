"""
SANJEEVANI: Emergency Report Analysis & Evidence Intelligence Module (Member 2).

This package provides tools for:
- Parsing emergency reports (location, disaster type, urgency, affected count).
- Image validation, SHA-256 hashing, and perceptual duplicate detection.
- Explainable confidence scoring and independent corroboration.
- Life-safety-first triage prioritization.
- Contradiction and freshness detection.
- Persistent evidence storage (reports and images).
"""

from .evidence import (
    extract_location,
    detect_disaster_type,
    detect_urgency,
    extract_affected_count,
    extract_incident_summary,
    generate_report_id,
    reset_report_counter,
    process_emergency_report,
    receive_report
)

from .image_analysis import (
    analyze_image,
    compute_file_sha256,
    compute_perceptual_hash,
    compute_hamming_distance,
    ImageRegistry
)

from .confidence import (
    calculate_report_freshness,
    detect_contradictions,
    check_corroboration,
    evaluate_confidence,
    calculate_priority
)

from .storage import (
    ensure_directories,
    save_report_json,
    load_report_json,
    load_all_historical_reports,
    save_evidence_image,
    PersistentImageRegistry
)

__all__ = [
    "extract_location",
    "detect_disaster_type",
    "detect_urgency",
    "extract_affected_count",
    "extract_incident_summary",
    "generate_report_id",
    "reset_report_counter",
    "process_emergency_report",
    "receive_report",
    "analyze_image",
    "compute_file_sha256",
    "compute_perceptual_hash",
    "compute_hamming_distance",
    "ImageRegistry",
    "calculate_report_freshness",
    "detect_contradictions",
    "check_corroboration",
    "evaluate_confidence",
    "calculate_priority",
    "ensure_directories",
    "save_report_json",
    "load_report_json",
    "load_all_historical_reports",
    "save_evidence_image",
    "PersistentImageRegistry"
]
