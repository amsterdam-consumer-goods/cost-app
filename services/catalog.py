# services/catalog.py
"""
Catalog management utilities.
- Handles reading/writing data/catalog.json safely
- Provides add, update, and get functions for warehouses
"""
from __future__ import annotations
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
CATALOG_PATH = DATA_DIR / "catalog.json"

def load() -> Dict[str, Any]:
    """Read data/catalog.json and return a dict; if missing, return a safe empty structure."""
    if not CATALOG_PATH.exists():
        return {"warehouses": []}
    try:
        with CATALOG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"warehouses": []}
        data.setdefault("warehouses", [])
        return data
    except Exception as e:
        print(f"[catalog.load] Could not read {CATALOG_PATH}: {e}")
        return {"warehouses": []}

def path() -> Path:
    """Return the absolute path to catalog.json."""
    return CATALOG_PATH

def _now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def _atomic_write_json(path: Path, data: Any) -> None:
    """Write JSON atomically (safe for concurrent access)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix="catalog_", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        shutil.move(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

def _save(obj: Dict[str, Any]) -> None:
    """Write the catalog dictionary atomically."""
    if not isinstance(obj, dict):
        raise ValueError("Catalog root must be a dict.")
    obj.setdefault("warehouses", [])
    _atomic_write_json(CATALOG_PATH, obj)

def _find_index_by_id(items: List[Dict[str, Any]], warehouse_id: str) -> int:
    """Find the index of a warehouse by ID or return -1 if not found."""
    wid = (warehouse_id or "").strip()
    for i, it in enumerate(items):
        if str(it.get("warehouse_id", "")).strip() == wid:
            return i
    return -1

def add_warehouse(draft: Dict[str, Any]) -> None:
    """Add a new warehouse. The ID must be unique."""
    wid = (draft.get("warehouse_id") or "").strip()
    if not wid:
        raise ValueError("Warehouse ID is required.")

    cat = load()
    items = cat.setdefault("warehouses", [])
    if _find_index_by_id(items, wid) != -1:
        raise ValueError("Warehouse ID must be unique.")

    new_obj = dict(draft)
    new_obj.setdefault("name", "")
    new_obj.setdefault("country", "")
    new_obj.setdefault("saved_features", {})
    new_obj.setdefault("saved_rates", {})
    new_obj.setdefault("_created_at", _now_iso())
    new_obj["_updated_at"] = new_obj["_created_at"]

    items.append(new_obj)
    _save(cat)

def get_warehouse(warehouse_id: str) -> Dict[str, Any] | None:
    """Return warehouse by ID or None if not found."""
    wid = (warehouse_id or "").strip()
    if not wid:
        return None
    cat = load()
    items = cat.get("warehouses", [])
    idx = _find_index_by_id(items, wid)
    if idx == -1:
        return None
    return items[idx]

def update_warehouse(warehouse_id: str, new_obj: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Update an existing warehouse and return (old_snapshot, new_snapshot)."""
    wid = (warehouse_id or "").strip()
    if not wid:
        raise ValueError("Warehouse ID is required.")

    cat = load()
    items = cat.setdefault("warehouses", [])
    idx = _find_index_by_id(items, wid)
    if idx == -1:
        raise ValueError(f"Warehouse '{wid}' not found.")

    old_snapshot = dict(items[idx])
    merged = dict(items[idx])
    merged.update(new_obj or {})
    merged["warehouse_id"] = wid
    merged["_updated_at"] = _now_iso()

    items[idx] = merged
    _save(cat)
    return old_snapshot, dict(merged)
