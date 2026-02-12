"""
Generic Warehouse Calculator UI
================================

Main orchestration module for warehouse cost calculation workflow.

This module coordinates:
- Base warehousing calculation (inbound, outbound, storage, order fee)
- Labeling cost calculation and UI
- Transfer cost calculation and UI
- Second warehouse leg calculation
- VVP (Total cost) calculation and display
- P&L (Final calculator) integration
- Export functionality (Excel, Print)

Workflow:
1. Initialize VVPCalculator with selected warehouse
2. Calculate base warehousing costs
3. Render labeling UI → get labeling cost
4. Render transfer UI → get transfer cost
5. Render second leg UI → get second leg cost
6. Calculate total VVP cost
7. Display results
8. Run final calculator (P&L)
9. Show breakdown
10. Provide export options

Related Files:
- warehouses/calculators.py: VVPCalculator, cost calculation logic
- ui/warehouse_inputs.py: Labeling and transfer UI components
- ui/final_calc.py: P&L calculator
- ui/second_leg.py: Second warehouse leg UI
- warehouses/exporters/: Excel and print exporters
"""

from __future__ import annotations
from typing import Any, Dict, Tuple
import streamlit as st

from warehouses.calculators import VVPCalculator
from .warehouse_inputs import render_labelling_ui, render_transfer_ui
from .final_calc import final_calculator
from .second_leg import second_leg_ui
from warehouses.exporters import export_to_excel, export_to_print


# ============================================================================
# MAIN CALCULATOR
# ============================================================================

def compute_generic(
    *,
    wh: Dict[str, Any],
    all_whs_map: Dict[str, Dict[str, Any]],
    pieces: int,
    pallets: int,
    weeks: int,
    buying_transport_cost: float,
    pallet_unit_cost: float,
) -> None:
    """
    Main warehouse cost calculation orchestrator.
    
    Coordinates entire calculation workflow:
    - Base warehousing costs
    - Optional labeling costs
    - Optional transfer costs
    - Optional second leg costs
    - Total VVP calculation
    - P&L calculation
    - Results display
    - Export options
    
    Args:
        wh: Selected warehouse configuration
        all_whs_map: Map of all warehouses (for second leg)
        pieces: Number of pieces in order
        pallets: Number of pallets
        weeks: Storage duration in weeks
        buying_transport_cost: Inbound transport cost
        pallet_unit_cost: Cost per pallet unit
    """
    # Initialize calculator
    calculator = VVPCalculator(wh)
    warehouse_title = calculator.get_warehouse_title()
    
    # Display header
    _render_header(calculator, warehouse_title)
    
    # Calculate base warehousing
    warehousing = calculator.calculate_base_warehousing(pallets, weeks)
    
    # Labeling UI and calculation
    labeling_required, label_total = render_labelling_ui(wh, pieces, warehouse_title)
    
    # Transfer UI and calculation
    transfer_total, extra_warehousing = render_transfer_ui(
        wh, pallets, calculator.inbound_per, calculator.outbound_per,
        labeling_required, warehouse_title
    )
    
    # Second warehouse leg
    second_leg_cost, second_leg_breakdown = _render_second_leg(warehouse_title, pallets)
    
    # Calculate totals
    totals = calculator.calculate_total(
        pallets=pallets,
        pieces=pieces,
        weeks=weeks,
        buying_transport_cost=buying_transport_cost,
        pallet_unit_cost=pallet_unit_cost,
        labelling_total=label_total,
        transfer_total=transfer_total,
        extra_warehousing=extra_warehousing,
        second_leg_cost=second_leg_cost,
    )
    
    # Display VVP results
    _render_vvp_results(warehouse_title, totals)
    
    # Final calculator (P&L)
    fc_results = final_calculator(pieces=pieces, vvp_cost_per_piece_rounded=totals['cpp_rounded'])
    
    # Breakdown
    _render_breakdown(
        warehousing=warehousing,
        extra_warehousing=extra_warehousing,
        labeling_required=labeling_required,
        label_total=label_total,
        transfer_total=transfer_total,
        pallets=pallets,
        pallet_unit_cost=pallet_unit_cost,
        buying_transport_cost=buying_transport_cost,
        totals=totals,
        second_leg_breakdown=second_leg_breakdown,
        fc_results=fc_results,
    )
    
    # Export section
    _render_export_section(
        warehouse_title=warehouse_title,
        warehousing=warehousing,
        extra_warehousing=extra_warehousing,
        totals=totals,
        fc_results=fc_results,
    )


# ============================================================================
# DISPLAY COMPONENTS
# ============================================================================

def _render_header(calculator: VVPCalculator, warehouse_title: str) -> None:
    """
    Render warehouse header with rates.
    
    Args:
        calculator: VVPCalculator instance
        warehouse_title: Warehouse display name
    """
    st.subheader(warehouse_title)
    st.caption(
        f"Rates — Inbound: €{calculator.inbound_per:.2f}/pallet • "
        f"Outbound: €{calculator.outbound_per:.2f}/pallet • "
        f"Storage: €{calculator.storage_per:.2f}/pallet/week • "
        f"Order fee: €{calculator.order_fee:.2f}"
    )


