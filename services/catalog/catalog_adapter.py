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

from .config_manager import load_catalog, list_warehouses


def normalize_catalog(catalog: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Normalize catalog structure to consistent format.
    
    Ensures catalog always has:
    - 'warehouses': List of warehouse dicts
    - 'customers': Dict or list of customer data
    
    Process:
    1. If catalog is None, load from storage
    2. Use list_warehouses for consistent warehouse list
    3. Preserve customer data structure
    4. Return normalized dict
    
    Args:
        catalog: Optional catalog dict (loads if None)
        
    Returns:
        Normalized catalog dict with consistent structure
        
    Example:
        >>> catalog = normalize_catalog()
        >>> catalog.keys()
        dict_keys(['warehouses', 'customers'])
        >>> type(catalog['warehouses'])
        <class 'list'>
    """
    # Load catalog if not provided
    if catalog is None:
        catalog = load_catalog()
    
    # Use config_manager's list_warehouses for consistent normalization
    # This handles various warehouse list formats
    warehouses = list_warehouses(catalog)
    
    # Preserve customers (dict or list format)
    customers = catalog.get("customers", {})
    
    return {
        "warehouses": warehouses,
        "customers": customers,
    }