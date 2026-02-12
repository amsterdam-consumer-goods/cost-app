"""Customer data loading and management."""

from __future__ import annotations
from typing import List, Dict, Any, Optional
import streamlit as st


def load_customers() -> tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Load customers from catalog (NO CACHE - always fresh).
    
    Returns:
        (customer_list, catalog_path)
    """
    try:
        import sys
        import importlib
        
        # Force reload to get fresh data
        if 'services.config_manager' in sys.modules:
            importlib.reload(sys.modules['services.config_manager'])
        
        from services.catalog import list_customers, get_catalog_path
        
        customers_list = list_customers()
        
        if not customers_list:
            return [], None
        
        norm_rows: List[Dict[str, Any]] = []
        for c in customers_list:
            name = str(c.get("name", "")).strip()
            if not name:
                continue
            addrs = c.get("addresses", [])
            if not isinstance(addrs, list):
                addrs = [addrs] if addrs else []
            norm_rows.append({"name": name, "addresses": addrs})
        
        catalog_path = get_catalog_path()
        return norm_rows, str(catalog_path)
    
    except Exception as e:
        st.error(f"Error loading customers: {e}")
        import traceback
        st.code(traceback.format_exc())
        return [], None


def get_customer_names(customers: List[Dict[str, Any]]) -> List[str]:
    """Extract and sort customer names."""
    names = [str(x.get("name", "")).strip() for x in customers]
    names = [n for n in names if n and n.lower() != "nan"]
    names.sort()
    return names


def get_customer_addresses(customers: List[Dict[str, Any]], customer_name: str) -> List[str]:
    """Get addresses for specific customer."""
    for row in customers:
        if str(row.get("name", "")).strip().casefold() == customer_name.strip().casefold():
            raw = row.get("addresses", []) or []
            out, seen = [], set()
            for x in raw:
                s = str(x).strip()
                if s and s not in seen:
                    out.append(s)
                    seen.add(s)
            return out
    return []