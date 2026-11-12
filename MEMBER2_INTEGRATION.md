# SANJEEVANI: Member 2 Integration Guide
## Emergency Report Analysis & Evidence Intelligence

**Module Owner:** Member 2  
**Target Audience:** Member 3 (Simulation & Rescue Optimization), Member 4 (Streamlit Dashboard & Integration)  
**Package:** `sanjeevani`

---

## 1. Quick Integration Overview

Member 2 provides the frontline disaster report ingestion, NLP entity extraction, photographic evidence validation, explainable confidence scoring, and life-safety triage prioritization engine for **SANJEEVANI** / **RESQ-AI**.

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
    source_id: Optional[str] = "anonymous_citizen",
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
| `source_id` | `str` or `None` | `"anonymous_citizen"` | Unique identifier for reporting user (e.g. phone, username). |
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
  "source_id": "citizen_alice",
  "source_type": "citizen",
  "report_time": "2026-11-12T11:10:25",
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
      "channels": 3,
      "cv2_shape": [240, 320, 3]
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
    "independent_textual_reports": [],
    "independent_image_reports": [],
    "duplicate_image_report_ids": [],
    "visually_similar_report_ids": [],
    "unknown_independence_report_ids": [],
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

## 4. Key Architectural Enhancements & Fixes

### A. Independent Textual vs Photographic Corroboration
The system strictly distinguishes between:
1. **Independent Textual Corroboration (`independent_textual_reports`):**
   Different identified sources reporting the same disaster at the same location.
2. **Independent Photographic Corroboration (`independent_image_reports`):**
   Genuinely distinct photographs verifying the scene.
3. **Duplicate Images (`duplicate_image_report_ids`):**
   Same SHA-256 binary hash across multiple reports. Re-sharing an image never increases photographic corroboration.
4. **Visually Similar Images (`visually_similar_report_ids`):**
   pHash Hamming distance $\le 10$. Re-compressed, cropped, or filtered versions of the same photo are flagged for human review.

### B. Anonymous Source Handling
- Identified sources (officials, first responders, registered citizens) are eligible for independent corroboration.
- Anonymous reports (`source_id: None` or `"anonymous_citizen"`) are categorized under `unknown_independence_report_ids`.
- The system never assumes independence between multiple anonymous messages, avoiding viral bot or copied rumor inflation.

### C. False Contradiction Prevention
- Distinguishes **ONGOING**, **RESOLVED**, and **NO_DISASTER** (all clear) states.
- Statements like *"The fire is extinguished and everyone is safe"* are identified as `RESOLVED` and do not generate false contradiction alerts when compared with *"Area is clear, no fire"*.
- Genuine contradictions (e.g. *"Severe flood rising"* vs *"No flood, completely dry"*) are flagged for human verification without discarding either report.

### D. Life-Safety-First Prioritization Guarantee
- Urgent life-threat cues (`trapped`, `drowning`, `injured`, `buried`, `stranded`) trigger **CRITICAL priority unconditionally**.
- Low evidence confidence, duplicate photographs, or contradictory reports **never** downgrade life-safety priority.

---

## 5. Instructions for Member 4 (Streamlit Dashboard)

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

# 2. Upload and input form
st.header("🚨 Submit Emergency Report")
user_text = st.text_area("Emergency Incident Message:")
uploaded_file = st.file_uploader("Upload Incident Photo (Optional):", type=["jpg", "png", "jpeg"])

if st.button("Process & Triage Report"):
    temp_image_path = None
    if uploaded_file:
        temp_image_path = f"data/images/{uploaded_file.name}"
        with open(temp_image_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

    # Load history for cross-validation
    history = load_all_historical_reports()

    # Process through pipeline
    result = process_emergency_report(
        raw_text=user_text,
        image_path=temp_image_path,
        source_id="citizen_web_user",
        source_type="registered_citizen",
        registry=st.session_state.registry,
        historical_reports=history,
        save_record=True,
        archive_image=True
    )

    # Display Triage Badge
    if result["priority"] == "CRITICAL":
        st.error(f"🚨 TRIAGE PRIORITY: {result['priority']}")
    elif result["priority"] == "HIGH":
        st.warning(f"⚠️ TRIAGE PRIORITY: {result['priority']}")
    else:
        st.info(f"ℹ️ TRIAGE PRIORITY: {result['priority']}")

    st.write(f"Confidence Score: {result['confidence']['score']}% ({result['confidence']['verification_status']})")
    st.json(result)
```

---

## 6. Instructions for Member 3 (Simulation & Rescue Optimization)

Member 3 can consume Member 2's output directly to dynamically update node weights, flood hazards, and rescue routing:

```python
from sanjeevani import load_all_historical_reports

def get_active_rescue_demands():
    reports = load_all_historical_reports()
    critical_missions = []

    for r in reports:
        # Filter for active life threats
        if r.get("priority") in ("CRITICAL", "HIGH"):
            loc = r.get("location")
            affected = (r.get("affected") or {}).get("count") or 1
            disaster = r.get("disaster_type")

            critical_missions.append({
                "report_id": r["report_id"],
                "target_node": loc,
                "disaster_type": disaster,
                "victims_count": affected,
                "priority": r["priority"],
                "confidence": r["confidence"]["score"],
                "verified": r["confidence"]["verification_status"] == "Verified"
            })

    return critical_missions
```
