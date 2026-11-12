"""
sanjeevani.storage
------------------
Persistent evidence record and report storage module for SANJEEVANI (Member 2).

Key Features:
- Automatic directory initialization (`data/reports/`, `data/images/`).
- Persistent JSON report storage with conflict/overwrite protection.
- Evidence photograph archiving.
- Persistent JSON Image Registry for duplicate detection across application restarts.
- Loading historical reports for automatic corroboration and contradiction detection.
"""

import json
import os
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional
from .image_analysis import ImageRegistry


DEFAULT_DATA_DIR = "data"
DEFAULT_REPORTS_DIR = os.path.join(DEFAULT_DATA_DIR, "reports")
DEFAULT_IMAGES_DIR = os.path.join(DEFAULT_DATA_DIR, "images")
DEFAULT_REGISTRY_PATH = os.path.join(DEFAULT_IMAGES_DIR, "image_registry.json")


def ensure_directories(
    reports_dir: str = DEFAULT_REPORTS_DIR,
    images_dir: str = DEFAULT_IMAGES_DIR
) -> Dict[str, str]:
    """
    Ensures that required storage directories exist on disk.
    Creates them automatically without crashing if missing.

    Returns:
        Dict[str, str]: Paths to the verified directories.
    """
    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    return {
        "reports_dir": reports_dir,
        "images_dir": images_dir
    }


def save_report_json(
    report: Dict[str, Any],
    reports_dir: str = DEFAULT_REPORTS_DIR,
    overwrite: bool = False
) -> str:
    """
    Saves a processed emergency report dictionary as a JSON file.

    Avoids accidental overwrites by appending a timestamp if a report
    file with the same report_id already exists.

    Args:
        report: Processed emergency report dictionary.
        reports_dir: Destination folder.
        overwrite: If True, allows overwriting existing file with same ID.

    Returns:
        str: Absolute or relative path to the saved JSON file.
    """
    ensure_directories(reports_dir=reports_dir)

    report_id = report.get("report_id", "UNKNOWN_REPORT")
    base_filename = f"{report_id}.json"
    target_path = os.path.join(reports_dir, base_filename)

    # Collision handling: if file exists and overwrite is False, add unique timestamp
    if os.path.exists(target_path) and not overwrite:
        timestamp_slug = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
        target_path = os.path.join(reports_dir, f"{report_id}_{timestamp_slug}.json")

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return target_path


def load_report_json(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Loads a single emergency report from a JSON file.
    """
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def load_all_historical_reports(
    reports_dir: str = DEFAULT_REPORTS_DIR
) -> List[Dict[str, Any]]:
    """
    Scans the reports directory and returns all previously stored reports.
    Useful for feeding into corroboration and contradiction detection.

    Returns:
        List[Dict[str, Any]]: List of historical report dictionaries.
    """
    if not os.path.exists(reports_dir):
        return []

    reports: List[Dict[str, Any]] = []
    for entry in sorted(os.listdir(reports_dir)):
        if entry.lower().endswith(".json"):
            full_path = os.path.join(reports_dir, entry)
            rep = load_report_json(full_path)
            if rep and isinstance(rep, dict) and "report_id" in rep:
                reports.append(rep)

    return reports


def save_evidence_image(
    source_image_path: str,
    report_id: str,
    images_dir: str = DEFAULT_IMAGES_DIR
) -> Optional[str]:
    """
    Copies an uploaded image into the permanent data/images storage archive,
    tagging it with the report ID to prevent filename collisions.

    Args:
        source_image_path: Path of incoming image.
        report_id: Unique ID of associated report.
        images_dir: Permanent storage folder.

    Returns:
        str: Destination path where the image was archived, or None if source missing.
    """
    if not source_image_path or not os.path.exists(source_image_path):
        return None

    ensure_directories(images_dir=images_dir)

    filename = os.path.basename(source_image_path)
    safe_filename = f"{report_id}_{filename}"
    destination_path = os.path.join(images_dir, safe_filename)

    # Avoid copying onto itself
    if os.path.abspath(source_image_path) != os.path.abspath(destination_path):
        shutil.copy2(source_image_path, destination_path)

    return destination_path


class PersistentImageRegistry(ImageRegistry):
    """
    Extends ImageRegistry to persist image hashes to disk in JSON format.
    Allows duplicate and perceptual similarity matching across restarts.
    """

    def __init__(
        self,
        registry_path: str = DEFAULT_REGISTRY_PATH,
        similarity_threshold: int = 10
    ):
        super().__init__(similarity_threshold=similarity_threshold)
        self.registry_path = registry_path
        self.load_from_disk()

    def register(
        self,
        report_id: str,
        sha256_hash: str,
        phash_str: str,
        file_name: Optional[str] = None
    ) -> None:
        """Registers the image and immediately persists to disk."""
        super().register(report_id, sha256_hash, phash_str, file_name)
        self.save_to_disk()

    def save_to_disk(self) -> None:
        """Saves registry records to JSON file."""
        try:
            folder = os.path.dirname(self.registry_path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump(self._records, f, indent=2)
        except Exception:
            pass  # Non-blocking on IO failure

    def load_from_disk(self) -> None:
        """Loads existing records from disk if available."""
        if os.path.exists(self.registry_path):
            try:
                with open(self.registry_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self._records = data
            except Exception:
                self._records = []
