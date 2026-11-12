# SANJEEVANI: Member 2 Integration Guide
## Emergency Report Analysis & Evidence Intelligence

**Module Owner:** Member 2  
**Target Audience:** Member 3 (Simulation & Rescue Optimization), Member 4 (Streamlit Dashboard & Integration)  
**Package:** `sanjeevani`

---

## 1. Quick Integration Overview

Member 2 provides the frontline disaster report ingestion, NLP entity extraction, photographic evidence validation, explainable confidence scoring, and triage prioritization engine for **SANJEEVANI**.

All outputs are native, JSON-compatible Python dictionaries designed for immediate consumption by Streamlit (Member 4) and rescue routing algorithms (Member 3).

### Key Import Statement
```python
from sanjeevani import (
    process_emergency_report,
    PersistentImageRegistry,
    load_all_historical_reports,
    save_report_json
)
```

---

## 2. Core API Reference

### `process_emergency_report(...)`
The primary single-entry-point function for the entire evidence intelligence pipeline.

#### Function Signature
```python
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
```

#### Parameters
| Parameter | Type | Default | Description |
|---|---|---|---|
| `raw_text` | `str` | *Required* | Raw message submitted by citizen or responder. |
| `image_path` | `str` or `None` | `None` | Local filesystem path to the uploaded image. |
| `source_id` | `str` | `"anonymous_citizen"` | Unique identifier for reporting user (e.g. phone, username). |
| `source_type` | `str` | `"citizen"` | Source trust tier: `"official"`, `"first_responder"`, `"registered_citizen"`, `"citizen"`. |
| `report_time` | `str` or `None` | `None` | ISO 8601 timestamp. If `None`, defaults to current time. |
| `report_id` | `str` or `None` | `None` | Unique ID. If `None`, auto-generates (`R001`, `R002`, etc.). |
| `registry` | `ImageRegistry` | `None` | Instance of `PersistentImageRegistry` for duplicate detection. |
| `historical_reports` | `List[dict]` | `None` | List of prior reports for contradiction & corroboration checks. |
| `save_record` | `bool` | `False` | When `True`, automatically saves report JSON into `data/reports/`. |
| `archive_image` | `bool` | `False` | When `True`, copies uploaded image into `data/images/`. |

---

## 3. Standard Structured Output Format

The output is a 100% JSON-compatible Python dictionary:

```json
{
  "report_id": "R001",
  "raw_text": "Flood water is entering houses near Zone Z2. 15 people are trapped.",
  "disaster_type": "Flood",
  "location": "Zone Z2",
  "incident": "Flood water is entering houses near Zone Z2",
  "urgency": "High",
  "affected": {
    "count": 15,
    "unit": "people"
  },
  "source_id": "anonymous_citizen",
  "source_type": "citizen",
  "report_time": "2026-11-12T09:17:57",
  "freshness": {
    "age_minutes": 0.0,
    "age_hours": 0.0,
    "is_stale": false,
    "explanation": "Report is fresh (0.0 minutes old).",
    "note": "Freshness measures time since report submission, not the ongoing status of the emergency."
  },
  "evidence": {
    "image_available": true,
    "image_valid": true,
    "image_path": "data/images/synthetic_flood.jpg",
    "image_sha256": "8df30f4291876f89790850aa...",
    "perceptual_hash": "d4d42b2bd4d42b2b",
    "dimensions": {
      "width": 320,
      "height": 240,
      "channels": 3
    },
    "format": "JPEG",
    "file_size_kb": 12.4,
    "possible_duplicate": false,
    "duplicate_type": null,
    "similarity_distance": null,
    "matched_report_id": null,
    "duplicate_explanation": "No duplicate or visually similar images detected in registry.",
    "disclaimer": "Image analysis extracts technical metadata and visual fingerprints. It does NOT prove whether a photograph is genuine, authentic, or staged."
  },
  "corroboration": {
    "is_corroborated": false,
    "corroborating_report_ids": [],
    "duplicate_chatter_ids": [],
    "explanation": "No corroborating reports found."
  },
  "contradictions": [],
  "confidence": {
    "score": 90,
    "verification_status": "Verified",
    "supporting_evidence": [
      "Baseline report structure evaluated (+40 points).",
      "Specific disaster location identified: 'Zone Z2' (+15 points).",
      "Recognized disaster type: 'Flood' (+10 points).",
      "Specific casualty/affected count reported: 15 people (+10 points).",
      "Valid photographic evidence attached and verified via image analysis (+15 points)."
    ],
    "evidence_against": [],
    "missing_information": [],
    "uncertainty_note": "Confidence score reflects information completeness, source reliability, and photographic consistency. It does NOT provide definitive proof of truth. High uncertainty must prompt on-ground inspection."
  },
  "priority": "CRITICAL",
  "priority_reasons": [
    "Immediate life safety hazard detected (trapped/injured indicators present).",
    "15 people directly impacted."
  ],
  "storage": {
    "saved_json_path": "data/reports/R001.json",
    "archived_image_path": "data/images/R001_synthetic_flood.jpg"
  }
}
```

