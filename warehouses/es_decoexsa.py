# Spain / Decoexsa — first leg + optional second leg (with temperature-controlled toggle).
#
# First leg (toggle determines rate set):
# - Non temperature-controlled:
#     Inbound   : €2.90 / pallet
#     Outbound  : €2.90 / pallet
#     Storage   : €1.82 / pallet / week
# - Temperature-controlled:
#     Inbound   : €4.75 / pallet
#     Outbound  : €4.75 / pallet
#     Storage   : €4.20 / pallet / week
#
# Always add:
# - Order check  : €29.50 * 1.5 h (flat per order)
# - Buying transport cost (from app.py)
# - Optional pallet cost from app.py: (€/pallet) × pallets → INCLUDED in VVP if > 0
#
# Output template (same as others):
# - Total Cost (€)
# - Cost per piece (€)
# - Rounded Cost per piece (€)  [ceil to 2 decimals]

from __future__ import annotations
import math
import streamlit as st
from .final_calc import final_calculator
from .second_leg import second_leg_ui

# --- Fixed toggled rate sets (UPPERCASE for future admin override)
# Non temperature-controlled
NON_TC_INBOUND_PER_PALLET = 2.90
NON_TC_OUTBOUND_PER_PALLET = 2.90
NON_TC_STORAGE_PER_PALLET_PER_WEEK = 1.82

# Temperature-controlled
TC_INBOUND_PER_PALLET = 4.75
TC_OUTBOUND_PER_PALLET = 4.75
TC_STORAGE_PER_PALLET_PER_WEEK = 4.20

# Order check (always added)
ORDER_CHECK_HOURLY_EUR = 29.50
ORDER_CHECK_HOURS = 1.5


def compute_es_decoexsa(
    pieces: int,
    pallets: int,
    weeks: int,
    buying_transport_cost: float,
    pallet_unit_cost: float,
) -> None:
    """Render Spain / Decoexsa calculator and VVP results."""
    st.subheader("Spain / Decoexsa")

    # --- Warehouse-specific UI (checkbox)
    temperature_controlled = st.checkbox(
        "Temperature-controlled section?",
        value=False,
        key="es_decoexsa_tc",
        help="Tick if the order goes to the temperature-controlled area."
    )

    # --- Choose rate set
    if temperature_controlled:
        INBOUND_PER_PALLET = TC_INBOUND_PER_PALLET
        OUTBOUND_PER_PALLET = TC_OUTBOUND_PER_PALLET
        STORAGE_PER_PALLET_PER_WEEK = TC_STORAGE_PER_PALLET_PER_WEEK
    else:
        INBOUND_PER_PALLET = NON_TC_INBOUND_PER_PALLET
        OUTBOUND_PER_PALLET = NON_TC_OUTBOUND_PER_PALLET
        STORAGE_PER_PALLET_PER_WEEK = NON_TC_STORAGE_PER_PALLET_PER_WEEK

    # --- First-leg components
    inbound_cost = pallets * INBOUND_PER_PALLET
    outbound_cost = pallets * OUTBOUND_PER_PALLET
    storage_cost = pallets * weeks * STORAGE_PER_PALLET_PER_WEEK
    order_check_cost = ORDER_CHECK_HOURLY_EUR * ORDER_CHECK_HOURS

    # Optional pallet cost
    pallet_cost_total = (pallet_unit_cost or 0.0) * pallets if (pallet_unit_cost or 0) > 0 else 0.0

    warehousing_total = inbound_cost + outbound_cost + storage_cost + order_check_cost

    # --- Second leg (optional)
    second_leg_added_cost, second_leg_breakdown = second_leg_ui(
        primary_warehouse="Spain / Decoexsa",
        pallets=pallets,
    )

    # --- Totals for VVP
    base_total = (
        warehousing_total
        + buying_transport_cost
        + pallet_cost_total        # include optional pallet cost
    )
    total_cost = base_total + second_leg_added_cost

    cost_per_piece = (total_cost / pieces) if pieces else 0.0
    cost_per_piece_rounded = math.ceil(cost_per_piece * 100) / 100.0  # ceil to 2 decimals

    st.caption("You are entering inputs for **Spain / Decoexsa**")

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
            "Temperature controlled?": bool(temperature_controlled),

            # Inputs
            "Pieces (#)": pieces,
            "Pallets (#)": pallets,
            "Weeks in Storage": weeks,

            # Selected rates
            "Inbound (€/pallet)": round(INBOUND_PER_PALLET, 2),
            "Outbound (€/pallet)": round(OUTBOUND_PER_PALLET, 2),
            "Storage (€/pallet/week)": round(STORAGE_PER_PALLET_PER_WEEK, 2),

            # First-leg components
            "Inbound Cost (€)": round(inbound_cost, 2),
            "Outbound Cost (€)": round(outbound_cost, 2),
            "Storage Cost (€)": round(storage_cost, 2),

            # Order check
            "Order Check Hours": ORDER_CHECK_HOURS,
            "Order Check Hourly (€/h)": ORDER_CHECK_HOURLY_EUR,
            "Order Check Cost (€)": round(order_check_cost, 2),

            # Optional pallet cost
            "Pallet Unit Cost (€/pallet)": round(pallet_unit_cost or 0.0, 2),
            "Pallet Cost Total (€)": round(pallet_cost_total, 2),

            # Other
            "Buying Transport Cost (€ total)": round(buying_transport_cost or 0.0, 2),

            # Totals (1st leg)
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
