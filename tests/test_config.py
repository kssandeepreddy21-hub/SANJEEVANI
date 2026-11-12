"""Tests for RESQ-AI environment configuration and portable data path resolution."""

from pathlib import Path
import pytest

from sanjeevani import config


def test_default_data_dir_and_paths(monkeypatch):
    monkeypatch.delenv(config.ENV_DATA_DIR, raising=False)
    monkeypatch.delenv(config.ENV_MODE, raising=False)

    assert config.get_data_dir() == config.LOCAL_DATA_DIR
    assert config.get_graph_path() == config.LOCAL_DATA_DIR / "processed" / config.GRAPH_FILENAME
    assert config.get_cache_path() == config.LOCAL_DATA_DIR / "processed" / config.CACHE_FILENAME
    assert config.get_pbf_path() == config.LOCAL_DATA_DIR / "raw" / config.PBF_FILENAME
    assert config.get_payload_path().exists()
    assert config.get_mode() == "synthetic"


def test_env_data_dir_override(monkeypatch, tmp_path):
    custom_dir = tmp_path / "external_osm"
    (custom_dir / "processed").mkdir(parents=True)
    (custom_dir / "raw").mkdir(parents=True)
    fake_cache = custom_dir / "processed" / config.CACHE_FILENAME
    fake_cache.write_bytes(b"cache")

    monkeypatch.setenv(config.ENV_DATA_DIR, str(custom_dir))

    assert config.get_data_dir() == custom_dir
    assert config.get_cache_path() == fake_cache
    assert config.osm_data_available() is True


def test_osm_data_unavailable_when_missing(monkeypatch, tmp_path):
    empty_dir = tmp_path / "empty_data"
    empty_dir.mkdir()
    monkeypatch.setenv(config.ENV_DATA_DIR, str(empty_dir))

    assert config.osm_data_available() is False


def test_mode_parsing(monkeypatch):
    monkeypatch.setenv(config.ENV_MODE, "osm")
    assert config.get_mode() == "osm"

    monkeypatch.setenv(config.ENV_MODE, "BENGALURU")
    assert config.get_mode() == "osm"

    monkeypatch.setenv(config.ENV_MODE, "synthetic")
    assert config.get_mode() == "synthetic"

    monkeypatch.setenv(config.ENV_MODE, "unknown_value")
    assert config.get_mode() == "synthetic"


def test_no_hardcoded_personal_windows_paths():
    repo_root = Path(__file__).resolve().parent.parent
    py_files = list((repo_root / "sanjeevani").glob("*.py")) + [
        repo_root / name for name in ("app.py", "data.py", "resilience.py", "main.py")
    ]
    forbidden_fragments = ("C:\\Users\\", "C:/Users/", "HIMASHRI")
    for file_path in py_files:
        text = file_path.read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            assert fragment not in text, f"Hardcoded user path '{fragment}' found in {file_path}"

