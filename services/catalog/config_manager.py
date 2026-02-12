"""
Configuration Manager
=====================

Facade for storage and repository layers with backward compatibility.

This module provides:
- Catalog loading and saving (Gist → Local fallback)
- Warehouse CRUD operations
- Customer CRUD operations
- ID generation utilities
- Backward-compatible API for existing code

Architecture:
- Uses StorageManager for file I/O (handles Gist sync + local backup)
- Uses Repository pattern for data access
- Maintains singleton storage instance

Related Files:
- services/storage/: StorageManager implementation
- services/repositories/: Warehouse and Customer repositories
- data/catalog.json: Local catalog storage
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..storage import StorageManager
from ..repositories import WarehouseRepository, CustomerRepository
from ..utils import generate_unique_id


# ============================================================================
# SINGLETON STORAGE INSTANCE
# ============================================================================

_storage: Optional[StorageManager] = None


def _get_storage() -> StorageManager:
    """
    Get or create storage manager instance (singleton).
    
    Returns:
        StorageManager instance
    """
    global _storage
    if _storage is None:
        _storage = StorageManager()
    return _storage


# ============================================================================
# CATALOG OPERATIONS
# ============================================================================

def load_catalog() -> Dict[str, Any]:
    """
    Load catalog from storage.
    
    Loading priority:
    1. GitHub Gist (if configured)
    2. Local file (data/catalog.json)
    
    Returns:
        Dict with 'warehouses' and 'customers' keys
        
    Note:
        StorageManager handles encoding (UTF-8) automatically
    """
    return _get_storage().load()


def save_catalog(data: Dict[str, Any]) -> Path:
    """
    Save catalog to storage.
    
    Saves to:
    1. Local file (data/catalog.json)
    2. GitHub Gist (if configured)
    
    Args:
        data: Catalog dictionary
        
    Returns:
        Path to local catalog file
        
    Note:
        StorageManager handles encoding (UTF-8) automatically
    """
    return _get_storage().save(data)


def get_catalog_path() -> Path:
    """
    Get path to local catalog file.
    
    Returns:
        Path to data/catalog.json
    """
    return _get_storage().get_path()


def catalog_mtime() -> str:
    """
    Get last modification time of catalog.
    
    Returns:
        Formatted timestamp string
    """
    return _get_storage().get_mtime()


def get_last_warning() -> Optional[str]:
    """
    Get last warning message from storage operations.
    
    Useful for displaying Gist sync issues to users.
    
    Returns:
        Warning message or None
    """
    return _get_storage().get_last_warning()


# ============================================================================
# WAREHOUSE OPERATIONS
# ============================================================================

def list_warehouses(*args, **kwargs) -> List[Dict[str, Any]]:
    """
    List all warehouses.
    
    Supports multiple calling patterns for backward compatibility:
    
    Patterns:
        list_warehouses() -> Load catalog and list
        list_warehouses(catalog_dict) -> List from provided catalog
        list_warehouses(path=Path(...)) -> Load from specific file
    
    Args:
        *args: Optional catalog dict
        **kwargs: Optional path parameter
        
    Returns:
        List of warehouse dictionaries
    """
    # Pattern 1: Catalog dict provided
    if len(args) >= 1:
        catalog = args[0]
        if isinstance(catalog, dict):
            return WarehouseRepository.list_all(catalog)
    
    # Pattern 2: Path provided
    path = kwargs.get("path")
    if path:
        import json
        with open(path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
        return WarehouseRepository.list_all(catalog)
    
    # Pattern 3: Load from storage
    return WarehouseRepository.list_all(load_catalog())


def get_wh_by_id(*args, **kwargs) -> Optional[Dict[str, Any]]:
    """
    Get warehouse by ID.
    
    Patterns:
        get_wh_by_id(warehouse_id) -> Load catalog, find warehouse
        get_wh_by_id(catalog, warehouse_id) -> Find in provided catalog
        get_wh_by_id(warehouse_id, path=Path(...)) -> Load from file, find
    
    Args:
        *args: warehouse_id or (catalog, warehouse_id)
        **kwargs: Optional path parameter
        
    Returns:
        Warehouse dict or None if not found
    """
    # Determine catalog and warehouse_id
    if len(args) == 1:
        wid = str(args[0])
        catalog = load_catalog()
    elif len(args) >= 2:
        catalog = args[0]
        wid = str(args[1])
    else:
        return None
    
    # Override with path if provided
    path = kwargs.get("path")
    if path:
        import json
        with open(path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
    
    return WarehouseRepository.get_by_id(catalog, wid)


def get_warehouse(catalog: Dict[str, Any], wid: str) -> Dict[str, Any]:
    """
    Get warehouse by ID (returns empty dict if not found).
    
    Args:
        catalog: Catalog dictionary
        wid: Warehouse ID
        
    Returns:
        Warehouse dict or empty dict
    """
    result = WarehouseRepository.get_by_id(catalog, wid)
    return result if result else {}


def list_warehouse_ids(catalog: Dict[str, Any]) -> List[str]:
    """
    Get list of warehouse IDs.
    
    Args:
        catalog: Catalog dictionary
        
    Returns:
        List of warehouse ID strings
    """
    return WarehouseRepository.list_ids(catalog)


def upsert_warehouse(
    catalog: Dict[str, Any],
    wid: str,
    payload: Dict[str, Any]
) -> Tuple[Dict[str, Any], bool]:
    """
    Update existing warehouse or insert new one.
    
    Args:
        catalog: Catalog dictionary
        wid: Warehouse ID
        payload: Warehouse data
        
    Returns:
        Tuple of (updated_catalog, was_new)
        - updated_catalog: Modified catalog dict
        - was_new: True if inserted, False if updated
    """
    return WarehouseRepository.upsert(catalog, wid, payload)


# ============================================================================
# CUSTOMER OPERATIONS
# ============================================================================

def list_customers(catalog: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    List all customers.
    
    Args:
        catalog: Optional catalog dict (loads if not provided)
        
    Returns:
        List of customer dictionaries
    """
    if catalog is None:
        catalog = load_catalog()
    return CustomerRepository.list_all(catalog)


def add_customer(
    catalog: Dict[str, Any],
    payload: Dict[str, Any]
) -> Tuple[Dict[str, Any], str]:
    """
    Add new customer.
    
    Args:
        catalog: Catalog dictionary
        payload: Customer data
        
    Returns:
        Tuple of (updated_catalog, customer_name)
    """
    return CustomerRepository.add(catalog, payload)


def gen_customer_id(name: str, catalog: Dict[str, Any]) -> str:
    """
    Generate unique customer ID.
    
    Args:
        name: Customer name
        catalog: Catalog dict (to check existing IDs)
        
    Returns:
        Unique customer ID
    """
    return CustomerRepository.generate_id(name, catalog)


# ============================================================================
# ID GENERATION UTILITIES
# ============================================================================

def unique_id(base: str, existing: set[str]) -> str:
    """
    Generate unique ID from base string.
    
    Appends numbers if base already exists in set.
    
    Args:
        base: Base ID string
        existing: Set of existing IDs
        
    Returns:
        Unique ID
        
    Example:
        unique_id("warehouse", {"warehouse", "warehouse_1"})
        → "warehouse_2"
    """
    return generate_unique_id(base, existing)