"""
sanjeevani.image_analysis
-------------------------
Image verification and perceptual duplicate detection module for SANJEEVANI.

Technical Concepts Explained:
1. Cryptographic Hash (SHA-256):
   Produces a unique 64-character fingerprint of the file's exact binary bytes.
   If even a single byte changes, the SHA-256 changes completely.
   Used for: Exact file duplicate detection.

2. Perceptual Hash (pHash):
   Unlike SHA-256, perceptual hashing analyzes the visual frequency content of an image
   using the Discrete Cosine Transform (DCT). Visually similar images (even if resized,
   compressed, or slightly color-shifted) produce very similar hashes.
   Used for: Detecting visually similar or reused disaster photos.

3. Hamming Distance:
   The count of bit positions in which two binary hashes differ.
   - Distance = 0: Visually identical.
   - Distance <= 10: Visually very similar (likely same scene or cropped/compressed version).
   - Distance > 10: Visually distinct images.

Important Ethical Note:
Image processing extracts technical metadata and visual fingerprints.
It does NOT prove whether a photograph is genuine, staged, or outdated.
Visual similarity triggers a human verification alert; it never automatically
discards or classifies an image as fake.
"""

import os
import hashlib
from typing import Dict, Any, Optional, Tuple, List
import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError
import imagehash


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
SIMILARITY_THRESHOLD_DEFAULT = 10  # Hamming distance <= 10 flags visual similarity


def compute_file_sha256(file_path: str) -> str:
    """
    Computes the SHA-256 cryptographic hash of a file on disk.

    Args:
        file_path (str): Path to the file.

    Returns:
        str: 64-character hexadecimal SHA-256 string.
    """
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read in chunks of 64KB to handle large image files efficiently
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_perceptual_hash(image_input) -> str:
    """
    Generates a perceptual hash (pHash) using Discrete Cosine Transform.

    Args:
        image_input: Either a file path (str) or an open PIL Image object.

    Returns:
        str: Hexadecimal string representation of the perceptual hash.
    """
    if isinstance(image_input, str):
        with Image.open(image_input) as img:
            return str(imagehash.phash(img))
    return str(imagehash.phash(image_input))


def compute_hamming_distance(hash1_str: str, hash2_str: str) -> int:
    """
    Calculates the Hamming distance between two perceptual hash strings.

    Args:
        hash1_str (str): Hex string of first hash.
        hash2_str (str): Hex string of second hash.

    Returns:
        int: Number of differing bits.
    """
    h1 = imagehash.hex_to_hash(hash1_str)
    h2 = imagehash.hex_to_hash(hash2_str)
    return int(h1 - h2)


def analyze_image(image_path: Optional[str]) -> Dict[str, Any]:
    """
    Inspects an image path, validates its format, extracts dimensions,
    calculates file size, and computes both SHA-256 and perceptual hashes.

    Gracefully handles:
    - Missing image paths (None or empty).
    - Non-existent files.
    - Unsupported extensions.
    - Corrupted or truncated image data.

    Args:
        image_path (Optional[str]): Path to image file.

    Returns:
        Dict[str, Any]: Detailed technical metadata and validation result.
    """
    # Baseline result structure
    result: Dict[str, Any] = {
        "image_available": False,
        "is_valid": False,
        "image_path": image_path,
        "file_name": None,
        "file_size_bytes": 0,
        "file_size_kb": 0.0,
        "format": None,
        "dimensions": None,  # {"width": int, "height": int, "channels": int}
        "image_sha256": None,
        "perceptual_hash": None,
        "error": None,
        "disclaimer": (
            "Image analysis extracts technical metadata and visual fingerprints. "
            "It does NOT prove whether a photograph is genuine, authentic, or staged."
        )
    }

    # Case 1: No image provided
    if not image_path:
        result["error"] = "No image path provided."
        return result

    # Case 2: File does not exist on disk
    if not os.path.exists(image_path) or not os.path.isfile(image_path):
        result["error"] = f"File not found: {image_path}"
        return result

    result["image_available"] = True
    result["file_name"] = os.path.basename(image_path)

    # File size
    try:
        size_bytes = os.path.getsize(image_path)
        result["file_size_bytes"] = size_bytes
        result["file_size_kb"] = round(size_bytes / 1024.0, 2)
        if size_bytes == 0:
            result["error"] = "File is empty (0 bytes)."
            return result
    except Exception as e:
        result["error"] = f"Error reading file size: {str(e)}"
        return result

    # Validate file extension
    _, ext = os.path.splitext(image_path)
    if ext.lower() not in SUPPORTED_EXTENSIONS:
        result["error"] = f"Unsupported image extension '{ext}'. Supported: {sorted(list(SUPPORTED_EXTENSIONS))}"
        return result

    # Compute SHA-256 checksum
    try:
        sha256_hash = compute_file_sha256(image_path)
        result["image_sha256"] = sha256_hash
    except Exception as e:
        result["error"] = f"Failed to compute SHA-256 hash: {str(e)}"
        return result

    # Verify and inspect with Pillow
    try:
        with Image.open(image_path) as pil_img:
            # Force decoding of image tile data to catch corrupted files
            pil_img.load()
            img_format = pil_img.format
            width, height = pil_img.size
            phash_str = str(imagehash.phash(pil_img))

            # Channel detection via mode
            mode_to_channels = {"L": 1, "RGB": 3, "RGBA": 4, "CMYK": 4, "P": 1}
            channels = mode_to_channels.get(pil_img.mode, len(pil_img.getbands()))

            result["format"] = img_format
            result["perceptual_hash"] = phash_str
    except (UnidentifiedImageError, OSError, ValueError) as err:
        result["error"] = f"Corrupted or invalid image file: {str(err)}"
        return result
    except Exception as err:
        result["error"] = f"Unexpected error reading image: {str(err)}"
        return result

    # Double-check readability with OpenCV
    try:
        cv_img = cv2.imread(image_path)
        if cv_img is None:
            # OpenCV could not decode image
            result["error"] = "OpenCV failed to decode image pixels (possible corruption)."
            return result
        cv_height, cv_width, *cv_channels = cv_img.shape
        cv_ch = cv_channels[0] if cv_channels else 1

        result["dimensions"] = {
            "width": width,
            "height": height,
            "channels": channels,
            "cv2_shape": [int(cv_height), int(cv_width), int(cv_ch)]
        }
    except Exception as e:
        result["error"] = f"OpenCV verification warning: {str(e)}"
        return result

    # If all validations pass
    result["is_valid"] = True
    result["error"] = None
    return result


