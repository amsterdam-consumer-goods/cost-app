"""Customer repository - handles all customer CRUD operations."""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Tuple


class CustomerRepository:
    """Manages customer data operations."""
    
    @staticmethod
    def list_all(catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get all customers from catalog."""
        customers = catalog.get("customers", [])
        if not isinstance(customers, list):
            return []
        return [c for c in customers if isinstance(c, dict)]
    
    @staticmethod
    def get_by_name(catalog: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
        """Get customer by name."""
        customers = catalog.get("customers", [])
        if not isinstance(customers, list):
            return None
        
        for c in customers:
            if isinstance(c, dict) and str(c.get("name", "")).strip().casefold() == name.strip().casefold():
                return c
        return None
    
    @staticmethod
    def add(catalog: Dict[str, Any], payload: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """
        Add a customer.
        
        Returns:
            (updated_catalog, customer_name)
        """
        import json
        
        updated = json.loads(json.dumps(catalog))
        customers = updated.get("customers", [])
        
        if not isinstance(customers, list):
            customers = []
            updated["customers"] = customers
        
        customer_name = payload.get("name", "customer")
        
        base_record = {
            "name": customer_name,
            "addresses": payload.get("addresses", []),
        }
        
        customers.append(base_record)
        return updated, customer_name
    
    @staticmethod
    def update(catalog: Dict[str, Any], old_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing customer."""
        import json
        
        updated = json.loads(json.dumps(catalog))
        customers = updated.get("customers", [])
        
        if isinstance(customers, list):
            for i, c in enumerate(customers):
                if isinstance(c, dict) and str(c.get("name", "")).strip().casefold() == old_name.strip().casefold():
                    customers[i] = payload
                    break
        
        return updated
    
    @staticmethod
    def delete(catalog: Dict[str, Any], name: str) -> Dict[str, Any]:
        """Delete customer by name."""
        import json
        
        updated = json.loads(json.dumps(catalog))
        customers = updated.get("customers", [])
        
        if isinstance(customers, list):
            updated["customers"] = [
                c for c in customers
                if not (isinstance(c, dict) and str(c.get("name", "")).strip().casefold() == name.strip().casefold())
            ]
        
        return updated
    
    @staticmethod
    def generate_id(name: str, catalog: Dict[str, Any]) -> str:
        """Generate unique customer ID from name."""
        existing = CustomerRepository._existing_names(catalog)
        slug = CustomerRepository._slugify(name)
        
        if slug not in existing:
            return slug
        
        i = 2
        while f"{slug}_{i}" in existing:
            i += 1
        return f"{slug}_{i}"
    
    @staticmethod
    def _existing_names(catalog: Dict[str, Any]) -> set[str]:
        """Get set of existing customer names."""
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
        """Convert text to slug format."""
        text = (text or "").strip().lower()
        text = re.sub(r"[^a-z0-9]+", "_", text)
        text = re.sub(r"_+", "_", text).strip("_")
        return text or "customer"