---

## 4. Instructions for Member 4 (Streamlit Dashboard)

Member 4 can integrate Member 2 directly into the Streamlit user interface in just a few lines:

```python
import streamlit as st
from sanjeevani import (
    process_emergency_report,
    PersistentImageRegistry,
    load_all_historical_reports
)

# 1. Initialize persistent state
if "registry" not in st.session_state:
    st.session_state.registry = PersistentImageRegistry()

# 2. UI Input Widgets
st.header("Submit Emergency Report")
report_text = st.text_area("Emergency Incident Details", placeholder="e.g. Severe flooding near Zone Z2. 10 people trapped.")
uploaded_photo = st.file_uploader("Upload Incident Photo (Optional)", type=["jpg", "png", "jpeg", "webp"])
source_role = st.selectbox("Reporter Role", ["citizen", "registered_citizen", "first_responder", "official"])

if st.button("Process & Triage Emergency"):
    # Save uploaded file temporarily if provided
    img_path = None
    if uploaded_photo:
        img_path = f"data/images/{uploaded_photo.name}"
        with open(img_path, "wb") as f:
            f.write(uploaded_photo.getbuffer())

    # Load previous reports for automated contradiction and corroboration checks
    history = load_all_historical_reports()

    # Call Member 2 processing pipeline
    result = process_emergency_report(
        raw_text=report_text,
        image_path=img_path,
        source_type=source_role,
        registry=st.session_state.registry,
        historical_reports=history,
        save_record=True,
        archive_image=True
    )

    # 3. Present Member 2 Results on Streamlit
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Priority", result["priority"])
    col2.metric("Confidence", f"{result['confidence']['score']}%")
    col3.metric("Disaster", result["disaster_type"])
    col4.metric("Location", result["location"] or "Unknown")

    if result["priority"] == "CRITICAL":
        st.error(f"CRITICAL TRIAGE: {', '.join(result['priority_reasons'])}")

    if result["evidence"]["possible_duplicate"]:
        st.warning(f"DUPLICATE IMAGE WARNING: {result['evidence']['duplicate_explanation']}")

    if result["contradictions"]:
        for c in result["contradictions"]:
            st.warning(f"CONTRADICTION ALERT: {c['explanation']}")

    # Verification breakdown accordion
    with st.expander("Explainable Confidence Breakdown"):
        st.write("**Status:**", result["confidence"]["verification_status"])
        st.write("**Supporting Factors:**", result["confidence"]["supporting_evidence"])
        st.write("**Penalties/Against:**", result["confidence"]["evidence_against"])
        st.write("**Missing Info:**", result["confidence"]["missing_information"])
```

---

## 5. Instructions for Member 3 (Disaster Simulation & Rescue Optimization)

Member 3's rescue route optimization algorithms can extract verified target zones, casualty counts, and life-safety priority flags directly from Member 2's output:

```python
from sanjeevani import load_all_historical_reports

def get_high_priority_rescue_targets():
    """
    Extracts high-priority rescue locations and casualty demands for Member 3's
    rescue optimization routing algorithms.
    """
    all_reports = load_all_historical_reports()
    rescue_targets = []

    for rep in all_reports:
        # Filter for active emergencies needing immediate response
        if rep.get("priority") in ("CRITICAL", "HIGH"):
            target = {
                "report_id": rep["report_id"],
                "location": rep["location"],
                "disaster_type": rep["disaster_type"],
                "urgency": rep["urgency"],
                "affected_people": (rep.get("affected") or {}).get("count") or 1,
                "priority": rep["priority"],
                "is_contradicted": len(rep.get("contradictions", [])) > 0,
                "timestamp": rep["report_time"]
            }
            rescue_targets.append(target)

    return rescue_targets
```

---

## 6. Safety & Verification Guarantees

1. **Life-Safety Guarantee:**
   A report with trapped people or life-threatening keywords will **always receive CRITICAL priority**, even if submitted anonymously with no photograph. Life rescue takes precedence over documentation certainty.
2. **Explainable Deduplication:**
   Exact file duplicates (matching SHA-256) are strictly distinguished from perceptual duplicates (matching pHash with Hamming distance $\le 10$).
3. **No Automatic Fake Dismissal:**
   Reused images or contradictory statements are flagged for human operator verification; they are never deleted or discarded automatically.
