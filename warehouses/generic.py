"""
Generic warehouse calculator - Orchestrates UI and calculations.
Refactored to use modular components.
"""

from __future__ import annotations
from typing import Any, Dict
import streamlit as st

from warehouses.calculators import VVPCalculator
from warehouses.ui import render_labelling_ui, render_transfer_ui
from warehouses.exporters import export_to_excel, export_to_print
from warehouses.final_calc import final_calculator
from warehouses.second_leg import second_leg_ui


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
    """Main entry point for warehouse cost calculation."""
    
    # Initialize calculator
    calculator = VVPCalculator(wh)
    title = calculator.get_warehouse_title()
    
    # Display header
    st.subheader(title)
    st.caption(
        f"Rates used — inbound: €{calculator.inbound_per:.2f}/pallet • "
        f"outbound: €{calculator.outbound_per:.2f}/pallet • "
        f"storage: €{calculator.storage_per:.2f}/pallet/week • "
        f"order fee: €{calculator.order_fee:.2f}"
    )
    
    # Calculate base warehousing
    warehousing = calculator.calculate_base_warehousing(pallets, weeks)
    
    # Labelling UI and calculation
    labelling_required, label_total = render_labelling_ui(wh, pieces, title)
    
    # Transfer UI and calculation
    transfer_total, extra_warehousing = render_transfer_ui(
        wh, pallets, calculator.inbound_per, calculator.outbound_per,
        labelling_required, title
    )
    
    # Second leg
    st.subheader("Second Warehouse Transfer")
    second_leg_added, second_leg_breakdown = second_leg_ui(
        primary_warehouse=title,
        pallets=pallets,
    )
    
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
        second_leg_cost=second_leg_added,
    )
    
    # Display results
    st.caption(f"You are entering inputs for **{title}**")
    st.markdown("---")
    st.subheader("VVP Results")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Cost (€)", f"{totals['total_cost']:.2f}")
    with c2:
        st.metric("Cost per piece (€)", f"{totals['cpp']:.4f}")
    with c3:
        st.metric("Rounded Cost per piece (€)", f"{totals['cpp_rounded']:.2f}")
    
    # Final calculator (P&L)
    fc = final_calculator(pieces=pieces, vvp_cost_per_piece_rounded=totals['cpp_rounded'])
    
    # Breakdown
    _render_breakdown(
        warehousing, extra_warehousing, labelling_required, label_total,
        transfer_total, pallets, pallet_unit_cost, totals, buying_transport_cost,
        second_leg_breakdown, fc
    )
    
    # Export section
    st.markdown("---")
    st.subheader("Save / Export")
    
    export_rows = _build_export_rows(
        warehousing, extra_warehousing, totals, fc
    )
    
    col_a, col_b = st.columns([1.6, 1])
    with col_a:
        export_to_excel(export_rows, title)
    with col_b:
        export_to_print(export_rows, title)


