"""ID generation utilities."""

from __future__ import annotations
import re


def slugify(text: str) -> str:
    """
    Convert text to URL-safe slug.
    
    Examples:
        'My Warehouse' -> 'my_warehouse'
        'NL-SVZ 123!' -> 'nl_svz_123'
    """
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "item"


def generate_unique_id(base: str, existing_ids: set[str]) -> str:
    """
    Generate unique ID from base string.
    
    Args:
        base: Base string to slugify
        existing_ids: Set of existing IDs to avoid
        
    Returns:
        Unique slug (may have _2, _3 suffix if needed)
    """
    slug = slugify(base)
    
    if slug not in existing_ids:
        return slug
    
    # Add counter if exists
    counter = 2
    while f"{slug}_{counter}" in existing_ids:
        counter += 1
    
    return f"{slug}_{counter}"