"""Only France delivery cost calculator."""

from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Optional
import streamlit as st


class FranceDeliveryCalculator:
    """Handles France delivery cost lookups."""
    
    def __init__(self):
        """Initialize with France rates table."""
        self.rates_table = self._load_rates()
    
    @staticmethod
    def _load_rates() -> List[Dict]:
        """Load France delivery rates from JSON."""
        base_dir = Path(__file__).resolve().parents[2]
        rates_path = base_dir / "data" / "fr_delivery_rates.json"
        
        if not rates_path.exists():
            st.warning(f"France delivery rates JSON not found: {rates_path}")
            return []
        
        try:
            with open(rates_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            st.error(f"France delivery rates JSON could not be read: {e}")
            return []
        
        rates = []
        for row in (data if isinstance(data, list) else []):
            try:
                dept = str(row.get("dept", "")).zfill(2)[:2]
                pallets = int(row.get("pallets"))
                total = float(row.get("total"))
                
                if dept and 1 <= int(dept) <= 95 and pallets >= 1 and total >= 0:
                    rates.append({"dept": dept, "pallets": pallets, "total": total})
            except Exception:
                continue
        
        return rates
    
    def lookup_cost(self, postal_code: str, pallets: int) -> float:
        """
        Lookup delivery cost for France address.
        
        Args:
            postal_code: 5-digit French postal code
            pallets: Number of pallets (capped at 33 for full truck)
            
        Returns:
            Delivery cost in euros
        """
        if not self.rates_table:
            return 0.0
        
        dept = str(postal_code)[:2].zfill(2)
        
        try:
            if not (1 <= int(dept) <= 95):
                return 0.0
        except Exception:
            return 0.0
        
        # Cap pallets at 33 (full truck), minimum 1
        effective_pallets = max(1, min(33, int(pallets)))
        
        # Filter rates for this department
        dept_rates = [r for r in self.rates_table if r["dept"] == dept]
        if not dept_rates:
            return 0.0
        
        # Try exact match first
        exact_match = next(
            (r for r in dept_rates if r["pallets"] == effective_pallets),
            None
        )
        if exact_match:
            return float(exact_match["total"])
        
        # Fall back to nearest lower pallet count
        lower_rates = [r for r in dept_rates if r["pallets"] <= effective_pallets]
        if lower_rates:
            lower_rates.sort(key=lambda x: x["pallets"])
            return float(lower_rates[-1]["total"])
        
        # If no lower rates, use minimum available
        dept_rates.sort(key=lambda x: x["pallets"])
        return float(dept_rates[0]["total"])
    
    @staticmethod
    def get_effective_pallets(pallets: int) -> int:
        """Get effective pallet count (capped at 33)."""
        return max(1, min(33, int(pallets or 0)))