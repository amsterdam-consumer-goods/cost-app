# warehouses/nl_mentrex.py
"""
Netherlands / Mentrex — first leg + optional second leg.

First leg:
- Inbound  : €5.10 / pallet
- Outbound : €5.10 / pallet
- Storage  : €1.40 / pallet / week
- Order fee: €50.00 flat (applies if pallets > 0 and pieces > 0)
- Optional pallet cost from app.py: (€/pallet) × pallets → INCLUDED in VVP if > 0

Second leg (optional):
- Computed via warehouses/second_leg.py using the target warehouse rates.
- Returned amount is added to VVP when enabled in the UI.
"""

from __future__ import annotations
import math
import streamlit as st
from .final_calc import final_calculator
from .second_leg import second_leg_ui


def compute_nl_mentrex(
    pieces: int,
    pallets: int,
    weeks: int,
    buying_transport_cost: float,
    pallet_unit_cost: float,
) -> None:
    """Render Netherlands / Mentrex calculator and VVP results."""
    st.subheader("Netherlands / Mentrex")

    # --- Fixed rates (first leg)
    INBOUND_PER_PALLET = 5.10
    OUTBOUND_PER_PALLET = 5.10
    STORAGE_PER_PALLET_PER_WEEK = 1.40
    ORDER_FIXED_FEE = 50.0

    # --- First-leg components
    inbound_cost = pallets * INBOUND_PER_PALLET
    outbound_cost = pallets * OUTBOUND_PER_PALLET
    storage_cost = pallets * weeks * STORAGE_PER_PALLET_PER_WEEK
    order_fee = ORDER_FIXED_FEE if (pallets > 0 and pieces > 0) else 0.0

    # Optional pallet cost
    pallet_cost_total = (pallet_unit_cost or 0.0) * pallets if (pallet_unit_cost or 0) > 0 else 0.0

    warehousing_total = inbound_cost + outbound_cost + storage_cost + order_fee

    # --- Second leg (optional)
    second_leg_added_cost, second_leg_breakdown = second_leg_ui(
        primary_warehouse="Netherlands / Mentrex",
        pallets=pallets,
        # pieces not used by second_leg in current design
    )

    # --- Totals for VVP
    base_total = (
        warehousing_total
        + buying_transport_cost
        + pallet_cost_total        # include optional pallet cost
    )
    total_cost = base_total + second_leg_added_cost

    cost_per_piece = (total_cost / pieces) if pieces else 0.0
    cost_per_piece_rounded = math.ceil(cost_per_piece * 100) / 100.0

    st.caption("You are entering inputs for **Netherlands / Mentrex**")

    # --- Results (VVP)
    st.markdown("---")
    st.subheader("VVP Results")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Cost (€)", f"{total_cost:.2f}")
    with c2:
        st.metric("Cost per piece (€)", f"{cost_per_piece:.4f}")
    with c3:
        st.metric("Rounded Cost per piece (€)", f"{cost_per_piece_rounded:.2f}")

    # --- Breakdown
    with st.expander("Breakdown"):
        rows = {
            "Inbound Cost (€)": round(inbound_cost, 2),
            "Outbound Cost (€)": round(outbound_cost, 2),
            "Storage Cost (€)": round(storage_cost, 2),
            "Order Fixed Cost (€)": round(order_fee, 2),
            "Warehousing Total (1st leg) (€)": round(warehousing_total, 2),

            "Buying Transport Cost (€ total)": round(buying_transport_cost, 2),

            "Pallet Unit Cost (€/pallet)": round(pallet_unit_cost or 0.0, 2),
            "Pallets (#)": pallets,
            "Pallet Cost Total (€)": round(pallet_cost_total, 2),
        }

        if second_leg_breakdown:
            rows.update(second_leg_breakdown)

        rows.update({
            "TOTAL (€)": round(total_cost, 2),
            "Cost per piece (€)": round(cost_per_piece, 4),
        })
        st.write(rows)

    # --- Hand off to P&L
    st.markdown("---")
    final_calculator(pieces=pieces, vvp_cost_per_piece_rounded=cost_per_piece_rounded)

