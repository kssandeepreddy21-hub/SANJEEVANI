"""
tests.test_storage
------------------
Unit tests for persistent report storage, image archiving, and
persistent image registry in sanjeevani.storage.
"""

import json
import os
import shutil
import tempfile
import unittest

from sanjeevani.storage import (
    ensure_directories,
    save_report_json,
    load_report_json,
    load_all_historical_reports,
    save_evidence_image,
    PersistentImageRegistry
)
from sanjeevani.evidence import process_emergency_report


class TestStorageModule(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.reports_dir = os.path.join(self.test_dir, "reports")
        self.images_dir = os.path.join(self.test_dir, "images")
        self.registry_path = os.path.join(self.images_dir, "test_registry.json")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_ensure_directories(self):
        """Tests that missing storage directories are automatically created."""
        dirs = ensure_directories(reports_dir=self.reports_dir, images_dir=self.images_dir)
        self.assertTrue(os.path.exists(self.reports_dir))
        self.assertTrue(os.path.exists(self.images_dir))
        self.assertEqual(dirs["reports_dir"], self.reports_dir)

    def test_02_save_and_load_report_json(self):
        """Tests saving and retrieving a structured emergency report JSON."""
        report = {
            "report_id": "R999",
            "disaster_type": "Flood",
            "location": "Zone Z2",
            "urgency": "High",
            "priority": "CRITICAL"
        }
        saved_path = save_report_json(report, reports_dir=self.reports_dir)
        self.assertTrue(os.path.exists(saved_path))

        loaded = load_report_json(saved_path)
        self.assertEqual(loaded["report_id"], "R999")
        self.assertEqual(loaded["priority"], "CRITICAL")

    def test_03_no_accidental_overwrite(self):
        """Tests that saving two reports with same ID does not overwrite unless specified."""
        report = {"report_id": "R001", "version": 1}
        path1 = save_report_json(report, reports_dir=self.reports_dir, overwrite=False)

        report2 = {"report_id": "R001", "version": 2}
        path2 = save_report_json(report2, reports_dir=self.reports_dir, overwrite=False)

        self.assertNotEqual(path1, path2)
        self.assertTrue(os.path.exists(path1))
        self.assertTrue(os.path.exists(path2))

    def test_04_load_all_historical_reports(self):
        """Tests loading multiple saved reports for historical checks."""
        rep1 = {"report_id": "R001", "location": "Zone A"}
        rep2 = {"report_id": "R002", "location": "Zone B"}
        save_report_json(rep1, reports_dir=self.reports_dir)
        save_report_json(rep2, reports_dir=self.reports_dir)

        all_reps = load_all_historical_reports(reports_dir=self.reports_dir)
        self.assertEqual(len(all_reps), 2)
        ids = [r["report_id"] for r in all_reps]
        self.assertIn("R001", ids)
        self.assertIn("R002", ids)

    def test_05_archive_evidence_image(self):
        """Tests copying an uploaded image into permanent evidence storage."""
        sample_img = os.path.join(self.test_dir, "sample.txt")
        with open(sample_img, "w") as f:
            f.write("mock image data")

        dest = save_evidence_image(sample_img, report_id="R101", images_dir=self.images_dir)
        self.assertTrue(os.path.exists(dest))
        self.assertIn("R101_sample.txt", dest)

    def test_06_persistent_image_registry(self):
        """Tests persistent image registry saves and loads across instances."""
        reg1 = PersistentImageRegistry(registry_path=self.registry_path)
        reg1.register(report_id="R001", sha256_hash="abc123sha", phash_str="11223344", file_name="f1.jpg")

        self.assertTrue(os.path.exists(self.registry_path))

        # Reopen with a fresh instance
        reg2 = PersistentImageRegistry(registry_path=self.registry_path)
        self.assertEqual(reg2.count(), 1)
        dup = reg2.check_duplicate(sha256_hash="abc123sha", phash_str="11223344")
        self.assertTrue(dup["is_duplicate"])
        self.assertEqual(dup["matched_report_id"], "R001")


if __name__ == "__main__":
    unittest.main()
