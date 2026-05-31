import json
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "config.json"
_SCAN_DIR = _PROJECT_ROOT / "scan"
_PARTIAL_DIR = _SCAN_DIR / "partial"
_FACTS_PATH = _PROJECT_ROOT / "facts.md"


def load_config() -> dict:
    return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))


def project_root() -> Path:
    return _PROJECT_ROOT


def scan_dir() -> Path:
    return _SCAN_DIR


def partial_dir() -> Path:
    return _PARTIAL_DIR


def facts_path() -> Path:
    return _FACTS_PATH


def user_home() -> Path:
    return Path.home()
