"""
ID Generation Utilities
=======================

Utility functions for generating unique IDs and slugs.

This module provides:
- Text slugification (convert to URL-safe format)
- Unique ID generation with conflict resolution
- Counter-based suffix appending

Used by:
- WarehouseRepository: Generate warehouse IDs
- CustomerRepository: Generate customer IDs
- Admin forms: Validate and generate IDs

Examples:
    >>> slugify("My Warehouse")
    'my_warehouse'
    
    >>> generate_unique_id("warehouse", {"warehouse", "warehouse_2"})
    'warehouse_3'

Related Files:
- services/repositories/: Uses these utilities
- services/config_manager.py: Exposes unique_id function
"""

from __future__ import annotations
import re


def slugify(text: str) -> str:
    """
    Convert text to URL-safe slug.
    
    Process:
    1. Lowercase text
    2. Replace non-alphanumeric chars with underscores
    3. Collapse multiple underscores
    4. Strip leading/trailing underscores
    5. Return 'item' if empty
    
    Args:
        text: Text to slugify
        
    Returns:
        Slugified string
        
    Examples:
        >>> slugify("My Warehouse")
        'my_warehouse'
        
        >>> slugify("NL-SVZ 123!")
        'nl_svz_123'
        
        >>> slugify("Germany / Offergeld")
        'germany_offergeld'
        
        >>> slugify("")
        'item'
        
        >>> slugify("   Spaces   Everywhere   ")
        'spaces_everywhere'
    """
    # Normalize to lowercase
    text = (text or "").strip().lower()
    
    # Replace non-alphanumeric with underscores
    text = re.sub(r"[^a-z0-9]+", "_", text)
    
    # Collapse multiple underscores
    text = re.sub(r"_+", "_", text).strip("_")
    
    # Fallback if empty
    return text or "item"


def generate_unique_id(base: str, existing_ids: set[str]) -> str:
    """
    Generate unique ID from base string.
    
    Process:
    1. Slugify base string
    2. If unique, return slug
    3. If exists, append counter (_2, _3, etc.)
    
    Args:
        base: Base string to slugify
        existing_ids: Set of existing IDs to avoid
        
    Returns:
        Unique slug (may have _N suffix)
        
    Examples:
        >>> generate_unique_id("warehouse", set())
        'warehouse'
        
        >>> generate_unique_id("warehouse", {"warehouse"})
        'warehouse_2'
        
        >>> generate_unique_id("warehouse", {"warehouse", "warehouse_2"})
        'warehouse_3'
        
        >>> generate_unique_id("My-Warehouse!", {"my_warehouse"})
        'my_warehouse_2'
    """
    # Slugify base text
    slug = slugify(base)
    
    # If unique, return immediately
    if slug not in existing_ids:
        return slug
    
    # Add counter suffix until unique
    counter = 2
    while f"{slug}_{counter}" in existing_ids:
        counter += 1
    
    return f"{slug}_{counter}"