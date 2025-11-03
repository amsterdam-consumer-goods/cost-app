"""
Catalog adapter: normalize old/new formats for backward compatibility.
"""

from __future__ import annotations
from typing import Any, Dict, List
from services.config_manager import load_catalog, list_warehouses

def normalize_catalog(catalog: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Normalize catalog structure to always return dict with 'warehouses' list.
    If catalog is None, loads from config_manager.
    """
    if catalog is None:
        catalog = load_catalog()
    
    # Use config_manager's list_warehouses for consistent normalization
    warehouses = list_warehouses(catalog)
    
    return {
        "warehouses": warehouses,
        "customers": catalog.get("customers", {}),
    }