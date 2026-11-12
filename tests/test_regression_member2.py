"""
tests.test_regression_member2
-----------------------------
Comprehensive regression test suite for RESQ-AI / SANJEEVANI (Member 2).
Covers all 14 required regression test scenarios specified in the Member 2
Code Correction and Improvement specification.
"""

from datetime import datetime, timedelta, timezone
import json
import os
import shutil
import tempfile
import unittest
import numpy as np
from PIL import Image

from sanjeevani.evidence import (
    process_emergency_report,
    reset_report_counter,
    extract_location,
    detect_disaster_type,
    detect_urgency
)
from sanjeevani.image_analysis import (
    analyze_image,
    ImageRegistry,
    compute_file_sha256,
    compute_perceptual_hash
)
from sanjeevani.confidence import (
    check_corroboration,
    detect_contradictions,
    evaluate_confidence,
    calculate_priority,
    calculate_report_freshness,
    is_anonymous_source
)
from sanjeevani.storage import PersistentImageRegistry


class TestMember2RegressionSuite(unittest.TestCase):

    def setUp(self):
        reset_report_counter(1)
        self.test_dir = tempfile.mkdtemp()
        self.registry = ImageRegistry(similarity_threshold=10)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_patterned_image(self, filename: str, seed: int = 42) -> str:
        """Helper to create a deterministic patterned image."""
        path = os.path.join(self.test_dir, filename)
        np.random.seed(seed)
        arr = np.zeros((100, 100, 3), dtype=np.uint8)
        arr[0:50, 0:50] = [255, 0, 0]
        arr[50:100, 50:100] = [0, 255, 0]
        arr[0:50, 50:100] = [0, 0, 255]
        img = Image.fromarray(arr)
        img.save(path, format="PNG")
        return path

    def _create_distinct_image(self, filename: str) -> str:
        """Helper to create a completely visually distinct image."""
        path = os.path.join(self.test_dir, filename)
        arr = np.full((100, 100, 3), 180, dtype=np.uint8)
        arr[20:80, 20:80] = [255, 255, 0]  # Yellow center
        img = Image.fromarray(arr)
        img.save(path, format="PNG")
        return path

    # TEST 1: EXACT DUPLICATE IMAGE
    def test_01_exact_duplicate_image(self):
        """
        Test 1: Exact duplicate image (same SHA-256).
        Expected: Duplicate detected, R002 not counted as independent photographic
        evidence, and human review flag present.
        """
        img1 = self._create_patterned_image("img1.png")
        img2 = os.path.join(self.test_dir, "img2_copy.png")
        shutil.copyfile(img1, img2)

        rep1 = process_emergency_report(
            raw_text="Flood water rising near Zone Z2.",
            image_path=img1,
            source_id="officer_alpha",
            source_type="first_responder",
            registry=self.registry
        )

        rep2 = process_emergency_report(
            raw_text="Water entering ground floors near Zone Z2.",
            image_path=img2,
            source_id="officer_beta",
            source_type="first_responder",
            registry=self.registry,
            historical_reports=[rep1]
        )

        # 1. Exact duplicate detected
        ev2 = rep2["evidence"]
        self.assertTrue(ev2["possible_duplicate"])
        self.assertEqual(ev2["duplicate_type"], "EXACT")
        self.assertEqual(ev2["matched_report_id"], rep1["report_id"])

        # 2. R001 must NOT be counted as independent photographic corroboration for R002
        corr2 = rep2["corroboration"]
        self.assertIn(rep1["report_id"], corr2["duplicate_image_report_ids"])
        self.assertNotIn(rep1["report_id"], corr2["independent_image_reports"])

        # 3. Textual corroboration remains valid because sources are independent
        self.assertIn(rep1["report_id"], corr2["independent_textual_reports"])

        # 4. Human review flag present
        self.assertEqual(rep2["confidence"]["verification_status"], "Flagged for Review (Duplicate Image)")

    # TEST 2: VISUALLY SIMILAR IMAGE
    def test_02_visually_similar_image(self):
        """
        Test 2: Visually similar image (different SHA-256 but pHash distance <= 10).
        Expected: Visually similar flag, no independent photographic corroboration,
        no automatic fake classification.
        """
        base_path = self._create_patterned_image("base.png")
        similar_path = os.path.join(self.test_dir, "similar.jpg")

        # Create visually similar JPEG with slight resize and quality compression
        with Image.open(base_path) as im:
            im_resized = im.resize((98, 98), Image.Resampling.LANCZOS)
            im_resized.save(similar_path, format="JPEG", quality=85)

        # Verify SHA-256 is different (binary distinct files)
        self.assertNotEqual(compute_file_sha256(base_path), compute_file_sha256(similar_path))

        rep1 = process_emergency_report(
            raw_text="Flooding in Sector 4.",
            image_path=base_path,
            source_id="user_alice",
            source_type="registered_citizen",
            registry=self.registry
        )

        rep2 = process_emergency_report(
            raw_text="Severe waterlogging in Sector 4.",
            image_path=similar_path,
            source_id="user_bob",
            source_type="registered_citizen",
            registry=self.registry,
            historical_reports=[rep1]
        )

        ev2 = rep2["evidence"]
        self.assertTrue(ev2["possible_duplicate"])
        self.assertEqual(ev2["duplicate_type"], "VISUALLY_SIMILAR")
        self.assertLessEqual(ev2["similarity_distance"], 10)

        # Must not be treated as independent photographic corroboration
        corr2 = rep2["corroboration"]
        self.assertIn(rep1["report_id"], corr2["visually_similar_report_ids"])
        self.assertNotIn(rep1["report_id"], corr2["independent_image_reports"])

        # Must not be classified as fake; should be flagged for review
        self.assertIn("not automatically classified as fake", ev2["duplicate_explanation"])
        self.assertEqual(rep2["confidence"]["verification_status"], "Flagged for Review (Visually Similar Image)")

    # TEST 3: DIFFERENT SOURCES AND DIFFERENT IMAGES
    def test_03_different_sources_and_different_images(self):
        """
        Test 3: Different sources and genuinely distinct images.
        Expected: Eligible for independent textual corroboration AND independent
        photographic corroboration.
        """
        img1 = self._create_patterned_image("flood1.png", seed=10)
        img2 = self._create_distinct_image("flood2.png")

        rep1 = process_emergency_report(
            raw_text="Flooding near Zone Z2 with water rising.",
            image_path=img1,
            source_id="citizen_1",
            source_type="registered_citizen",
            registry=self.registry
        )

        rep2 = process_emergency_report(
            raw_text="Water entering residential compounds near Zone Z2.",
            image_path=img2,
            source_id="citizen_2",
            source_type="registered_citizen",
            registry=self.registry,
            historical_reports=[rep1]
        )

        corr2 = rep2["corroboration"]
        self.assertTrue(corr2["is_corroborated"])
        self.assertIn(rep1["report_id"], corr2["independent_textual_reports"])
        self.assertIn(rep1["report_id"], corr2["independent_image_reports"])
        self.assertEqual(len(corr2["duplicate_image_report_ids"]), 0)

    # TEST 4: SAME SOURCE (DUPLICATE CHATTER)
    def test_04_same_source_not_independent(self):
        """
        Test 4: Multiple submissions from the same identified source.
        Expected: No independent corroboration (recorded as duplicate chatter).
        """
        rep1 = {
            "report_id": "R101",
            "raw_text": "Flooding near Zone Z2.",
            "location": "Zone Z2",
            "disaster_type": "Flood",
            "source_id": "operator_404",
            "source_type": "first_responder"
        }

        rep2 = {
            "report_id": "R102",
            "raw_text": "Flooding near Zone Z2 still continuing.",
            "location": "Zone Z2",
            "disaster_type": "Flood",
            "source_id": "operator_404",
            "source_type": "first_responder"
        }

        corr = check_corroboration(rep2, historical_reports=[rep1])
        self.assertFalse(corr["is_corroborated"])
        self.assertIn("R101", corr["duplicate_chatter_ids"])
        self.assertEqual(len(corr["independent_textual_reports"]), 0)

    # TEST 5: IDENTICAL COPIED MESSAGE
    def test_05_identical_copied_message(self):
        """
        Test 5: Verbatim copied message across different sources.
        Expected: Treated as viral/duplicate chatter; no independent textual corroboration.
        """
        copied_text = "Urgent: Water levels have crossed danger mark near Zone Z5!"
        rep1 = {
            "report_id": "R201",
            "raw_text": copied_text,
            "location": "Zone Z5",
            "disaster_type": "Flood",
            "source_id": "user_a",
            "source_type": "citizen"
        }

        rep2 = {
            "report_id": "R202",
            "raw_text": copied_text,
            "location": "Zone Z5",
            "disaster_type": "Flood",
            "source_id": "user_b",
            "source_type": "citizen"
        }

        corr = check_corroboration(rep2, historical_reports=[rep1])
        self.assertFalse(corr["is_corroborated"])
        self.assertIn("R201", corr["duplicate_chatter_ids"])
        self.assertEqual(len(corr["independent_textual_reports"]), 0)

    # TEST 6: ANONYMOUS SOURCES
    def test_06_anonymous_sources_independence_unknown(self):
        """
        Test 6: Multiple anonymous reports for the same incident.
        Expected: Independence remains unknown; no automatic independent corroboration.
        """
        rep1 = {
            "report_id": "R301",
            "raw_text": "Flooding reported near Zone Z2.",
            "location": "Zone Z2",
            "disaster_type": "Flood",
            "source_id": "anonymous_citizen",
            "source_type": "citizen"
        }

        rep2 = {
            "report_id": "R302",
            "raw_text": "Water is high near Zone Z2.",
            "location": "Zone Z2",
            "disaster_type": "Flood",
            "source_id": "anonymous",
            "source_type": "citizen"
        }

        corr = check_corroboration(rep2, historical_reports=[rep1])
        self.assertFalse(corr["is_corroborated"])
        self.assertIn("R301", corr["unknown_independence_report_ids"])
        self.assertEqual(len(corr["independent_textual_reports"]), 0)
        self.assertIn("source independence is unknown", corr["explanation"])

    # TEST 7: DUPLICATE IMAGE WITH TRAPPED PEOPLE
    def test_07_duplicate_image_with_trapped_people_maintains_critical_priority(self):
        """
        Test 7: Duplicate image attached to a report describing trapped people.
        Expected: Duplicate detected, confidence penalized, but priority remains strictly CRITICAL.
        """
        img1 = self._create_patterned_image("flood_base.png")

        rep1 = process_emergency_report(
            raw_text="Flooding near Zone Z2.",
            image_path=img1,
            source_id="citizen_one",
            registry=self.registry
        )

        rep2 = process_emergency_report(
            raw_text="15 people are trapped in rising floodwaters near Zone Z2!",
            image_path=img1,  # Reused photo
            source_id="citizen_two",
            registry=self.registry,
            historical_reports=[rep1]
        )

        # Duplicate must be detected
        self.assertTrue(rep2["evidence"]["possible_duplicate"])
        # Priority must remain CRITICAL to protect human lives
        self.assertEqual(rep2["priority"], "CRITICAL")
        self.assertTrue(any("Immediate life safety hazard" in r for r in rep2["priority_reasons"]))

    # TEST 8: LOW-CONFIDENCE INJURED-PERSON REPORT
    def test_08_low_confidence_injured_person_critical_priority(self):
        """
        Test 8: Low confidence report with injured people (anonymous, no photo, missing location/type).
        Expected: Score is low (< 40%), but priority remains strictly CRITICAL.
        """
        rep = process_emergency_report(
            raw_text="3 children injured, urgent medical help needed!",
            image_path=None,
            source_id="anonymous",
            source_type="anonymous"
        )

        self.assertLess(rep["confidence"]["score"], 40)
        self.assertEqual(rep["priority"], "CRITICAL")
        self.assertTrue(any("Confidence is low" in r and "CRITICAL" in r for r in rep["priority_reasons"]))

    # TEST 9: CONTRADICTORY REPORTS
    def test_09_contradictory_reports_detection(self):
        """
        Test 9: Contradictory reports for the same location.
        Expected: Conflict detected, flagged for human review, neither report rejected.
        """
        rep1 = {
            "report_id": "R501",
            "raw_text": "Severe flood water rising near Zone Z2.",
            "location": "Zone Z2",
            "disaster_type": "Flood"
        }

        rep2 = {
            "report_id": "R502",
            "raw_text": "No flooding near Zone Z2. Roads are completely clear and safe.",
            "location": "Zone Z2",
            "disaster_type": "Flood"
        }

        contradictions = detect_contradictions(rep2, historical_reports=[rep1])
        self.assertEqual(len(contradictions), 1)
        self.assertEqual(contradictions[0]["conflicting_report_id"], "R501")
        self.assertEqual(contradictions[0]["conflict_type"], "Direct Status Contradiction")
        self.assertIn("neither report is dismissed", contradictions[0]["explanation"])

    # TEST 10: OLD REPORT FRESHNESS
    def test_10_old_report_freshness(self):
        """
        Test 10: Old report (e.g. 12 hours old).
        Expected: Stale flag is True, report remains available, active possibility preserved.
        """
        past_time = (datetime.now() - timedelta(hours=12)).isoformat()
        freshness = calculate_report_freshness(past_time, stale_threshold_hours=6.0)

        self.assertTrue(freshness["is_stale"])
        self.assertGreaterEqual(freshness["age_hours"], 11.9)
        self.assertIn("must NOT be assumed false", freshness["explanation"])

    # TEST 11: MISSING IMAGE HANDLING
    def test_11_missing_image_graceful_processing(self):
        """
        Test 11: Missing or None image.
        Expected: Pipeline runs normally without crashing.
        """
        rep = process_emergency_report(
            raw_text="Heavy rain near Ward 12.",
            image_path=None
        )

        self.assertFalse(rep["evidence"]["image_available"])
        self.assertFalse(rep["evidence"]["image_valid"])
        self.assertIn("Photographic evidence", rep["confidence"]["missing_information"])
        self.assertIsNotNone(rep["report_id"])

    # TEST 12: MISSING SOURCE ID
    def test_12_missing_source_id_safe_handling(self):
        """
        Test 12: Missing source ID.
        Expected: Safe handling, default to anonymous, independence not assumed.
        """
        rep = process_emergency_report(
            raw_text="Water entering houses near Zone Z1.",
            source_id=None
        )

        self.assertEqual(rep["source_id"], "anonymous_citizen")
        self.assertTrue(is_anonymous_source(rep["source_id"]))

    # TEST 13: MULTIPLE HISTORICAL REPORTS (NO DUPLICATE COUNTING)
    def test_13_multiple_historical_reports_no_duplicate_counting(self):
        """
        Test 13: Multiple historical reports at same location.
        Expected: Correct matching report IDs, no duplicate counting or score inflation.
        """
        history = [
            {
                "report_id": "R701",
                "location": "Zone Z2",
                "disaster_type": "Flood",
                "source_id": "officer_1",
                "source_type": "first_responder",
                "raw_text": "Flooding reported at Zone Z2."
            },
            {
                "report_id": "R702",
                "location": "Zone Z2",
                "disaster_type": "Flood",
                "source_id": "officer_2",
                "source_type": "first_responder",
                "raw_text": "Road submerged near Zone Z2."
            }
        ]

        rep = process_emergency_report(
            raw_text="Water level rising rapidly near Zone Z2.",
            source_id="officer_3",
            source_type="first_responder",
            historical_reports=history
        )

        corr = rep["corroboration"]
        self.assertEqual(len(corr["independent_textual_reports"]), 2)
        self.assertIn("R701", corr["independent_textual_reports"])
        self.assertIn("R702", corr["independent_textual_reports"])

        # Confidence bonus must be capped (+15), not duplicated per report
        text_bonuses = [s for s in rep["confidence"]["supporting_evidence"] if "Independent corroboration" in s]
        self.assertEqual(len(text_bonuses), 1)

    # TEST 14: REGISTRY SELF-MATCH PREVENTION
    def test_14_registry_self_match_prevention(self):
        """
        Test 14: Registry must not match a report against itself.
        Expected: Re-evaluating or checking the same report ID does not produce self-duplicate.
        """
        img_path = self._create_patterned_image("self_test.png")
        data = analyze_image(img_path)

        reg = ImageRegistry(similarity_threshold=10)
        reg.register(
            report_id="R801",
            sha256_hash=data["image_sha256"],
            phash_str=data["perceptual_hash"]
        )

        # Checking duplicate while excluding self
        check_self = reg.check_duplicate(
            sha256_hash=data["image_sha256"],
            phash_str=data["perceptual_hash"],
            exclude_report_id="R801"
        )
        self.assertFalse(check_self["is_duplicate"])
        self.assertIsNone(check_self["matched_report_id"])

        # Another report checking the same image must correctly match R801
        check_other = reg.check_duplicate(
            sha256_hash=data["image_sha256"],
            phash_str=data["perceptual_hash"],
            exclude_report_id="R802"
        )
        self.assertTrue(check_other["is_duplicate"])
        self.assertEqual(check_other["matched_report_id"], "R801")


if __name__ == "__main__":
    unittest.main()
