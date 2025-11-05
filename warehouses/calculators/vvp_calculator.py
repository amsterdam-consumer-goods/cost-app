"""VVP Calculator - Pure calculation logic without UI."""

from __future__ import annotations
import math
from typing import Any, Dict, Tuple
from pathlib import Path
import json


class VVPCalculator:
    """Handles VVP cost calculations."""
    
    def __init__(self, warehouse: Dict[str, Any]):
        """Initialize with warehouse data."""
        self.warehouse = warehouse
        self.rates = warehouse.get("rates", {}) or {}
        self.features = warehouse.get("features", {}) or {}
        
        # Extract base rates
        self.inbound_per = float(self.rates.get("inbound", 0.0))
        self.outbound_per = float(self.rates.get("outbound", 0.0))
        self.storage_per = float(self.rates.get("storage", 0.0))
        self.order_fee = float(self.rates.get("order_fee", 0.0))
    
    def get_warehouse_title(self) -> str:
        """Get formatted warehouse title."""
        name = self.warehouse.get("name") or self.warehouse.get("id") or "Warehouse"
        country = self.warehouse.get("country", "")
        return f"{country} / {name}" if country else name
    
    def calculate_base_warehousing(
        self,
        pallets: int,
        weeks: int
    ) -> Dict[str, float]:
        """Calculate base warehousing costs."""
        inbound_cost = float(pallets) * self.inbound_per
        outbound_cost = float(pallets) * self.outbound_per
        storage_cost = float(pallets) * float(weeks) * self.storage_per
        total = inbound_cost + outbound_cost + storage_cost + self.order_fee
        
        return {
            "inbound_cost": inbound_cost,
            "outbound_cost": outbound_cost,
            "storage_cost": storage_cost,
            "order_fee": self.order_fee,
            "total": total,
        }
    
    def calculate_labelling(
        self,
        pieces: int,
        is_required: bool
    ) -> Tuple[float, Dict[str, Any]]:
        """Calculate labelling costs."""
        if not is_required:
            return 0.0, {}
        
        lab = self.features.get("label_costs")
        if not isinstance(lab, dict):
            return 0.0, {}
        
        label_per_piece = float(lab.get("label", 0.0))
        labelling_per_piece = float(lab.get("labelling", 0.0))
        total = (label_per_piece + labelling_per_piece) * float(pieces)
        
        return total, {
            "label_per_piece": label_per_piece,
            "labelling_per_piece": labelling_per_piece,
            "total": total,
        }
    
    def calculate_transfer(
        self,
        pallets: int,
        transfer_mode: str,
        **kwargs
    ) -> Tuple[float, float, Dict[str, Any]]:
        """
        Calculate transfer costs.
        
        Returns:
            (transfer_total, extra_warehousing, details)
        """
        if transfer_mode == "excel":
            return self._calculate_transfer_excel(pallets, **kwargs)
        elif transfer_mode == "fixed":
            return self._calculate_transfer_fixed(**kwargs)
        else:
            return 0.0, 0.0, {}
    
    def _calculate_transfer_excel(
        self,
        pallets: int,
        rates_excel: Dict[int, float],
        wh_to_lab: bool,
        lab_to_wh: bool,
        double_stack: bool = False,
    ) -> Tuple[float, float, Dict[str, Any]]:
        """Calculate transfer using Excel lookup."""
        pallets_for_lookup = math.ceil(pallets / 2) if (double_stack and pallets > 0) else pallets
        truck_cost = self._lookup_truck_cost(rates_excel, pallets_for_lookup) if (wh_to_lab or lab_to_wh) else 0.0
        
        wh_to_lab_cost = truck_cost if wh_to_lab else 0.0
        lab_to_wh_cost = truck_cost if lab_to_wh else 0.0
        transfer_total = wh_to_lab_cost + lab_to_wh_cost
        
        # Extra warehousing if round trip
        extra_warehousing = 0.0
        if wh_to_lab and lab_to_wh:
            extra_warehousing = float(pallets) * (self.inbound_per + self.outbound_per)
        
        return transfer_total, extra_warehousing, {
            "mode": "excel",
            "wh_to_lab_cost": wh_to_lab_cost,
            "lab_to_wh_cost": lab_to_wh_cost,
            "truck_cost": truck_cost,
        }
    
    def _calculate_transfer_fixed(
        self,
        fixed_amount: float = 0.0,
    ) -> Tuple[float, float, Dict[str, Any]]:
        """Calculate fixed transfer cost."""
        return fixed_amount, 0.0, {
            "mode": "fixed",
            "fixed_amount": fixed_amount,
        }
    
    @staticmethod
    def _lookup_truck_cost(rates: Dict[int, float], pallets: int) -> float:
        """Lookup truck cost from rates table."""
        if not rates:
            return 0.0
        n = max(1, min(66, int(pallets)))
        if n in rates:
            return rates[n]
        lower = [k for k in rates if k <= n]
        return rates[max(lower)] if lower else 0.0
    
    @staticmethod
    def load_truck_rates(path_str: str) -> Dict[int, float]:
        """Load truck rates from file."""
        if not path_str:
            return {}
        
        p = Path(path_str)
        if not p.exists():
            return {}
        
        rates: Dict[int, float] = {}
        suffix = p.suffix.lower()
        
        if suffix == ".json":
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                return {}
            
            if isinstance(data, dict):
                for k, v in data.items():
                    try:
                        rates[int(k)] = float(v)
                    except Exception:
                        pass
            elif isinstance(data, list):
                for row in data:
                    try:
                        rates[int(row["pallets"])] = float(row["truck_cost"])
                    except Exception:
                        pass
        
        elif suffix in (".xlsx", ".xls", ".csv"):
            try:
                import pandas as pd
                df = pd.read_csv(p) if suffix == ".csv" else pd.read_excel(p, sheet_name=0)
                for _, row in df.iterrows():
                    try:
                        rates[int(row["pallets"])] = float(row["truck_cost"])
                    except Exception:
                        continue
            except Exception:
                return {}
        
        return rates
    
    def calculate_total(
        self,
        pallets: int,
        pieces: int,
        weeks: int,
        buying_transport_cost: float,
        pallet_unit_cost: float,
        labelling_total: float,
        transfer_total: float,
        extra_warehousing: float,
        second_leg_cost: float,
    ) -> Dict[str, float]:
        """Calculate final totals."""
        warehousing = self.calculate_base_warehousing(pallets, weeks)
        warehousing_total = warehousing["total"] + extra_warehousing
        
        pallet_cost_total = float(pallet_unit_cost) * float(pallets) if pallet_unit_cost > 0 else 0.0
        
        base_total = (
            warehousing_total +
            float(buying_transport_cost) +
            pallet_cost_total +
            labelling_total +
            transfer_total
        )
        
        total_cost = base_total + second_leg_cost
        cpp = (total_cost / float(pieces)) if pieces else 0.0
        cpp_rounded = math.ceil(cpp * 100) / 100.0
        
        return {
            "warehousing_total": warehousing_total,
            "pallet_cost_total": pallet_cost_total,
            "base_total": base_total,
            "total_cost": total_cost,
            "cpp": cpp,
            "cpp_rounded": cpp_rounded,
        }