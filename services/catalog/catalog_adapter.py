"""
Catalog Adapter
===============

Normalizes catalog structure for backward compatibility.

This module provides:
- Format normalization (old → new structure)
- Consistent data access patterns
- Fallback to config_manager if catalog not provided

Purpose:
Old catalog formats may have different structures. This adapter
ensures all code sees a consistent format:

{
  "warehouses": [...],
  "customers": {...}
}

Related Files:
- services/config_manager.py: Catalog loading and saving
- services/repositories/: Data access layer
"""

from __future__ import annotations
from typing import Any, Dict, Optional

from __future__ import annotations
from typing import Any, Dict, Optional


def normalize_catalog(catalog: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Normalize catalog structure to standard format.
    
    Args:
        catalog: Optional catalog dict. If None, loads from storage.
        
    Returns:
        Normalized catalog with 'warehouses' and 'customers' keys
    """
    # Lazy import to avoid circular dependency
    if catalog is None:
        from .config_manager import load_catalog
        catalog = load_catalog()
    
    # Ensure top-level keys exist
    if not isinstance(catalog, dict):
        catalog = {}
    
    catalog.setdefault("warehouses", [])
    catalog.setdefault("customers", [])
    
    # Normalize warehouses to list format
    warehouses = catalog.get("warehouses")
    
    if isinstance(warehouses, dict):
        # Convert dict format to list format
        from .config_manager import list_warehouses
        catalog["warehouses"] = list_warehouses(catalog)
    elif not isinstance(warehouses, list):
        catalog["warehouses"] = []
    
    # Normalize customers (support both list and dict formats)
    customers = catalog.get("customers")
    
    if not isinstance(customers, (list, dict)):
        catalog["customers"] = []
    
    return catalog