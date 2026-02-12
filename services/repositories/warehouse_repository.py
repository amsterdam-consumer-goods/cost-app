"""
Warehouse Repository
====================

Data access layer for warehouse CRUD operations.

This module provides:
- List all warehouses (sorted by name)
- Get warehouse by ID
- Create/Update warehouse (upsert)
- Delete warehouse
- Generate unique warehouse IDs
- ID slugification utilities

Repository Pattern:
- Operates on catalog dictionary
- Returns new catalog copies (immutability)
- No direct file I/O (handled by config_manager)

Related Files:
- services/config_manager.py: Catalog loading and saving
- data/catalog.json: Warehouse data storage
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Tuple


class WarehouseRepository:
    """
    Manages warehouse data operations.
    
    All methods operate on catalog dictionaries and return
    new copies to maintain immutability.
    """
    
    @staticmethod
    def list_all(catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get all warehouses from catalog, sorted by name.
        
        Sorting:
        - Primary: Warehouse name (alphabetical)
        - Secondary: Warehouse ID (alphabetical)
        
        Args:
            catalog: Catalog dictionary
            
        Returns:
            List of warehouse dictionaries, sorted
            Empty list if no warehouses or invalid format
        """
        warehouses = catalog.get("warehouses", [])
        
        if not isinstance(warehouses, list):
            return []
        
        # Filter valid warehouses (must have ID)
        items = [w for w in warehouses if isinstance(w, dict) and w.get("id")]
        
        # Sort by name, then by ID
        return sorted(
            items,
            key=lambda x: (str(x.get("name") or "").lower(), str(x.get("id") or "").lower())
        )
    
    @staticmethod
    def get_by_id(catalog: Dict[str, Any], warehouse_id: str) -> Optional[Dict[str, Any]]:
        """
        Get warehouse by ID.
        
        Args:
            catalog: Catalog dictionary
            warehouse_id: Warehouse ID to search for
            
        Returns:
            Warehouse dict if found, None otherwise
        """
        warehouses = catalog.get("warehouses", [])
        
        if not isinstance(warehouses, list):
            return None
        
        for w in warehouses:
            if isinstance(w, dict) and str(w.get("id", "")) == str(warehouse_id):
                return w
        
        return None
    
    @staticmethod
    def list_ids(catalog: Dict[str, Any]) -> List[str]:
        """
        Get list of all warehouse IDs.
        
        Args:
            catalog: Catalog dictionary
            
        Returns:
            Sorted list of warehouse ID strings
            Empty list if no warehouses
        """
        warehouses = catalog.get("warehouses", [])
        
        if not isinstance(warehouses, list):
            return []
        
        # Extract IDs from valid warehouses
        ids = [
            str(w.get("id", ""))
            for w in warehouses
            if isinstance(w, dict) and w.get("id")
        ]
        
        # Sort case-insensitive, remove duplicates
        return sorted(set(ids), key=lambda s: s.lower())
    
    @staticmethod
    def upsert(
        catalog: Dict[str, Any],
        warehouse_id: str,
        payload: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Update existing warehouse or insert new one.
        
        Process:
        1. Deep copy catalog to avoid mutations
        2. Search for existing warehouse by ID
        3. If found: Update in place
        4. If not found: Append to list
        
        Args:
            catalog: Catalog dictionary
            warehouse_id: Warehouse ID
            payload: Complete warehouse data
            
        Returns:
            Tuple of (updated_catalog, was_new)
            - updated_catalog: New catalog dict with changes
            - was_new: True if inserted, False if updated
        """
        import json
        
        # Deep copy to avoid mutating original
        updated = json.loads(json.dumps(catalog))
        warehouses = updated.get("warehouses", [])
        
        # Ensure warehouses is a list
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
        """
        Delete warehouse by ID.
        
        Args:
            catalog: Catalog dictionary
            warehouse_id: Warehouse ID to delete
            
        Returns:
            New catalog dict with warehouse removed
        """
        import json
        
        # Deep copy to avoid mutating original
        updated = json.loads(json.dumps(catalog))
        warehouses = updated.get("warehouses", [])
        
        if isinstance(warehouses, list):
            # Filter out matching warehouse
            updated["warehouses"] = [
                w for w in warehouses
                if not (isinstance(w, dict) and str(w.get("id", "")) == str(warehouse_id))
            ]
        
        return updated
    
    @staticmethod
    def generate_id(name: str, existing_ids: List[str]) -> str:
        """
        Generate unique warehouse ID from name.
        
        Process:
        1. Slugify name (lowercase, underscores)
        2. If unique, return slug
        3. If exists, append counter (_2, _3, etc.)
        
        Args:
            name: Warehouse name
            existing_ids: List of existing warehouse IDs
            
        Returns:
            Unique warehouse ID
            
        Examples:
            generate_id("NL SVZ", []) → "nl_svz"
            generate_id("NL SVZ", ["nl_svz"]) → "nl_svz_2"
            generate_id("Germany / Offergeld", []) → "germany_offergeld"
        """
        slug = WarehouseRepository._slugify(name)
        
        # If slug is unique, return it
        if slug not in existing_ids:
            return slug
        
        # Add counter if exists
        i = 2
        while f"{slug}_{i}" in existing_ids:
            i += 1
        
        return f"{slug}_{i}"
    
    @staticmethod
    def _slugify(text: str) -> str:
        """
        Convert text to slug format.
        
        Process:
        1. Lowercase
        2. Replace non-alphanumeric with underscores
        3. Collapse multiple underscores
        4. Strip leading/trailing underscores
        
        Args:
            text: Text to slugify
            
        Returns:
            Slugified string
            
        Examples:
            _slugify("NL SVZ") → "nl_svz"
            _slugify("Germany / Offergeld") → "germany_offergeld"
            _slugify("FR-Coquelle") → "fr_coquelle"
            _slugify("") → "warehouse"
        """
        text = (text or "").strip().lower()
        
        # Replace non-alphanumeric with underscores
        text = re.sub(r"[^a-z0-9]+", "_", text)
        
        # Collapse multiple underscores
        text = re.sub(r"_+", "_", text).strip("_")
        
        # Fallback if empty
        return text or "warehouse"