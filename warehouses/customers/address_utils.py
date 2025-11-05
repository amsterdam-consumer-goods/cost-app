"""Address parsing and validation utilities."""

from __future__ import annotations
import re
from typing import Optional


def extract_postal_code(address: Optional[str]) -> Optional[str]:
    """Extract 5-digit postal code from address."""
    if not address:
        return None
    match = re.search(r"\b(\d{5})\b", address)
    return match.group(1) if match else None


def is_spain_address(address: Optional[str]) -> bool:
    """Check if address is in Spain."""
    if not address:
        return False
    
    addr_lower = address.lower()
    spanish_keywords = ("spain", "españa", "espana", "espagne", "spanje")
    
    if any(word in addr_lower for word in spanish_keywords):
        return True
    
    if re.search(r"\bES\b|\bES-\b|\(ES\)", address, flags=re.IGNORECASE):
        return True
    
    return False


def is_france_address(address: Optional[str]) -> bool:
    """Check if address is in France (excluding Spain false positives)."""
    if not address:
        return False
    
    if is_spain_address(address):
        return False
    
    addr_lower = address.lower()
    
    # Check for French keywords
    if ("france" in addr_lower) or ("frankrijk" in addr_lower):
        return True
    
    # Check for FR country code
    if re.search(r"\bFR\b|\bFR-\b|\(FR\)", address, flags=re.IGNORECASE):
        return True
    
    # Check for French postal code pattern (01-95)
    postal_match = re.search(r"\b(\d{5})\b", addr_lower)
    if postal_match:
        try:
            dept = int(postal_match.group(1)[:2])
            if 1 <= dept <= 95:
                # Only confirm if also has French keywords
                if re.search(
                    r"\bFR\b|\bFR-\b|\(FR\)|france|frankrijk",
                    address,
                    flags=re.IGNORECASE
                ):
                    return True
        except Exception:
            pass
    
    return False