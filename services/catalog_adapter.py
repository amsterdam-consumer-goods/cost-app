# services/catalog_adapter.py
"""
Minimal identity adapter.
- normalize_catalog / normalize_wh pass data mostly unchanged
- Adds safe defaults for missing keys
"""
from __future__ import annotations
from typing import Any, Dict, List

def normalize_wh(wh: Dict[str, Any]) -> Dict[str, Any]:
    """Return a warehouse dictionary with all required keys safely set."""
    out: Dict[str, Any] = dict(wh) if isinstance(wh, dict) else {}
    out.setdefault("id", out.get("name", "warehouse"))
    out.setdefault("name", out.get("id", "Warehouse"))
    out.setdefault("country", out.get("country", ""))
    out.setdefault(
        "rates",
        out.get(
            "rates",
            {"inbound": 0.0, "outbound": 0.0, "storage": 0.0, "order_fee": 0.0},
        ),
    )
    out.setdefault("features", out.get("features", {}))
    return out

def normalize_catalog(catalog: Dict[str, Any]) -> Dict[str, Any]:
    """Return catalog with normalized warehouse records."""
    out: Dict[str, Any] = dict(catalog) if isinstance(catalog, dict) else {}
    whs: List[Dict[str, Any]] = out.get("warehouses", []) or []
    out["warehouses"] = [normalize_wh(w) for w in whs]
    return out
