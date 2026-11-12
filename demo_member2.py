"""
demo_member2.py
----------------
SANJEEVANI Member 2: Emergency Report Analysis & Evidence Intelligence
End-to-End Demonstration Script

DISCLAIMER:
All demonstration data, coordinates, incidents, and messages below are
SYNTHETIC SIMULATIONS generated solely for evaluating the SANJEEVANI
disaster intelligence prototype. They do NOT represent real-world emergencies.
"""

import json
import os
import shutil
import tempfile
import cv2
import numpy as np
from PIL import Image

from sanjeevani import (
    process_emergency_report,
    PersistentImageRegistry,
    load_all_historical_reports,
    ensure_directories,
    reset_report_counter
)


def create_synthetic_demo_image(filepath: str, color=(0, 100, 255), label: str = "WATER") -> str:
    """Helper to generate a synthetic test image."""
    img = np.zeros((240, 320, 3), dtype=np.uint8)
    img[:] = color
    cv2.putText(
        img,
        f"SYNTHETIC DEMO: {label}",
        (15, 120),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2
    )
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    cv2.imwrite(filepath, img)
    return filepath


def run_demonstration():
    print("=" * 75)
    print("    SANJEEVANI: EMERGENCY REPORT ANALYSIS & EVIDENCE INTELLIGENCE")
    print("                MEMBER 2 - END-TO-END DEMONSTRATION")
    print("=" * 75)
    print("Notice: All reports in this demonstration are SYNTHETIC SIMULATIONS.\n")

    reset_report_counter(1)

    # Step 0: Ensure directories
    dirs = ensure_directories()
    reports_dir = dirs["reports_dir"]
    images_dir = dirs["images_dir"]

    # Step 0b: Initialize persistent registry (fresh instance for demo run)
    registry_file = os.path.join(images_dir, "demo_image_registry.json")
    if os.path.exists(registry_file):
        os.remove(registry_file)
    registry = PersistentImageRegistry(registry_path=registry_file, similarity_threshold=10)

    # Clean previous demo image if exists
    demo_img_1 = os.path.join(images_dir, "synthetic_flood_evidence.jpg")
    create_synthetic_demo_image(demo_img_1, color=(180, 80, 20), label="FLOOD ZONE Z2")

    # Synthetic Scenarios
    synthetic_cases = [
        {
            "title": "SCENARIO 1: CRITICAL FLOOD REPORT WITH TRAPPED POPULATION & EVIDENCE PHOTO",
            "text": "Flood water is entering houses near Zone Z2. 15 people are trapped.",
            "source_id": "citizen_alice_01",
            "source_type": "citizen",
            "image": demo_img_1
        },
        {
            "title": "SCENARIO 2: REUSED/DUPLICATE IMAGE SUBMITTED FOR A DIFFERENT INCIDENT",
            "text": "Severe flooding reported near Zone Z2. Water levels rising rapidly.",
            "source_id": "citizen_bob_02",
            "source_type": "citizen",
            "image": demo_img_1  # Re-submitting the exact same photo to trigger duplicate detection!
        },
        {
            "title": "SCENARIO 3: CONTRADICTORY STATUS REPORT FOR SAME LOCATION",
            "text": "No flooding reported near Zone Z2. Roads are completely clear and safe.",
            "source_id": "citizen_charlie_03",
            "source_type": "citizen",
            "image": None
        },
        {
            "title": "SCENARIO 4: MEDIUM URGENCY INFRASTRUCTURE HAZARD",
            "text": "Heavy rainfall and road blockage near Zone Z3.",
            "source_id": "traffic_officer_44",
            "source_type": "first_responder",
            "image": None
        },
        {
            "title": "SCENARIO 5: FIRE INCIDENT REQUIRING RESCUE",
            "text": "Fire reported near Sector A. Several residents need assistance. 6 children injured.",
            "source_id": "sector_watch_09",
            "source_type": "registered_citizen",
            "image": None
        }
    ]

    in_memory_history = []

    for idx, case in enumerate(synthetic_cases, 1):
        print("\n" + "-" * 75)
        print(f"[{idx}] {case['title']}")
        print("-" * 75)
        print(f"Input Message : \"{case['text']}\"")
        print(f"Source ID     : {case['source_id']} ({case['source_type']})")
        print(f"Attached Image: {case['image'] or 'None'}")

        # Process report with full pipeline
        report = process_emergency_report(
            raw_text=case["text"],
            image_path=case["image"],
            source_id=case["source_id"],
            source_type=case["source_type"],
            registry=registry,
            historical_reports=in_memory_history,
            save_record=True,
            archive_image=True
        )

        in_memory_history.append(report)

        print("\n--- EXTRACTED DISASTER INTELLIGENCE ---")
        print(f"  • Report ID      : {report['report_id']}")
        print(f"  • Timestamp      : {report['report_time']}")
        print(f"  • Disaster Type  : {report['disaster_type']}")
        print(f"  • Location       : {report['location']}")
        print(f"  • Incident       : {report['incident']}")
        print(f"  • Urgency        : {report['urgency']}")
        print(f"  • Affected Count : {report['affected']['count']} {report['affected'].get('unit') or ''}")

        print("\n--- EVIDENCE & IMAGE INTELLIGENCE ---")
        ev = report["evidence"]
        print(f"  • Image Available: {ev['image_available']}")
        if ev["image_available"]:
            print(f"  • Valid Format   : {ev['image_valid']} ({ev['format']})")
            print(f"  • Dimensions     : {ev['dimensions']['width']}x{ev['dimensions']['height']}")
            print(f"  • SHA-256 Hash   : {ev['image_sha256'][:24]}...")
            print(f"  • Perceptual pHash: {ev['perceptual_hash']}")
            print(f"  • Duplicate Flag : {ev['possible_duplicate']} (Type: {ev['duplicate_type']})")
            if ev["possible_duplicate"]:
                print(f"  • Alert Details  : {ev['duplicate_explanation']}")

        print("\n--- CORROBORATION & CONTRADICTIONS ---")
        corr = report["corroboration"]
        print(f"  • Corroborated   : {corr['is_corroborated']} - {corr['explanation']}")
        contra = report["contradictions"]
        print(f"  • Contradictions : {len(contra)} detected")
        for c in contra:
            print(f"    [!] CONFLICT: {c['explanation']}")

        print("\n--- CONFIDENCE & TRIAGE PRIORITIZATION ---")
        conf = report["confidence"]
        print(f"  • Confidence Score: {conf['score']}%")
        print(f"  • Status          : {conf['verification_status']}")
        print(f"  • TRIAGE PRIORITY : >>> {report['priority']} <<<")
        print(f"  • Priority Reasons:")
        for r in report["priority_reasons"]:
            print(f"      - {r}")

        print(f"\n  • Saved to Disk   : {report['storage']['saved_json_path']}")

    print("\n" + "=" * 75)
    print("DEMONSTRATION COMPLETED SUCCESSFULLY.")
    print("All synthetic reports analyzed, cross-checked, scored, and stored.")
    print("=" * 75)


if __name__ == "__main__":
    run_demonstration()
