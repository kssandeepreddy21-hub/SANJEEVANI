# SANJEEVANI: Member 2
## Emergency Report Analysis & Evidence Intelligence

> **Full Project:** SANJEEVANI / RESQ-AI — Human-Centric Disaster Intelligence, Infrastructure Resilience & Autonomous Emergency Response Network.  
> **Tagline:** *Predict the failure. Protect the connection. Save the response time.*  
> **Module Lead:** Member 2 (Emergency Report Analysis & Evidence Intelligence)

---

## 1. What Member 2 Does

During rapid-onset disasters (floods, fires, earthquakes, landslides, cyclones), emergency control rooms are overwhelmed by thousands of panic-driven messages, social media posts, and forwarded photographs. Emergency operators face three dangerous bottlenecks:
1. **Unstructured Data:** Messages are chaotic and lack standardized formatting.
2. **Reused & Outdated Photos:** Old photos from past disasters are forwarded, wasting critical rescue drones and boats on resolved or non-existent sites.
3. **Conflicting & Copied Reports:** Conflicting reports cause hesitation, while viral copied messages create an illusion of multiple independent confirmations.

**Member 2 solves these challenges by providing:**
* **Rule-Based NLP Entity Extraction:** Instant extraction of disaster type, designated location/zone, urgency level, and impacted population count without expensive LLM latency or API costs.
* **Dual-Layer Image Intelligence:**
  * *Exact Duplicate Detection:* SHA-256 byte-level cryptographic fingerprinting.
  * *Perceptual Similarity Analysis:* Discrete Cosine Transform (DCT) Perceptual Hashing (`pHash`) and Hamming distance measurement to flag visually identical or re-compressed photographs across reports.
* **Independent Corroboration Engine:** Explicitly distinguishes **independent textual/eyewitness accounts** from **independent photographic evidence**. Re-shared photos do not count as photographic corroboration.
* **Anonymous Source Governance:** Standardizes anonymous-source handling, categorizing unknown reporters under `unknown_independence_report_ids` to prevent viral rumor inflation.
* **Context-Aware Contradiction Detection:** Differentiates `ONGOING`, `RESOLVED`, and `NO_DISASTER` conditions to prevent false contradictions from phrases like *"The fire is extinguished and everyone is safe"*.
* **Explainable Confidence Scoring:** Transparent score (0–100%) factoring source tier, freshness, photo validity, and independent corroboration.
* **Life-Safety-First Triage Prioritization:** Ensures trapped and injured victims are dispatched with **CRITICAL priority**, separating triage urgency from documentation confidence.
* **Persistent Evidence Records:** Automatically saves structured JSON records to `data/reports/` and archives images to `data/images/`.

---

## 2. Architecture & Pipeline

```
Raw Emergency Message + Optional Incident Photo
                      │
                      ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                     sanjeevani/evidence.py                   │
 │                                                             │
 │  1. Dynamic ID Generator: Atomic sequential ID (R001, ...)  │
 │  2. Location Extractor: Zone Z2, Sector 4, Ward 12, etc.    │
 │  3. Disaster Classifier: Flood, Fire, Earthquake, etc.      │
 │  4. Urgency Classifier: High, Medium, Low, Unknown          │
 │  5. Affected Extractor: 15 people, 4 families, etc.         │
 │  6. Incident Summary: Concise incident event clause         │
 └──────────────────────────────┬──────────────────────────────┘
                                │
                      ┌─────────┴─────────┐
                      ▼                   ▼
       ┌────────────────────────┐  ┌────────────────────────┐
       │   image_analysis.py    │  │     confidence.py      │
       │                        │  │                        │
       │ • OpenCV & PIL Decoder │  │ • Temporal Freshness   │
       │ • Format & Dimensions  │  │ • Source Tier Trust    │
       │ • SHA-256 Checksum     │  │ • Textual Corroboration│
       │ • DCT Perceptual pHash │  │ • Photo Corroboration  │
       │ • Hamming Distance     │  │ • Contradiction Check  │
       │ • Image Registry Match │  │ • Scoring & Breakdown  │
       │ • Self-Match Guard     │  │ • Life-Safety Priority │
       └──────────────┬─────────┘  └───────────┬────────────┘
                      │                        │
                      └─────────┬──────────────┘
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                     sanjeevani/storage.py                    │
 │                                                             │
 │  • Persistent JSON Image Registry                           │
 │  • Atomic Non-Overwriting JSON Report Store (`data/reports/`)│
 │  • Permanent Evidence Image Archive (`data/images/`)         │
 └──────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
 Standardized Structured JSON Output (For Streamlit & Rescue Optimization)
```

---

## 3. Technologies Used

* **Python 3.10+ / 3.14** — Core programming language.
* **OpenCV (`opencv-python`)** — Matrix decoding, color channel validation, and synthetic test image generation.
* **Pillow (`PIL`)** — Image format identification, pixel buffer verification, and corrupted file handling.
* **ImageHash** — Discrete Cosine Transform perceptual hashing (`phash`) and Hamming distance computation.
* **Hashlib** — Standard library cryptographic SHA-256 generation.
* **Regular Expressions (`re`)** — Deterministic, explainable entity and pattern extraction.
* **Unittest** — Automated test suite with zero external test runners required.

---

## 4. Folder Structure

