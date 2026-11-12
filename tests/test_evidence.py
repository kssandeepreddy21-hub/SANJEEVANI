"""
tests.test_evidence
-------------------
Unit tests for text analysis, entity extraction, unique ID generation,
and complete emergency report processing in sanjeevani.evidence.
"""

import unittest
from sanjeevani.evidence import (
    extract_location,
    detect_disaster_type,
    detect_urgency,
    extract_affected_count,
    extract_incident_summary,
    generate_report_id,
    reset_report_counter,
    process_emergency_report
)


class TestEvidenceProcessing(unittest.TestCase):

    def setUp(self):
        reset_report_counter(1)

    def test_01_normal_flood_report(self):
        """Test Case 1: Normal flood report with complete information."""
        text = "Flood water is entering houses near Zone Z2. 15 people are trapped."
        report = process_emergency_report(raw_text=text)

        self.assertEqual(report["disaster_type"], "Flood")
        self.assertEqual(report["location"], "Zone Z2")
        self.assertEqual(report["urgency"], "High")
        self.assertEqual(report["affected"]["count"], 15)
        self.assertEqual(report["affected"]["unit"], "people")
        self.assertIn("Flood water is entering houses", report["incident"])
        self.assertIsNotNone(report["report_id"])
        self.assertIsNotNone(report["report_time"])
        # Priority should be CRITICAL due to trapped people
        self.assertEqual(report["priority"], "CRITICAL")

    def test_02_missing_location(self):
        """Test Case 2: Report with missing location handled without crashing."""
        text = "Water is rising rapidly and people are crying for help."
        report = process_emergency_report(raw_text=text)

        self.assertIsNone(report["location"])
        self.assertIn("Specific location / zone", report["confidence"]["missing_information"])
        # Should not crash and should record penalty
        self.assertTrue(any("Missing specific location" in item for item in report["confidence"]["evidence_against"]))

    def test_03_high_urgency_report(self):
        """Test Case 3: High urgency report with life-threatening keywords."""
        text = "Life-threatening fire with 5 people trapped on roof near Zone Z3."
        report = process_emergency_report(raw_text=text)

        self.assertEqual(report["disaster_type"], "Fire")
        self.assertEqual(report["location"], "Zone Z3")
        self.assertEqual(report["urgency"], "High")
        self.assertEqual(report["affected"]["count"], 5)
        self.assertEqual(report["priority"], "CRITICAL")

    def test_04_affected_population_extraction(self):
        """Test Case 4: Affected population count and units extraction."""
        # Case A: People
        res1 = extract_affected_count("15 people are trapped")
        self.assertEqual(res1, {"count": 15, "unit": "people"})

        # Case B: Families
        res2 = extract_affected_count("Landslide occurred; 8 families stranded near Zone A1")
        self.assertEqual(res2, {"count": 8, "unit": "families"})

        # Case C: Children
        res3 = extract_affected_count("Medical emergency: 4 children injured")
        self.assertEqual(res3, {"count": 4, "unit": "children"})

        # Case D: No numbers or affected units
        res4 = extract_affected_count("Heavy rain in the area")
        self.assertEqual(res4, {"count": None, "unit": None})

    def test_05_missing_information_graceful_handling(self):
        """Test Case 12: Missing information handled gracefully without crashing."""
        text = "Something bad is happening."
        report = process_emergency_report(raw_text=text)

        self.assertEqual(report["disaster_type"], "Unknown")
        self.assertIsNone(report["location"])
        self.assertEqual(report["urgency"], "Unknown")
        self.assertIsNone(report["affected"]["count"])
        self.assertIn("Disaster classification", report["confidence"]["missing_information"])
        self.assertIn("Specific location / zone", report["confidence"]["missing_information"])
        self.assertIn("Specific number of affected people", report["confidence"]["missing_information"])
        self.assertEqual(report["confidence"]["verification_status"], "Unverified")

    def test_06_unique_report_id_generation(self):
        """Test that report IDs are unique and avoid hardcoded values."""
        id1 = generate_report_id("R")
        id2 = generate_report_id("R")
        id3 = generate_report_id("R")
        self.assertNotEqual(id1, id2)
        self.assertNotEqual(id2, id3)
        self.assertEqual(id1, "R001")
        self.assertEqual(id2, "R002")

        # Timestamped format test
        ts_id = generate_report_id("R", use_timestamp=True)
        self.assertTrue(ts_id.startswith("R-202"))


if __name__ == "__main__":
    unittest.main()