def _render_second_leg(warehouse_title: str, pallets: int) -> Tuple[float, Dict]:
    """
    Render second warehouse leg UI.
    
    Args:
        warehouse_title: Primary warehouse name
        pallets: Number of pallets
        
    Returns:
        Tuple of (second_leg_cost, second_leg_breakdown)
    """
    st.subheader("Second Warehouse Transfer")
    
    second_leg_cost, second_leg_breakdown = second_leg_ui(
        primary_warehouse=warehouse_title,
        pallets=pallets,
    )
    
    return second_leg_cost, second_leg_breakdown


def _render_vvp_results(warehouse_title: str, totals: Dict[str, float]) -> None:
    """
    Render VVP calculation results.
    
    Shows:
    - Total cost
    - Cost per piece
    - Rounded cost per piece
    
    Args:
        warehouse_title: Warehouse name for context caption
        totals: Calculation results from VVPCalculator
    """
    st.caption(f"You are entering inputs for **{warehouse_title}**")
    st.markdown("---")
    st.subheader("VVP Results")
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.metric("Total Cost (€)", f"{totals['total_cost']:.2f}")
    
    with c2:
        st.metric("Cost per piece (€)", f"{totals['cpp']:.4f}")
    
    with c3:
        st.metric("Rounded Cost per piece (€)", f"{totals['cpp_rounded']:.2f}")


def _render_breakdown(
    warehousing: Dict[str, float],
    extra_warehousing: float,
    labeling_required: bool,
    label_total: float,
    transfer_total: float,
    pallets: int,
    pallet_unit_cost: float,
    buying_transport_cost: float,
    totals: Dict[str, float],
    second_leg_breakdown: Dict,
    fc_results: Dict[str, Any],
) -> None:
    """
    Render detailed calculation breakdown.
    
    Shows complete breakdown of:
    - Warehousing costs (inbound, outbound, storage, order fee)
    - Extra warehousing on return
    - Labeling costs
    - Transfer costs
    - Pallet costs
    - Buying transport
    - Second leg costs (if applicable)
    - Total costs and per-piece costs
    - P&L results (if calculated)
    
    Args:
        warehousing: Base warehousing cost breakdown
        extra_warehousing: Extra warehousing on return
        labeling_required: Whether labeling was selected
        label_total: Total labeling cost
        transfer_total: Total transfer cost
        pallets: Number of pallets
        pallet_unit_cost: Cost per pallet unit
        buying_transport_cost: Inbound transport cost
        totals: Total cost calculations
        second_leg_breakdown: Second leg cost breakdown (if applicable)
        fc_results: Final calculator P&L results
    """
    with st.expander("📊 Detailed Breakdown"):
        breakdown = {}
        
        # Warehousing costs
        breakdown.update({
            "— Warehousing —": "",
            "Inbound Cost (€)": round(warehousing["inbound_cost"], 2),
            "Outbound Cost (€)": round(warehousing["outbound_cost"], 2),
            "Storage Cost (€)": round(warehousing["storage_cost"], 2),
            "Order fee (€)": round(warehousing["order_fee"], 2),
            "Warehousing Total (1st leg) (€)": round(warehousing["total"], 2),
        })
        
        if extra_warehousing > 0:
            breakdown["Extra Warehousing on Return (€)"] = round(extra_warehousing, 2)
        
        # Labeling
        breakdown.update({
            "— Labeling —": "",
            "Labeling required?": bool(labeling_required),
            "Labeling total (€)": round(label_total, 2),
        })
        
        # Transfer
        if transfer_total > 0:
            breakdown.update({
                "— Transfer —": "",
                "Transfer total (€)": round(transfer_total, 2),
            })
        
        # Pallets
        breakdown.update({
            "— Pallets —": "",
            "Pallet unit (€/pallet)": round(float(pallet_unit_cost) or 0.0, 2),
            "Pallets (#)": pallets,
            "Pallet cost total (€)": round(totals['pallet_cost_total'], 2),
        })
        
        # Buying transport
        breakdown.update({
            "— Buying Transport —": "",
            "Buying transport (€ total)": round(float(buying_transport_cost), 2),
        })
        
        # Second leg
        if second_leg_breakdown:
            breakdown.update({
                "— Second Warehouse Leg —": "",
            })
            breakdown.update(second_leg_breakdown)
        
        # Totals
        breakdown.update({
            "— VVP Totals —": "",
            "Warehousing Total (incl. return) (€)": round(totals['warehousing_total'], 2),
            "TOTAL (€)": round(totals['total_cost'], 2),
            "Cost per piece (€)": round(totals['cpp'], 4),
            "Rounded VVP (€)": round(totals['cpp_rounded'], 2),
        })
        
        # P&L results
        if isinstance(fc_results, dict) and fc_results.get("sales_price_cpp"):
            breakdown.update({
                "— P&L Results —": "",
                "Sales price (€ / pc)": fc_results.get("sales_price_cpp"),
                "Unit purchase (€ / pc)": fc_results.get("unit_purchase_cpp"),
                "Unit delivery (€ / pc)": fc_results.get("unit_delivery_cpp"),
                "Unit gross cost (€ / pc)": fc_results.get("unit_gross_cpp"),
                "Total revenue (€)": fc_results.get("total_revenue"),
                "Gross profit (€)": fc_results.get("gross_profit"),
                "Gross margin (%)": fc_results.get("gross_margin_pct"),
                "Net profit (€)": fc_results.get("net_profit"),
                "Net margin (%)": fc_results.get("net_margin_pct"),
                "Delivery transport (TOTAL €)": fc_results.get("delivery_transport_total"),
            })
        
        st.write(breakdown)


