"""
Warehouse calculator: Slovakia / Arufel

What this does
--------------
- Applies a per-shipment fixed warehouse charge (if there is a real inbound).
- Optionally applies labelling cost per piece.
- Optionally adds a “second leg” (internal transfer to another warehouse) cost.
- Produces VVP totals and a readable cost breakdown.
- Hands off the rounded VVP cost per piece to the final P&L calculator.
"""

from __future__ import annotations

import math
import streamlit as st

from .final_calc import final_calculator
from .second_leg import second_leg_ui


def compute_sk_arufel(
    pieces: int,
    pallets: int,
    weeks: int,  # kept for signature consistency (not used by this warehouse)
    buying_transport_cost: float,
) -> None:
    """Render the Slovakia / Arufel calculator and results."""
    st.subheader("Slovakia / Arufel")

    # -------------------------------------------------------------------------
    # Fixed rates
    # -------------------------------------------------------------------------
    WH_FIXED_PER_SHIPMENT = 360.0  # applies once when there is a real inbound
    LABELLING_PER_PIECE = 0.03     # label + labelling total per piece

    # -------------------------------------------------------------------------
    # Options
    # -------------------------------------------------------------------------
    do_labelling = st.checkbox("Labelling required?")

    # -------------------------------------------------------------------------
    # First-leg components (Arufel)
    # -------------------------------------------------------------------------
    # Apply warehouse fixed charge only if there is a real inbound (pallets & pieces)
    warehouse_fixed = WH_FIXED_PER_SHIPMENT if (pallets > 0 and pieces > 0) else 0.0

    # Labelling is an add-on per piece
    labelling_cost = LABELLING_PER_PIECE * pieces if do_labelling else 0.0

    # For this warehouse we do not have in/out/storage breakdown
    warehousing_total = warehouse_fixed

    # -------------------------------------------------------------------------
    # Second leg (optional internal transfer) – shown uniformly across warehouses
    # -------------------------------------------------------------------------
    second_leg_added_cost, second_leg_breakdown = second_leg_ui(
        primary_warehouse="Slovakia / Arufel",
        pallets=pallets,
    )

    # -------------------------------------------------------------------------
    # Totals for VVP
    # -------------------------------------------------------------------------
    base_total = warehousing_total + labelling_cost + buying_transport_cost
    total_cost = base_total + second_leg_added_cost

    cost_per_piece = (total_cost / pieces) if pieces else 0.0
    cost_per_piece_rounded = math.ceil(cost_per_piece * 100) / 100.0  # round up to 2 dp

    st.caption("You are entering inputs for **Slovakia / Arufel**")

    # -------------------------------------------------------------------------
    # Results (VVP)
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("VVP Results")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Cost (€)", f"{total_cost:.2f}")
    with c2:
        st.metric("Cost per piece (€)", f"{cost_per_piece:.4f}")
    with c3:
        st.metric("Rounded Cost per piece (€)", f"{cost_per_piece_rounded:.2f}")

    # -------------------------------------------------------------------------
    # Breakdown (includes second leg if used)
    # -------------------------------------------------------------------------
    with st.expander("Breakdown"):
        rows = {
            "Warehouse Fixed Cost (€)": round(warehouse_fixed, 2),
            "Labelling applied?": do_labelling,
            "Labelling Cost (€)": round(labelling_cost, 2),
            "Buying Transport Cost (€ TOTAL)": round(buying_transport_cost, 2),
            "Warehousing Total (1st leg) (€)": round(warehousing_total, 2),
        }
        if second_leg_breakdown:
            rows.update({"—— Second Leg ——": ""})
            rows.update(second_leg_breakdown)

        rows.update(
            {
                "TOTAL (€)": round(total_cost, 2),
                "Cost per piece (€)": round(cost_per_piece, 4),
            }
        )
        st.write(rows)

    # -------------------------------------------------------------------------
    # Hand off to P&L
    # -------------------------------------------------------------------------
    st.markdown("---")
    final_calculator(
        pieces=pieces,
        vvp_cost_per_piece_rounded=cost_per_piece_rounded,
    )
