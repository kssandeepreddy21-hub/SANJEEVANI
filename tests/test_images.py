"""
tests.test_images
-----------------
Unit tests for image analysis, format validation, SHA-256 hashing,
perceptual hash computation, and duplicate image detection in sanjeevani.image_analysis.
"""

import os
import shutil
import tempfile
import unittest
import numpy as np
from PIL import Image

from sanjeevani.image_analysis import (
    analyze_image,
    compute_file_sha256,
    compute_perceptual_hash,
    compute_hamming_distance,
    ImageRegistry
)


class TestImageAnalysis(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for test images
        self.test_dir = tempfile.mkdtemp()
        self.registry = ImageRegistry(similarity_threshold=10)

    def tearDown(self):
        # Clean up temporary directory
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_sample_image(self, filename: str, color=(100, 150, 200), size=(200, 200), fmt="PNG") -> str:
        """Helper to create a solid/patterned image for testing."""
        path = os.path.join(self.test_dir, filename)
        img = Image.new("RGB", size, color=color)
        img.save(path, format=fmt)
        return path

    def _create_patterned_image(self, filename: str, seed: int = 42) -> str:
        """Helper to create an image with deterministic visual features."""
        path = os.path.join(self.test_dir, filename)
        np.random.seed(seed)
        # Create a 100x100 RGB image with distinct blocks
        arr = np.zeros((100, 100, 3), dtype=np.uint8)
        arr[0:50, 0:50] = [255, 0, 0]      # Red square
        arr[50:100, 50:100] = [0, 255, 0]  # Green square
        arr[0:50, 50:100] = [0, 0, 255]    # Blue square
        img = Image.fromarray(arr)
        img.save(path, format="PNG")
        return path

    def test_01_valid_image_analysis(self):
        """Tests image metadata, dimensions, SHA-256, and perceptual hash extraction."""
        path = self._create_sample_image("sample.jpg", fmt="JPEG", size=(320, 240))
        res = analyze_image(path)

        self.assertTrue(res["image_available"])
        self.assertTrue(res["is_valid"])
        self.assertEqual(res["format"], "JPEG")
        self.assertEqual(res["dimensions"]["width"], 320)
        self.assertEqual(res["dimensions"]["height"], 240)
        self.assertEqual(res["dimensions"]["channels"], 3)
        self.assertGreater(res["file_size_bytes"], 0)
        self.assertIsNotNone(res["image_sha256"])
        self.assertIsNotNone(res["perceptual_hash"])
        self.assertIn("does NOT prove whether a photograph is genuine", res["disclaimer"])

    def test_02_missing_image(self):
        """Test Case 11: Missing image path or non-existent file."""
        # Case A: None
        res_none = analyze_image(None)
        self.assertFalse(res_none["image_available"])
        self.assertFalse(res_none["is_valid"])
        self.assertIn("No image path provided", res_none["error"])

        # Case B: Non-existent file
        res_missing = analyze_image(os.path.join(self.test_dir, "non_existent.jpg"))
        self.assertFalse(res_missing["is_valid"])
        self.assertIn("File not found", res_missing["error"])

    def test_03_corrupted_image(self):
        """Test Case 10: Corrupted or truncated image file handled gracefully."""
        corrupt_path = os.path.join(self.test_dir, "corrupt.jpg")
        # Write random non-image bytes
        with open(corrupt_path, "wb") as f:
            f.write(b"NOT_A_VALID_JPEG_HEADER_RANDOM_GARBAGE_BYTES_1234567890")

        res = analyze_image(corrupt_path)
        self.assertTrue(res["image_available"])
        self.assertFalse(res["is_valid"])
        self.assertIsNotNone(res["error"])
        self.assertIn("Corrupted or invalid image", res["error"])

    def test_04_two_identical_photographs(self):
        """Test Case 5: Two identical photographs (Exact file duplicate)."""
        img1 = self._create_patterned_image("photo_1.png")
        img2 = os.path.join(self.test_dir, "photo_2_copy.png")
        shutil.copyfile(img1, img2)

        data1 = analyze_image(img1)
        data2 = analyze_image(img2)

        # Register photo 1 in registry
        self.registry.register(
            report_id="R001",
            sha256_hash=data1["image_sha256"],
            phash_str=data1["perceptual_hash"]
        )

        # Check duplicate for photo 2
        dup = self.registry.check_duplicate(
            sha256_hash=data2["image_sha256"],
            phash_str=data2["perceptual_hash"]
        )

        self.assertTrue(dup["is_duplicate"])
        self.assertEqual(dup["duplicate_type"], "EXACT")
        self.assertEqual(dup["matched_report_id"], "R001")
        self.assertEqual(dup["hamming_distance"], 0)
        self.assertIn("Exact duplicate detected", dup["explanation"])

    def test_05_two_visually_similar_photographs(self):
        """Test Case 6: Two visually similar photographs (same scene, re-saved with slight compression)."""
        base_path = self._create_patterned_image("base_scene.png")
        data1 = analyze_image(base_path)

        # Create a visually similar variant: open, resize slightly by 1 pixel, save as JPEG quality 85
        variant_path = os.path.join(self.test_dir, "variant_scene.jpg")
        with Image.open(base_path) as im:
            # Slight resize & JPEG compression alters binary bytes completely but preserves perceptual visual structure
            im_resized = im.resize((98, 98), Image.Resampling.LANCZOS)
            im_resized.save(variant_path, format="JPEG", quality=85)

        data2 = analyze_image(variant_path)

        # Verify SHA-256 is completely different (binary distinct)
        self.assertNotEqual(data1["image_sha256"], data2["image_sha256"])

        # Register photo 1
        self.registry.register(
            report_id="R001",
            sha256_hash=data1["image_sha256"],
            phash_str=data1["perceptual_hash"]
        )

        # Compare photo 2 against registry
        dup = self.registry.check_duplicate(
            sha256_hash=data2["image_sha256"],
            phash_str=data2["perceptual_hash"]
        )

        self.assertTrue(dup["is_duplicate"])
        self.assertEqual(dup["duplicate_type"], "VISUALLY_SIMILAR")
        self.assertEqual(dup["matched_report_id"], "R001")
        self.assertLessEqual(dup["hamming_distance"], 10)
        self.assertIn("Visually similar photograph detected", dup["explanation"])
        self.assertIn("not automatically classified as fake", dup["explanation"])


if __name__ == "__main__":
    unittest.main()
