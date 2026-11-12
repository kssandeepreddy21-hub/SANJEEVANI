"""
tests.test_confidence
---------------------
Unit tests for confidence scoring, report freshness, independent corroboration,
contradiction detection, and life-safety triage prioritization in sanjeevani.confidence.
"""

from datetime import datetime, timedelta, timezone
import unittest

from sanjeevani.confidence import (
    calculate_report_freshness,
    detect_contradictions,
    check_corroboration,
    evaluate_confidence,
    calculate_priority
)
from sanjeevani.evidence import process_emergency_report


class TestConfidenceAndPriority(unittest.TestCase):

    def test_01_two_independent_reports_corroboration(self):
        """Test Case 7: Two independent reports supporting the same incident."""
        report_1 = {
            "report_id": "R101",
            "raw_text": "Severe flood water rising near Zone Z2.",
            "location": "Zone Z2",
            "disaster_type": "Flood",
            "source_id": "citizen_alice",
            "source_type": "citizen"
        }

        report_2 = {
            "report_id": "R102",
            "raw_text": "Water entered ground floor shops near Zone Z2.",
            "location": "Zone Z2",
            "disaster_type": "Flood",
            "source_id": "citizen_bob",
            "source_type": "citizen"
        }

        corroboration = check_corroboration(report_2, historical_reports=[report_1])

        self.assertTrue(corroboration["is_corroborated"])
        self.assertIn("R101", corroboration["corroborating_report_ids"])
        self.assertIn("Corroborated by 1 independent report", corroboration["explanation"])

    def test_02_same_source_not_independent_corroboration(self):
        """Tests that multiple submissions from the SAME source do not count as independent corroboration."""
        report_1 = {
            "report_id": "R101",
            "raw_text": "Flooding near Zone Z2.",
            "location": "Zone Z2",
            "disaster_type": "Flood",
            "source_id": "user_123"
        }

        report_2 = {
            "report_id": "R102",
            "raw_text": "Flooding near Zone Z2.",
            "location": "Zone Z2",
            "disaster_type": "Flood",
            "source_id": "user_123"
        }

        corroboration = check_corroboration(report_2, historical_reports=[report_1])

        self.assertFalse(corroboration["is_corroborated"])
        self.assertIn("do NOT count as independent corroboration", corroboration["explanation"])

    def test_03_contradictory_reports_detection(self):
        """Test Case 8: Contradictory reports for the same location."""
        report_a = {
            "report_id": "R201",
            "raw_text": "Severe flooding near Zone Z2. Water is rising fast.",
            "location": "Zone Z2",
            "disaster_type": "Flood"
        }

        report_b = {
            "report_id": "R202",
            "raw_text": "No flooding reported near Zone Z2. Roads are safe and all clear.",
            "location": "Zone Z2",
            "disaster_type": "Flood"
        }

        contradictions = detect_contradictions(report_b, historical_reports=[report_a])

        self.assertEqual(len(contradictions), 1)
        self.assertEqual(contradictions[0]["conflicting_report_id"], "R201")
        self.assertIn("Flagged for human verification; neither report is dismissed", contradictions[0]["explanation"])

    def test_04_old_emergency_report_freshness(self):
        """Test Case 9: Old emergency report flagged as stale while preserving active possibility."""
        ten_hours_ago = (datetime.now() - timedelta(hours=10)).isoformat(timespec="seconds")
        freshness = calculate_report_freshness(ten_hours_ago, stale_threshold_hours=6.0)

        self.assertTrue(freshness["is_stale"])
        self.assertGreaterEqual(freshness["age_hours"], 9.9)
        self.assertIn("exceeds freshness threshold", freshness["explanation"])
        self.assertIn("must NOT be assumed false", freshness["explanation"])

    def test_05_trapped_people_maintains_critical_priority_despite_low_confidence(self):
        """
        Crucial requirement: A report describing trapped people must NOT receive
        low priority just because confidence score is low.
        """
        # Anonymous unverified report without image, missing details, low confidence
        low_confidence_eval = {
            "score": 25,
            "verification_status": "Unverified",
            "supporting_evidence": ["Baseline report structure evaluated."],
            "evidence_against": ["Missing image", "Unverified source"],
            "missing_information": ["Photographic evidence"]
        }

        report = {
            "report_id": "R301",
            "raw_text": "12 people are trapped inside water near Zone Z2!",
            "location": "Zone Z2",
            "disaster_type": "Flood",
            "urgency": "High",
            "affected": {"count": 12, "unit": "people"}
        }

        priority_res = calculate_priority(report, low_confidence_eval)

        # Must be CRITICAL despite confidence score of only 25%
        self.assertEqual(priority_res["priority"], "CRITICAL")
        self.assertTrue(any("Confidence is low" in r and "CRITICAL" in r for r in priority_res["reasons"]))

    def test_06_source_reliability_impact_on_confidence(self):
        """Tests that official sources receive higher confidence than anonymous sources."""
        report_official = {
            "report_id": "R401",
            "raw_text": "Water rising near Zone Z2.",
            "location": "Zone Z2",
            "disaster_type": "Flood",
            "source_type": "official"
        }

        report_anonymous = {
            "report_id": "R402",
            "raw_text": "Water rising near Zone Z2.",
            "location": "Zone Z2",
            "disaster_type": "Flood",
            "source_type": "anonymous"
        }

        conf_official = evaluate_confidence(report_official)
        conf_anon = evaluate_confidence(report_anonymous)

        self.assertGreater(conf_official["score"], conf_anon["score"])
        self.assertTrue(any("official agency" in s for s in conf_official["supporting_evidence"]))


if __name__ == "__main__":
    unittest.main()
