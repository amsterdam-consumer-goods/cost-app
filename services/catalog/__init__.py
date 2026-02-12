"""
Catalog Management Module
=========================

Central module for catalog operations.

Exports:
- load_catalog: Load catalog from storage
- save_catalog: Save catalog to storage
- normalize_catalog: Normalize catalog structure
- list_warehouses: List all warehouses
- And more...

Usage:
    from services.catalog import load_catalog, normalize_catalog
"""

from .config_manager import (
    load_catalog,
    save_catalog,
    get_catalog_path,
    catalog_mtime,
    get_last_warning,
    list_warehouses,
    get_wh_by_id,
    get_warehouse,
    list_warehouse_ids,
    upsert_warehouse,
    list_customers,
    add_customer,
    gen_customer_id,
    unique_id,
)

from .catalog_adapter import normalize_catalog

__all__ = [
    # Load/Save
    "load_catalog",
    "save_catalog",
    "get_catalog_path",
    "catalog_mtime",
    "get_last_warning",
    
    # Warehouse ops
    "list_warehouses",
    "get_wh_by_id",
    "get_warehouse",
    "list_warehouse_ids",
    "upsert_warehouse",
    
    # Customer ops
    "list_customers",
    "add_customer",
    "gen_customer_id",
    
    # Utils
    "unique_id",
    "normalize_catalog",
]