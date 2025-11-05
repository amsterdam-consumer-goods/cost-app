"""
Configuration manager - Facade for storage and repository layers.
Maintains backward compatibility with existing code.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .storage import StorageManager
from .repositories import WarehouseRepository, CustomerRepository
from .utils import generate_unique_id


# ============================================================================
# Module-level storage instance (singleton pattern)
# ============================================================================
_storage: Optional[StorageManager] = None


def _get_storage() -> StorageManager:
    """Get or create storage manager instance."""
    global _storage
    if _storage is None:
        _storage = StorageManager()
    return _storage


# ============================================================================
# Public API - Load/Save
# ============================================================================

def load_catalog() -> Dict[str, Any]:
    """
    Load catalog from storage (Gist → Local fallback).
    
    Returns:
        Dict with 'warehouses' and 'customers' keys
    """
    return _get_storage().load()


def save_catalog(data: Dict[str, Any]) -> Path:
    """
    Save catalog to storage (Gist + Local).
    
    Args:
        data: Catalog dict
        
    Returns:
        Path to local file
    """
    return _get_storage().save(data)


def get_catalog_path() -> Path:
    """Get path to local catalog file."""
    return _get_storage().get_path()


def catalog_mtime() -> str:
    """Get last modification time of catalog."""
    return _get_storage().get_mtime()


def get_last_warning() -> Optional[str]:
    """Get last warning message (for UI display)."""
    return _get_storage().get_last_warning()


# ============================================================================
# Warehouse Operations
# ============================================================================

def list_warehouses(*args, **kwargs) -> List[Dict[str, Any]]:
    """
    List all warehouses.
    
    Supports multiple calling patterns for backward compatibility:
    - list_warehouses() -> uses load_catalog()
    - list_warehouses(catalog_dict)
    - list_warehouses(path=Path(...))
    """
    if len(args) >= 1:
        catalog = args[0]
        if isinstance(catalog, dict):
            return WarehouseRepository.list_all(catalog)
    
    path = kwargs.get("path")
    if path:
        import json
        with open(path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
        return WarehouseRepository.list_all(catalog)
    
    return WarehouseRepository.list_all(load_catalog())


def get_wh_by_id(*args, **kwargs) -> Optional[Dict[str, Any]]:
    """
    Get warehouse by ID.
    
    Supports:
    - get_wh_by_id(warehouse_id)
    - get_wh_by_id(catalog, warehouse_id)
    - get_wh_by_id(warehouse_id, path=Path(...))
    """
    if len(args) == 1:
        wid = str(args[0])
        catalog = load_catalog()
    elif len(args) >= 2:
        catalog = args[0]
        wid = str(args[1])
    else:
        return None
    
    path = kwargs.get("path")
    if path:
        import json
        with open(path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
    
    return WarehouseRepository.get_by_id(catalog, wid)


def get_warehouse(catalog: Dict[str, Any], wid: str) -> Dict[str, Any]:
    """Get warehouse by ID (returns empty dict if not found)."""
    result = WarehouseRepository.get_by_id(catalog, wid)
    return result if result else {}


def list_warehouse_ids(catalog: Dict[str, Any]) -> List[str]:
    """Get list of warehouse IDs."""
    return WarehouseRepository.list_ids(catalog)


def upsert_warehouse(
    catalog: Dict[str, Any],
    wid: str,
    payload: Dict[str, Any]
) -> Tuple[Dict[str, Any], bool]:
    """
    Update or insert warehouse.
    
    Returns:
        (updated_catalog, was_new)
    """
    return WarehouseRepository.upsert(catalog, wid, payload)


# ============================================================================
# Customer Operations
# ============================================================================

def list_customers(catalog: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """List all customers."""
    if catalog is None:
        catalog = load_catalog()
    return CustomerRepository.list_all(catalog)


def add_customer(
    catalog: Dict[str, Any],
    payload: Dict[str, Any]
) -> Tuple[Dict[str, Any], str]:
    """
    Add customer.
    
    Returns:
        (updated_catalog, customer_name)
    """
    return CustomerRepository.add(catalog, payload)


def gen_customer_id(name: str, catalog: Dict[str, Any]) -> str:
    """Generate unique customer ID."""
    return CustomerRepository.generate_id(name, catalog)


# ============================================================================
# ID Generation (Backward Compatibility)
# ============================================================================

def unique_id(base: str, existing: set[str]) -> str:
    """Generate unique ID from base string."""
    return generate_unique_id(base, existing)