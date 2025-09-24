"""
Romania / Giurgiu — first leg + optional second leg.

First leg:
- Inbound  : €2.30 / pallet
- Outbound : €2.30 / pallet
- Storage  : €1.40 / pallet / week
- Optional labelling per piece:
    * Label      : €0.015 / piece
    * Labelling  : €0.033 / piece
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


def compute_ro_giurgiu(
    pieces: int,
    pallets: int,
    weeks: int,
    buying_transport_cost: float,
    pallet_unit_cost: float,
) -> None:
    """Render Romania / Giurgiu calculator and VVP results."""
    st.subheader("Romania / Giurgiu")

    # --- Fixed rates (first leg)
    INBOUND_PER_PALLET = 2.30
    OUTBOUND_PER_PALLET = 2.30
    STORAGE_PER_PALLET_PER_WEEK = 1.40
    LABEL_PER_PIECE = 0.015
    LABELLING_PER_PIECE = 0.033

    # --- Options
    do_labelling = st.checkbox("Labelling required?")

    # --- First-leg components
    inbound_cost = pallets * INBOUND_PER_PALLET
    outbound_cost = pallets * OUTBOUND_PER_PALLET
    storage_cost = pallets * weeks * STORAGE_PER_PALLET_PER_WEEK

    # Labelling (optional)
    labelling_cost = ((LABEL_PER_PIECE + LABELLING_PER_PIECE) * pieces) if do_labelling else 0.0

    # Pallet cost (optional, included if provided)
    pallet_cost_total = (pallet_unit_cost or 0.0) * pallets if (pallet_unit_cost or 0) > 0 else 0.0

    warehousing_total = inbound_cost + outbound_cost + storage_cost

    # --- Second leg (optional)
    second_leg_added_cost, second_leg_breakdown = second_leg_ui(
        primary_warehouse="Romania / Giurgiu",
        pallets=pallets,
        # pieces not used by second_leg in current design
    )

    # --- Totals for VVP
    base_total = (
        warehousing_total
        + labelling_cost
        + buying_transport_cost
        + pallet_cost_total            # include optional pallet cost
    )
    total_cost = base_total + second_leg_added_cost

    cost_per_piece = (total_cost / pieces) if pieces else 0.0
    cost_per_piece_rounded = math.ceil(cost_per_piece * 100) / 100.0  # round up to 2 dp

    st.caption("You are entering inputs for **Romania / Giurgiu**")

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
            "Labelling applied?": do_labelling,
            "Labelling Cost (€)": round(labelling_cost, 2),
            "Buying Transport Cost (€ total)": round(buying_transport_cost, 2),
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