def _render_breakdown(
    warehousing: Dict[str, float],
    extra_warehousing: float,
    labelling_required: bool,
    label_total: float,
    transfer_total: float,
    pallets: int,
    pallet_unit_cost: float,
    totals: Dict[str, float],
    buying_transport_cost: float,
    second_leg_breakdown: Dict,
    fc: Dict[str, Any],
) -> None:
    """Render breakdown expander."""
    with st.expander("Breakdown"):
        rows = {
            "Inbound Cost (€)": round(warehousing["inbound_cost"], 2),
            "Outbound Cost (€)": round(warehousing["outbound_cost"], 2),
            "Storage Cost (€)": round(warehousing["storage_cost"], 2),
            "Order fee (€)": round(warehousing["order_fee"], 2),
            "Warehousing Total (1st leg) (€)": round(warehousing["total"], 2),
            "Extra Warehousing on Return (€)": round(extra_warehousing, 2),
            "Labelling required?": bool(labelling_required),
            "Labelling total (€)": round(label_total, 2),
            "Transfer total (€)": round(transfer_total, 2),
            "Pallet unit (€/pallet)": round(float(pallet_unit_cost) or 0.0, 2),
            "Pallets (#)": pallets,
            "Pallet cost total (€)": round(totals['pallet_cost_total'], 2),
            "Buying transport (€ total)": round(float(buying_transport_cost), 2),
        }
        
        if second_leg_breakdown:
            rows.update(second_leg_breakdown)
        
        rows.update({
            "Warehousing Total (incl. return) (€)": round(totals['warehousing_total'], 2),
            "TOTAL (€)": round(totals['total_cost'], 2),
            "Cost per piece (€)": round(totals['cpp'], 4),
            "Rounded VPP (€)": round(totals['cpp_rounded'], 2),
        })
        
        if isinstance(fc, dict):
            rows.update({
                "Sales price (€ / pc)": fc.get("sales_price_cpp"),
                "Unit purchase (€ / pc)": fc.get("unit_purchase_cpp"),
                "Unit delivery (€ / pc)": fc.get("unit_delivery_cpp"),
                "Unit gross cost (€ / pc)": fc.get("unit_gross_cpp"),
                "Total revenue (€)": fc.get("total_revenue"),
                "Gross profit (€)": fc.get("gross_profit"),
                "Gross margin (%)": fc.get("gross_margin_pct"),
                "Net profit (€)": fc.get("net_profit"),
                "Net margin (%)": fc.get("net_margin_pct"),
                "Delivery transport (TOTAL €)": fc.get("delivery_transport_total"),
            })
        
        st.write(rows)


def _build_export_rows(
    warehousing: Dict[str, float],
    extra_warehousing: float,
    totals: Dict[str, float],
    fc: Dict[str, Any],
) -> list:
    """Build export rows for Excel/Print."""
    def _blank(x):
        return "" if (x is None or x == "" or x == 0 or x == 0.0) else x
    
    export_rows = []
    
    # Warehousing
    export_rows.append(("— Warehousing —", ""))
    export_rows += [
        ("Inbound Cost (€)", round(warehousing["inbound_cost"], 2)),
        ("Outbound Cost (€)", round(warehousing["outbound_cost"], 2)),
        ("Storage Cost (€)", round(warehousing["storage_cost"], 2)),
    ]
    if extra_warehousing > 0:
        export_rows.append(("Warehousing extra (return) (€)", round(extra_warehousing, 2)))
    export_rows.append(("Warehousing Total (incl. return) (€)", round(totals['warehousing_total'], 2)))
    
    # Commercials
    sales = fc.get("sales_price_cpp") if isinstance(fc, dict) else None
    purch = fc.get("unit_purchase_cpp") if isinstance(fc, dict) else None
    unit_del = fc.get("unit_delivery_cpp") if isinstance(fc, dict) else None
    del_total = fc.get("delivery_transport_total") if isinstance(fc, dict) else None
    
    export_rows.append(("", ""))
    export_rows.append(("— Commercials —", ""))
    export_rows += [
        ("Sales price (€ / pc)", _blank(sales)),
        ("Unit purchase (€ / pc)", _blank(purch)),
        ("Unit delivery (€ / pc)", _blank(unit_del)),
        ("Delivery transport (TOTAL €)", _blank(del_total)),
    ]
    
    # Results
    grosp = fc.get("gross_profit") if isinstance(fc, dict) else None
    grosm = fc.get("gross_margin_pct") if isinstance(fc, dict) else None
    netp = fc.get("net_profit") if isinstance(fc, dict) else None
    netm = fc.get("net_margin_pct") if isinstance(fc, dict) else None
    
    export_rows.append(("", ""))
    export_rows.append(("— Results —", ""))
    export_rows += [
        ("TOTAL (€)", round(totals['total_cost'], 2)),
        ("Cost per piece (€)", round(totals['cpp'], 4)),
        ("Rounded CPP (€)", round(totals['cpp_rounded'], 2)),
        ("Gross profit (€)", _blank(grosp)),
        ("Gross margin (%)", _blank(grosm)),
        ("Net profit (€)", _blank(netp)),
        ("Net margin (%)", _blank(netm)),
    ]
    
    return export_rows