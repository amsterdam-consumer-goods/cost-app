"""Path utilities."""

from __future__ import annotations
from pathlib import Path


def get_project_root() -> Path:
    """
    Get project root directory.
    
    Returns:
        Path to project root (where app.py is located)
    """
    # Start from this file: services/utils/path_utils.py
    # Go up 2 levels: services/ -> project_root/
    return Path(__file__).resolve().parents[2]


def get_data_dir() -> Path:
    """Get data directory path."""
    return get_project_root() / "data"


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists, create if needed."""
    path.mkdir(parents=True, exist_ok=True)
    return path