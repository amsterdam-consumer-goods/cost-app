"""
Catalog Adapter
===============
Normalizes catalog structure.
"""

from __future__ import annotations
from typing import Any, Dict, Optional


def normalize_catalog(catalog: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Normalize catalog to standard format."""
    
    # Lazy import (avoid circular dependency)
    if catalog is None:
        from .config_manager import load_catalog
        catalog = load_catalog()
    
    if not isinstance(catalog, dict):
        catalog = {}
    
    catalog.setdefault("warehouses", [])
    catalog.setdefault("customers", [])
    
    # Normalize warehouses
    warehouses = catalog.get("warehouses")
    if isinstance(warehouses, dict):
        from .config_manager import list_warehouses
        catalog["warehouses"] = list_warehouses(catalog)
    elif not isinstance(warehouses, list):
        catalog["warehouses"] = []
    
    # Normalize customers
    if not isinstance(catalog.get("customers"), (list, dict)):
        catalog["customers"] = []
    
    return catalog