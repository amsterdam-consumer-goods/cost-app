"""
Path Utilities
==============

Utility functions for path resolution and directory management.

This module provides:
- Project root directory detection
- Data directory access
- Directory creation helpers

Used by:
- StorageManager: Locate catalog.json
- Admin panel: File uploads and exports
- Tools: Script path resolution

Examples:
    >>> get_project_root()
    PosixPath('/path/to/cost-app')
    
    >>> get_data_dir()
    PosixPath('/path/to/cost-app/data')

Related Files:
- services/storage/: Uses path utilities
- data/: Data directory
"""

from __future__ import annotations
from pathlib import Path


def get_project_root() -> Path:
    """
    Get project root directory.
    
    Determines root by navigating up from this file's location.
    
    File structure:
        project_root/
        ├── services/
        │   └── utils/
        │       └── path_utils.py  ← This file
        ├── app.py
        └── data/
    
    Returns:
        Path to project root (where app.py is located)
        
    Example:
        >>> root = get_project_root()
        >>> (root / "app.py").exists()
        True
    """
    # Start from this file: services/utils/path_utils.py
    # Go up 2 levels: utils/ → services/ → project_root/
    return Path(__file__).resolve().parents[2]


def get_data_dir() -> Path:
    """
    Get data directory path.
    
    Returns:
        Path to data directory (project_root/data)
        
    Example:
        >>> data_dir = get_data_dir()
        >>> catalog_path = data_dir / "catalog.json"
    """
    return get_project_root() / "data"


def ensure_dir(path: Path) -> Path:
    """
    Ensure directory exists, create if needed.
    
    Creates parent directories as well if they don't exist.
    Safe to call multiple times (idempotent).
    
    Args:
        path: Directory path to ensure exists
        
    Returns:
        Same path (for chaining)
        
    Example:
        >>> output_dir = ensure_dir(Path("output/exports"))
        >>> output_dir.exists()
        True
    """
    path.mkdir(parents=True, exist_ok=True)
    return path