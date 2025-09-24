"""
Slovakia / Arufel — first leg + optional second leg.

First leg:
- Fixed per-shipment warehouse charge: €360 (applies only if inbound exists)
- Optional labelling per piece: €0.03
- Optional pallet cost from app.py: (€/pallet) × pallets → INCLUDED in VVP if > 0

Second leg (optional):
- Calculated via warehouses/second_leg.py against the target warehouse rates.
- Returned amount is added to VVP when enabled in the UI.
"""

from __future__ import annotations
import math
import streamlit as st
from .final_calc import final_calculator
from .second_leg import second_leg_ui


def compute_sk_arufel(
    pieces: int,
    pallets: int,
    weeks: int,                 # kept for signature consistency; not used by Arufel
    buying_transport_cost: float,
    pallet_unit_cost: float,    # optional €/pallet from app.py (included if > 0)
) -> None:
    """Render Slovakia / Arufel calculator and VVP results."""
    st.subheader("Slovakia / Arufel")

    # --- Fixed rates (first leg)
    WH_FIXED_PER_SHIPMENT = 360.0
    LABELLING_PER_PIECE = 0.03

    # --- Options
    do_labelling = st.checkbox("Labelling required?")

    # --- First-leg components
    warehouse_fixed = WH_FIXED_PER_SHIPMENT if (pallets > 0 and pieces > 0) else 0.0
    labelling_cost = (LABELLING_PER_PIECE * pieces) if do_labelling else 0.0

    # Pallet cost (optional, included if provided)
    pallet_cost_total = (pallet_unit_cost or 0.0) * pallets if (pallet_unit_cost or 0) > 0 else 0.0

    warehousing_total = warehouse_fixed  # Arufel has no in/out/storage split

    # --- Second leg (optional)
    second_leg_added_cost, second_leg_breakdown = second_leg_ui(
        primary_warehouse="Slovakia / Arufel",
        pallets=pallets,
        # pieces not used by second_leg in current design
    )

    # --- Totals for VVP
    base_total = (
        warehousing_total
        + labelling_cost
        + buying_transport_cost
        + pallet_cost_total            # <-- include optional pallet cost in VVP
    )
    total_cost = base_total + second_leg_added_cost

    cost_per_piece = (total_cost / pieces) if pieces else 0.0
    cost_per_piece_rounded = math.ceil(cost_per_piece * 100) / 100.0

    st.caption("You are entering inputs for **Slovakia / Arufel**")

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
            # Inputs / first leg
            "Warehouse Fixed Cost (€)": round(warehouse_fixed, 2),
            "Labelling applied?": do_labelling,
            "Labelling Cost (€)": round(labelling_cost, 2),
            "Buying Transport Cost (€ total)": round(buying_transport_cost, 2),

            # Pallet cost visibility + inclusion
            "Pallet Unit Cost (€/pallet)": round(pallet_unit_cost or 0.0, 2),
            "Pallets (#)": pallets,
            "Pallet Cost Total (€)": round(pallet_cost_total, 2),
            "Warehousing Total (1st leg) (€)": round(warehousing_total, 2),
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