def _render_export_section(
    warehouse_title: str,
    warehousing: Dict[str, float],
    extra_warehousing: float,
    totals: Dict[str, float],
    fc_results: Dict[str, Any],
) -> None:
    """
    Render export options section.
    
    Provides:
    - Excel export button
    - Print export button
    
    Args:
        warehouse_title: Warehouse name for export filename
        warehousing: Warehousing cost breakdown
        extra_warehousing: Extra warehousing cost
        totals: Total calculations
        fc_results: Final calculator results
    """
    st.markdown("---")
    st.subheader("Save / Export")
    
    # Build export data
    export_rows = _build_export_rows(
        warehousing=warehousing,
        extra_warehousing=extra_warehousing,
        totals=totals,
        fc_results=fc_results,
    )
    
    # Render export buttons
    col_excel, col_print = st.columns([1.6, 1])
    
    with col_excel:
        export_to_excel(export_rows, warehouse_title)
    
    with col_print:
        export_to_print(export_rows, warehouse_title)


# ============================================================================
# EXPORT DATA PREPARATION
# ============================================================================

def _build_export_rows(
    warehousing: Dict[str, float],
    extra_warehousing: float,
    totals: Dict[str, float],
    fc_results: Dict[str, Any],
) -> list:
    """
    Build export data rows for Excel and print.
    
    Creates structured list of (label, value) tuples for export.
    Groups data into sections:
    - Warehousing
    - Commercials (P&L inputs)
    - Results (VVP and P&L outputs)
    
    Args:
        warehousing: Warehousing cost breakdown
        extra_warehousing: Extra warehousing cost
        totals: Total calculations
        fc_results: Final calculator results
        
    Returns:
        List of (label, value) tuples
    """
    def _blank(x):
        """Convert None/0 to empty string for cleaner export."""
        return "" if (x is None or x == "" or x == 0 or x == 0.0) else x
    
    export_rows = []
    
    # Warehousing section
    export_rows.append(("— Warehousing —", ""))
    export_rows.extend([
        ("Inbound Cost (€)", round(warehousing["inbound_cost"], 2)),
        ("Outbound Cost (€)", round(warehousing["outbound_cost"], 2)),
        ("Storage Cost (€)", round(warehousing["storage_cost"], 2)),
        ("Order fee (€)", round(warehousing["order_fee"], 2)),
    ])
    
    if extra_warehousing > 0:
        export_rows.append(("Warehousing extra (return) (€)", round(extra_warehousing, 2)))
    
    export_rows.append(("Warehousing Total (incl. return) (€)", round(totals['warehousing_total'], 2)))
    
    # Commercials section
    sales = fc_results.get("sales_price_cpp") if isinstance(fc_results, dict) else None
    purchase = fc_results.get("unit_purchase_cpp") if isinstance(fc_results, dict) else None
    unit_delivery = fc_results.get("unit_delivery_cpp") if isinstance(fc_results, dict) else None
    delivery_total = fc_results.get("delivery_transport_total") if isinstance(fc_results, dict) else None
    
    export_rows.append(("", ""))
    export_rows.append(("— Commercials —", ""))
    export_rows.extend([
        ("Sales price (€ / pc)", _blank(sales)),
        ("Unit purchase (€ / pc)", _blank(purchase)),
        ("Unit delivery (€ / pc)", _blank(unit_delivery)),
        ("Delivery transport (TOTAL €)", _blank(delivery_total)),
    ])
    
    # Results section
    gross_profit = fc_results.get("gross_profit") if isinstance(fc_results, dict) else None
    gross_margin = fc_results.get("gross_margin_pct") if isinstance(fc_results, dict) else None
    net_profit = fc_results.get("net_profit") if isinstance(fc_results, dict) else None
    net_margin = fc_results.get("net_margin_pct") if isinstance(fc_results, dict) else None
    
    export_rows.append(("", ""))
    export_rows.append(("— Results —", ""))
    export_rows.extend([
        ("TOTAL (€)", round(totals['total_cost'], 2)),
        ("Cost per piece (€)", round(totals['cpp'], 4)),
        ("Rounded CPP (€)", round(totals['cpp_rounded'], 2)),
        ("Gross profit (€)", _blank(gross_profit)),
        ("Gross margin (%)", _blank(gross_margin)),
        ("Net profit (€)", _blank(net_profit)),
        ("Net margin (%)", _blank(net_margin)),
    ])
    
    return export_rows