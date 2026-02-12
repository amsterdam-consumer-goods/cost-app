"""
Customer Repository
===================

Data access layer for customer CRUD operations.

This module provides:
- List all customers
- Get customer by name
- Create customer
- Update customer
- Delete customer
- Generate unique customer IDs

Repository Pattern:
- Operates on catalog dictionary
- Returns new catalog copies (immutability)
- No direct file I/O (handled by config_manager)

Customer Structure:
{
  "name": "Customer Name",
  "addresses": ["Address 1", "Address 2", ...]
}

Related Files:
- services/config_manager.py: Catalog loading and saving
- data/catalog.json: Customer data storage
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Tuple


class CustomerRepository:
    """
    Manages customer data operations.
    
    All methods operate on catalog dictionaries and return
    new copies to maintain immutability.
    """
    
    @staticmethod
    def list_all(catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get all customers from catalog.
        
        Args:
            catalog: Catalog dictionary
            
        Returns:
            List of customer dictionaries
            Empty list if no customers or invalid format
        """
        customers = catalog.get("customers", [])
        
        if not isinstance(customers, list):
            return []
        
        # Filter valid customers
        return [c for c in customers if isinstance(c, dict)]
    
    @staticmethod
    def get_by_name(catalog: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
        """
        Get customer by name (case-insensitive).
        
        Args:
            catalog: Catalog dictionary
            name: Customer name to search for
            
        Returns:
            Customer dict if found, None otherwise
        """
        customers = catalog.get("customers", [])
        
        if not isinstance(customers, list):
            return None
        
        # Case-insensitive name comparison
        search_name = name.strip().casefold()
        
        for c in customers:
            if isinstance(c, dict):
                customer_name = str(c.get("name", "")).strip().casefold()
                if customer_name == search_name:
                    return c
        
        return None
    
    @staticmethod
    def add(catalog: Dict[str, Any], payload: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """
        Add new customer.
        
        Args:
            catalog: Catalog dictionary
            payload: Customer data (must include 'name' and 'addresses')
            
        Returns:
            Tuple of (updated_catalog, customer_name)
        """
        import json
        
        # Deep copy to avoid mutating original
        updated = json.loads(json.dumps(catalog))
        customers = updated.get("customers", [])
        
        # Ensure customers is a list
        if not isinstance(customers, list):
            customers = []
            updated["customers"] = customers
        
        customer_name = payload.get("name", "customer")
        
        # Create customer record
        base_record = {
            "name": customer_name,
            "addresses": payload.get("addresses", []),
        }
        
        customers.append(base_record)
        
        return updated, customer_name
    
    @staticmethod
    def update(catalog: Dict[str, Any], old_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update existing customer.
        
        Finds customer by old_name (case-insensitive) and replaces with payload.
        
        Args:
            catalog: Catalog dictionary
            old_name: Current customer name
            payload: New customer data
            
        Returns:
            Updated catalog dictionary
        """
        import json
        
        # Deep copy to avoid mutating original
        updated = json.loads(json.dumps(catalog))
        customers = updated.get("customers", [])
        
        if isinstance(customers, list):
            # Case-insensitive search
            search_name = old_name.strip().casefold()
            
            for i, c in enumerate(customers):
                if isinstance(c, dict):
                    customer_name = str(c.get("name", "")).strip().casefold()
                    if customer_name == search_name:
                        customers[i] = payload
                        break
        
        return updated
    
    @staticmethod
    def delete(catalog: Dict[str, Any], name: str) -> Dict[str, Any]:
        """
        Delete customer by name (case-insensitive).
        
        Args:
            catalog: Catalog dictionary
            name: Customer name to delete
            
        Returns:
            New catalog dict with customer removed
        """
        import json
        
        # Deep copy to avoid mutating original
        updated = json.loads(json.dumps(catalog))
        customers = updated.get("customers", [])
        
        if isinstance(customers, list):
            # Case-insensitive filter
            search_name = name.strip().casefold()
            
            updated["customers"] = [
                c for c in customers
                if not (
                    isinstance(c, dict)
                    and str(c.get("name", "")).strip().casefold() == search_name
                )
            ]
        
        return updated
    
    @staticmethod
    def generate_id(name: str, catalog: Dict[str, Any]) -> str:
        """
        Generate unique customer ID from name.
        
        Process:
        1. Get existing customer names
        2. Slugify name
        3. If unique, return slug
        4. If exists, append counter (_2, _3, etc.)
        
        Args:
            name: Customer name
            catalog: Catalog dict (to check existing names)
            
        Returns:
            Unique customer ID
            
        Examples:
            generate_id("Acme Corp", {}) → "acme_corp"
            generate_id("Acme Corp", {"customers": [{"name": "Acme Corp"}]}) → "acme_corp_2"
        """
        existing = CustomerRepository._existing_names(catalog)
        slug = CustomerRepository._slugify(name)
        
        # If slug is unique, return it
        if slug not in existing:
            return slug
        
        # Add counter if exists
        i = 2
        while f"{slug}_{i}" in existing:
            i += 1
        
        return f"{slug}_{i}"
    
    @staticmethod
    def _existing_names(catalog: Dict[str, Any]) -> set[str]:
        """
        Get set of existing customer names.
        
        Args:
            catalog: Catalog dictionary
            
        Returns:
            Set of customer name strings
        """
        customers = catalog.get("customers", [])
        
        if not isinstance(customers, list):
            return set()
        
        names = set()
        for c in customers:
            if isinstance(c, dict):
                name = c.get("name", "")
                if name:
                    names.add(str(name))
        
        return names
    
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
            _slugify("Acme Corp") → "acme_corp"
            _slugify("ABC-XYZ Ltd.") → "abc_xyz_ltd"
            _slugify("") → "customer"
        """
        text = (text or "").strip().lower()
        
        # Replace non-alphanumeric with underscores
        text = re.sub(r"[^a-z0-9]+", "_", text)
        
        # Collapse multiple underscores
        text = re.sub(r"_+", "_", text).strip("_")
        
        # Fallback if empty
        return text or "customer"