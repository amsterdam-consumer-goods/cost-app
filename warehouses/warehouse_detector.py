"""Warehouse detection utilities - especially SVZ detection."""

from __future__ import annotations
import re
from typing import Optional, List, Set
import streamlit as st


class WarehouseDetector:
    """Detect current warehouse and check feature eligibility."""
    
    # SVZ warehouses allowed for France auto-delivery
    ALLOWED_SVZ_IDS: Set[str] = {"nl_svz", "svz"}
    SVZ_TOKEN_HINTS: tuple[str, ...] = ("svz",)
    
    @staticmethod
    def get_current_warehouse_id() -> Optional[str]:
        """Get current warehouse ID from session state."""
        candidates = (
            "warehouse_id",
            "selected_warehouse_id",
            "selected_warehouse",
            "warehouse",
            "wh_id",
            "current_warehouse_id",
        )
        
        for key in candidates:
            if key in st.session_state and st.session_state.get(key):
                return WarehouseDetector._normalize_id(st.session_state.get(key))
        
        return None
    
    @classmethod
    def is_svz_warehouse(cls) -> bool:
        """Check if current warehouse is SVZ (allows France auto-delivery)."""
        wid = cls.get_current_warehouse_id()
        if not wid:
            return False
        
        # Exact ID match
        if wid in cls.ALLOWED_SVZ_IDS:
            return True
        
        # Token-based match
        tokens = set(cls._tokenize(wid))
        if any(hint in wid for hint in cls.SVZ_TOKEN_HINTS):
            return True
        if any(hint in tokens for hint in cls.SVZ_TOKEN_HINTS):
            return True
        
        return False
    
    @staticmethod
    def _normalize_id(text: Optional[str]) -> Optional[str]:
        """Normalize ID to lowercase with underscores."""
        if not text:
            return None
        normalized = str(text).strip().lower()
        normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
        normalized = re.sub(r"_+", "_", normalized).strip("_")
        return normalized
    
    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Split text into tokens."""
        return [t for t in re.split(r"[_\-\s/\\]+", text) if t]