class ImageRegistry:
    """
    Registry to store image hashes and detect duplicate or visually similar images.

    Comparison Logic:
    1. Exact Duplicate: Same SHA-256 hash. The exact same digital file has been submitted before.
    2. Visually Similar: Hamming distance <= threshold. Different file or compression, but depicting
       the same visual structure. Flagged for human review.
    """

    def __init__(self, similarity_threshold: int = SIMILARITY_THRESHOLD_DEFAULT):
        self.similarity_threshold = similarity_threshold
        # Internal list of registered image records
        self._records: List[Dict[str, Any]] = []

    def register(self, report_id: str, sha256_hash: str, phash_str: str, file_name: Optional[str] = None) -> None:
        """
        Stores an image record in the registry for future comparison.
        """
        if not sha256_hash or not phash_str:
            return

        self._records.append({
            "report_id": report_id,
            "sha256": sha256_hash,
            "phash": phash_str,
            "file_name": file_name
        })

    def check_duplicate(self, sha256_hash: Optional[str], phash_str: Optional[str]) -> Dict[str, Any]:
        """
        Compares an image's hashes against all previously registered images.

        Returns:
            Dict[str, Any]:
                - is_duplicate (bool): True if exact or visually similar.
                - duplicate_type (str or None): "EXACT" | "VISUALLY_SIMILAR" | None.
                - matched_report_id (str or None): ID of matching earlier report.
                - hamming_distance (int or None): Bit distance.
                - explanation (str): Plain-English explanation.
        """
        result: Dict[str, Any] = {
            "is_duplicate": False,
            "duplicate_type": None,
            "matched_report_id": None,
            "hamming_distance": None,
            "explanation": "No duplicate or visually similar images detected in registry."
        }

        if not sha256_hash or not phash_str or not self._records:
            return result

        # Step 1: Check for EXACT binary file duplicate (SHA-256 match)
        for record in self._records:
            if record["sha256"] == sha256_hash:
                result["is_duplicate"] = True
                result["duplicate_type"] = "EXACT"
                result["matched_report_id"] = record["report_id"]
                result["hamming_distance"] = 0
                result["explanation"] = (
                    f"Exact duplicate detected: identical SHA-256 checksum as previously "
                    f"submitted report {record['report_id']}. Flagged for review."
                )
                return result

        # Step 2: Check for VISUALLY SIMILAR images via Perceptual Hash Hamming Distance
        min_distance = 999
        closest_match = None

        for record in self._records:
            try:
                dist = compute_hamming_distance(phash_str, record["phash"])
                if dist < min_distance:
                    min_distance = dist
                    closest_match = record
            except Exception:
                continue

        if closest_match is not None and min_distance <= self.similarity_threshold:
            result["is_duplicate"] = True
            result["duplicate_type"] = "VISUALLY_SIMILAR"
            result["matched_report_id"] = closest_match["report_id"]
            result["hamming_distance"] = min_distance
            result["explanation"] = (
                f"Visually similar photograph detected (Hamming distance {min_distance} <= "
                f"threshold {self.similarity_threshold}) matching report {closest_match['report_id']}. "
                f"Flagged for human verification; not automatically classified as fake."
            )
            return result

        # No match found
        result["hamming_distance"] = min_distance if min_distance != 999 else None
        return result

    def count(self) -> int:
        """Returns total registered image records."""
        return len(self._records)

    def clear(self) -> None:
        """Clears all records in memory (useful for testing)."""
        self._records.clear()
