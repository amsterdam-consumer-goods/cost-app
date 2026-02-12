"""
Warehouse Detection Utilities
==============================

Utilities for detecting current warehouse and checking feature eligibility.

This module provides:
- Current warehouse ID detection from session state
- SVZ warehouse detection (for France auto-delivery)
- ID normalization and token matching

SVZ Detection:
- Used to determine France auto-delivery eligibility
- Only SVZ warehouses can use automatic France delivery cost calculation
- Detection via exact ID match OR token-based matching

Related Files:
- ui/final_calc.py: Uses SVZ detection for France auto-delivery
- data/catalog.json: Warehouse configurations
"""

from __future__ import annotations
import re
from typing import Optional, List, Set
import streamlit as st


# ============================================================================
# WAREHOUSE DETECTOR
# ============================================================================

class WarehouseDetector:
    """
    Detect current warehouse and check feature eligibility.
    
    Primary use case: Determine if France auto-delivery is available.
    France auto-delivery is only enabled for SVZ warehouses.
    """
    
    # SVZ warehouse IDs allowed for France auto-delivery
    ALLOWED_SVZ_IDS: Set[str] = {"nl_svz", "svz"}
    
    # Token hints for SVZ detection
    SVZ_TOKEN_HINTS: tuple[str, ...] = ("svz",)
    
    @staticmethod
    def get_current_warehouse_id() -> Optional[str]:
        """
        Get current warehouse ID from session state.
        
        Searches common session state keys used across the application:
        - warehouse_id
        - selected_warehouse_id
        - selected_warehouse
        - warehouse
        - wh_id
        - current_warehouse_id
        
        Returns:
            Normalized warehouse ID or None if not found
        """
        # Common session state keys for warehouse ID
        candidates = (
            "warehouse_id",
            "selected_warehouse_id",
            "selected_warehouse",
            "warehouse",
            "wh_id",
            "current_warehouse_id",
        )
        
        for key in candidates:
            value = st.session_state.get(key)
            if value:
                return WarehouseDetector._normalize_id(value)
        
        return None
    
    @classmethod
    def is_svz_warehouse(cls) -> bool:
        """
        Check if current warehouse is SVZ.
        
        SVZ warehouses are allowed to use France auto-delivery feature.
        
        Detection methods:
        1. Exact ID match against ALLOWED_SVZ_IDS
        2. Token-based matching using SVZ_TOKEN_HINTS
        
        Returns:
            True if current warehouse is SVZ, False otherwise
        """
        wid = cls.get_current_warehouse_id()
        
        if not wid:
            return False
        
        # Exact ID match
        if wid in cls.ALLOWED_SVZ_IDS:
            return True
        
        # Token-based match (substring)
        if any(hint in wid for hint in cls.SVZ_TOKEN_HINTS):
            return True
        
        # Token-based match (split tokens)
        tokens = set(cls._tokenize(wid))
        if any(hint in tokens for hint in cls.SVZ_TOKEN_HINTS):
            return True
        
        return False
    
    @staticmethod
    def _normalize_id(text: Optional[str]) -> Optional[str]:
        """
        Normalize warehouse ID to lowercase with underscores.
        
        Process:
        1. Convert to lowercase
        2. Replace non-alphanumeric chars with underscores
        3. Collapse multiple underscores
        4. Strip leading/trailing underscores
        
        Args:
            text: Raw warehouse ID
            
        Returns:
            Normalized ID or None
        
        Examples:
            "NL SVZ" → "nl_svz"
            "Germany / Offergeld" → "germany_offergeld"
            "FR-Coquelle" → "fr_coquelle"
        """
        if not text:
            return None
        
        normalized = str(text).strip().lower()
        normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
        normalized = re.sub(r"_+", "_", normalized).strip("_")
        
        return normalized
    
    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """
        Split text into tokens for matching.
        
        Splits on: underscores, hyphens, spaces, slashes, backslashes
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of tokens
        
        Examples:
            "nl_svz" → ["nl", "svz"]
            "Germany/Offergeld" → ["Germany", "Offergeld"]
            "FR-Coquelle" → ["FR", "Coquelle"]
        """
        return [t for t in re.split(r"[_\-\s/\\]+", text) if t]