```
SANJEEVANI/
│
├── sanjeevani/
│   ├── __init__.py           <- Unified public API exports
│   ├── evidence.py           <- NLP entity extraction & main processing pipeline
│   ├── image_analysis.py     <- OpenCV, Pillow, pHash & duplicate registry
│   ├── confidence.py         <- Freshness, corroboration, contradictions & priority
│   └── storage.py            <- JSON persistence, image archiving & registry disk store
│
├── data/
│   ├── reports/              <- Saved emergency reports (JSON)
│   └── images/               <- Uploaded & archived incident photographs
│
├── tests/
│   ├── __init__.py
│   ├── test_evidence.py      <- Text extraction, urgency, affected count, dynamic IDs
│   ├── test_images.py        <- Pillow/OpenCV analysis, corrupted images, exact & visual dupes
│   ├── test_confidence.py    <- Corroboration, contradictions, freshness & life-safety priority
│   ├── test_storage.py       <- Directory handling, non-overwriting JSON store, image archiving
│   └── test_regression_member2.py <- 14 comprehensive regression tests covering all edge cases
│
├── demo_member2.py           <- Complete end-to-end multi-scenario demonstration
├── MEMBER2_INTEGRATION.md    <- Integration manual for Member 3 and Member 4
├── README_MEMBER2.md         <- Comprehensive architecture and usage guide
└── requirements.txt          <- Project dependencies
```

---

## 5. Major Python Functions Explained

### In `sanjeevani.evidence`
* **`extract_location(text)`**: Uses priority regex matching to detect official disaster zones (e.g., `Zone Z2`), administrative areas (`Sector 4`, `Ward 12`), and landmark phrases without requiring large gazetteers.
* **`detect_disaster_type(text)`**: Matches disaster vocabulary for Flood, Fire, Earthquake, Landslide, Cyclone, Building Collapse, and Tsunami. Returns `"Unknown"` if no indicators match.
* **`detect_urgency(text)`**: Scans for life-critical urgency cues (`trapped`, `drowning`, `injured`, `collapsed`) versus medium infrastructure cues (`water rising`, `road blocked`) versus low indicators (`minor waterlogging`, `normal`).
* **`extract_affected_count(text)`**: Extracts count and population unit (e.g. `{"count": 15, "unit": "people"}`).
* **`generate_report_id(prefix="R")`**: Produces non-hardcoded atomic sequential IDs (`R001`, `R002`) or timestamped IDs (`R-20261112-0001`).
* **`process_emergency_report(...)`**: Orchestrates text parsing, image inspection, duplicate detection, freshness calculation, corroboration, contradiction detection, confidence scoring, and priority calculation into a single JSON-ready output.

### In `sanjeevani.image_analysis`
* **`compute_file_sha256(file_path)`**: Computes the exact 64-character hexadecimal SHA-256 checksum in 64KB blocks to catch exact file duplicates.
* **`compute_perceptual_hash(image_input)`**: Generates an 8-byte DCT perceptual hash (`pHash`). Robust against resizing, format change, and compression.
* **`analyze_image(image_path)`**: Validates format, measures dimensions and file size, detects channels, and catches truncated or corrupted files cleanly.
* **`ImageRegistry`**: In-memory registry that calculates Hamming distance against prior submissions to flag exact or visually similar images, with built-in self-match protection (`exclude_report_id`).

### In `sanjeevani.confidence`
* **`calculate_report_freshness(report_time_str)`**: Computes elapsed age in minutes/hours. Flags reports $> 6$ hours as stale while emphasizing that old reports may still reflect ongoing emergencies. Safely handles clock skew and timezone offsets.
* **`detect_contradictions(current_report, historical_reports)`**: Accurately classifies status (`ONGOING`, `RESOLVED`, `NO_DISASTER`) to prevent false contradictions while flagging genuine conflicts for human review.
* **`check_corroboration(...)`**: Distinguishes independent textual reports from photographic corroboration, duplicate chatter, and anonymous reports.
* **`evaluate_confidence(...)`**: Transparent point-based model (0–100%) showing supporting points, penalties, and missing info without score inflation.
* **`calculate_priority(...)`**: Implements the **Life-Safety Guarantee**: trapped or injured victims automatically trigger **CRITICAL priority**, regardless of whether confidence score is high or low.

### In `sanjeevani.storage`
* **`save_report_json(report, reports_dir)`**: Writes report JSON to disk with automated timestamp collision protection to prevent accidental overwrites.
* **`load_all_historical_reports(reports_dir)`**: Reads all stored reports for automated cross-report checks.
* **`save_evidence_image(source_path, report_id, images_dir)`**: Safely archives uploaded incident photos into `data/images/`.
* **`PersistentImageRegistry`**: Auto-persists perceptual image hashes to `data/images/image_registry.json`.

---

## 6. Installation & Execution

### 1. Set Up Environment
```powershell
# Activate your virtual environment
.\.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### 2. Run the Full Unit Test Suite (37 Tests, 100% Pass Rate)
```powershell
.\.venv\Scripts\python.exe -m unittest tests/test_confidence.py tests/test_evidence.py tests/test_images.py tests/test_storage.py tests/test_regression_member2.py -v
```

### 3. Run the End-to-End Demonstration
```powershell
.\.venv\Scripts\python.exe demo_member2.py
```

### 4. Run the Interactive CLI Tool
```powershell
.\.venv\Scripts\python.exe -m sanjeevani.evidence
```

---

## 7. Limitations & Honest Engineering Boundaries

1. **Rule-Based NLP:** Location extraction relies on structured patterns (`Zone Z2`, `Sector 4`, landmarks). Free-form slang or unstructured addresses outside common patterns will be flagged as `location: None` (which is safely penalized and placed in `missing_information` rather than guessed incorrectly).
2. **Perceptual Hashing Scope:** pHash detects visually similar or recycled imagery; it **does not determine physical ground truth** (whether a photo is authentic, generated, or staged). Reused images trigger a human verification flag.
3. **No Automatic Ground Truth Dismissal:** Software never guesses which citizen is telling the truth when reports contradict each other. Conflicting statements are presented clearly to emergency dispatchers.
