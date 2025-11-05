"""Warehouse repository - handles all warehouse CRUD operations."""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Tuple


class WarehouseRepository:
    """Manages warehouse data operations."""
    
    @staticmethod
    def list_all(catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get all warehouses from catalog, sorted by name."""
        warehouses = catalog.get("warehouses", [])
        if not isinstance(warehouses, list):
            return []
        
        items = [w for w in warehouses if isinstance(w, dict) and w.get("id")]
        return sorted(items, key=lambda x: (str(x.get("name") or ""), str(x.get("id") or "")))
    
    @staticmethod
    def get_by_id(catalog: Dict[str, Any], warehouse_id: str) -> Optional[Dict[str, Any]]:
        """Get warehouse by ID."""
        warehouses = catalog.get("warehouses", [])
        if not isinstance(warehouses, list):
            return None
        
        for w in warehouses:
            if isinstance(w, dict) and str(w.get("id", "")) == str(warehouse_id):
                return w
        return None
    
    @staticmethod
    def list_ids(catalog: Dict[str, Any]) -> List[str]:
        """Get list of all warehouse IDs."""
        warehouses = catalog.get("warehouses", [])
        if not isinstance(warehouses, list):
            return []
        
        ids = [str(w.get("id", "")) for w in warehouses if isinstance(w, dict) and w.get("id")]
        return sorted(set(ids), key=lambda s: s.lower())
    
    @staticmethod
    def upsert(catalog: Dict[str, Any], warehouse_id: str, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        """
        Update or insert a warehouse.
        
        Returns:
            (updated_catalog, was_new)
        """
        import json
        
        # Deep copy to avoid mutations
        updated = json.loads(json.dumps(catalog))
        warehouses = updated.get("warehouses", [])
        
        if not isinstance(warehouses, list):
            warehouses = []
            updated["warehouses"] = warehouses
        
        # Try to find and update existing
        was_new = True
        for i, w in enumerate(warehouses):
            if isinstance(w, dict) and str(w.get("id", "")) == str(warehouse_id):
                warehouses[i] = payload
                was_new = False
                break
        
        # If not found, append
        if was_new:
            if isinstance(payload, dict):
                payload["id"] = str(warehouse_id)
            warehouses.append(payload)
        
        return updated, was_new
    
    @staticmethod
    def delete(catalog: Dict[str, Any], warehouse_id: str) -> Dict[str, Any]:
        """Delete warehouse by ID."""
        import json
        
        updated = json.loads(json.dumps(catalog))
        warehouses = updated.get("warehouses", [])
        
        if isinstance(warehouses, list):
            updated["warehouses"] = [
                w for w in warehouses
                if not (isinstance(w, dict) and str(w.get("id", "")) == str(warehouse_id))
            ]
        
        return updated
    
    @staticmethod
    def generate_id(name: str, existing_ids: List[str]) -> str:
        """Generate unique warehouse ID from name."""
        slug = WarehouseRepository._slugify(name)
        
        if slug not in existing_ids:
            return slug
        
        # Add counter if exists
        i = 2
        while f"{slug}_{i}" in existing_ids:
            i += 1
        return f"{slug}_{i}"
    
    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to slug format."""
        text = (text or "").strip().lower()
        text = re.sub(r"[^a-z0-9]+", "_", text)
        text = re.sub(r"_+", "_", text).strip("_")
        return text or "warehouse"