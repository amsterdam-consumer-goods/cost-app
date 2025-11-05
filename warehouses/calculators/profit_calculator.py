"""Profit and Loss calculator - Pure calculation logic."""

from __future__ import annotations
from typing import Dict


class ProfitCalculator:
    """Handles P&L calculations."""
    
    @staticmethod
    def calculate(
        pieces: int,
        vvp_cost_per_piece: float,
        purchase_price_per_piece: float,
        sales_price_per_piece: float,
        delivery_transport_total: float,
    ) -> Dict[str, float]:
        """
        Calculate complete P&L metrics.
        
        Returns:
            Dict with all financial metrics
        """
        unit_vvp = float(vvp_cost_per_piece)
        unit_purchase = float(purchase_price_per_piece)
        unit_delivery = (delivery_transport_total / pieces) if pieces else 0.0
        
        unit_gross_cost = unit_vvp + unit_purchase
        total_gross_cost = unit_gross_cost * pieces
        total_revenue = sales_price_per_piece * pieces
        gross_profit = total_revenue - total_gross_cost
        net_profit = total_revenue - total_gross_cost - delivery_transport_total
        
        gross_margin_pct = (gross_profit / total_revenue * 100.0) if total_revenue > 0 else 0.0
        net_margin_pct = (net_profit / total_revenue * 100.0) if total_revenue > 0 else 0.0
        total_cost = (unit_gross_cost * pieces) + delivery_transport_total
        
        return {
            "unit_vvp_cpp": round(unit_vvp, 2),
            "unit_purchase_cpp": round(unit_purchase, 3),
            "unit_delivery_cpp": round(unit_delivery, 4),
            "unit_gross_cpp": round(unit_gross_cost, 3),
            "sales_price_cpp": round(sales_price_per_piece, 3),
            "pieces": int(pieces),
            "delivery_transport_total": round(delivery_transport_total, 2),
            "total_gross_cost": round(total_gross_cost, 2),
            "total_revenue": round(total_revenue, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_margin_pct": round(gross_margin_pct, 2),
            "net_profit": round(net_profit, 2),
            "net_margin_pct": round(net_margin_pct, 2),
            "total_cost": round(total_cost, 2),
        }