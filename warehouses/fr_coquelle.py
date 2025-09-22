# warehouses/fr_coquelle.py
import math
import streamlit as st
from .final_calc import final_calculator
from .second_leg import second_leg_ui   # <-- second-leg picker & cost

def compute_fr_coquelle(
    pieces: int,
    pallets: int,
    weeks: int,
    buying_transport_cost: float,
):
    """
    France / Coquelle

    Inputs:
      - buying_transport_cost (€ total)
      - pieces (qty)
      - pallets (#)
      - weeks in storage

    Fixed rates:
      - Inbound             : 5.20 € / pallet
      - Outbound            : 5.40 € / pallet
      - Storage (weekly)    : 4.00 € / pallet / week
      - Administrative cost : 5.50 € per inbound (flat per order, only if pallets > 0 and pieces > 0)
    """

    st.subheader("France / Coquelle")

    # --- Fixed rates ---
    INBOUND_PER_PALLET          = 5.20
    OUTBOUND_PER_PALLET         = 5.40
    STORAGE_PER_PALLET_PER_WEEK = 4.00
    ADMIN_PER_INBOUND_FLAT      = 5.50

    # --- Warehousing components (1st leg) ---
    inbound_cost   = pallets * INBOUND_PER_PALLET
    outbound_cost  = pallets * OUTBOUND_PER_PALLET
    storage_cost   = pallets * weeks * STORAGE_PER_PALLET_PER_WEEK
    admin_cost     = ADMIN_PER_INBOUND_FLAT if (pallets > 0 and pieces > 0) else 0.0

    warehousing_total = inbound_cost + outbound_cost + storage_cost + admin_cost

    # ----------------------------
    # Second leg (optional)
    # ----------------------------
    # Renders a small UI section where the user can choose a second warehouse and
    # its simple cost model. Returns (added_cost, breakdown_dict).
    second_leg_added_cost, second_leg_breakdown = second_leg_ui(
        primary_warehouse="France / Coquelle",
        pallets=pallets,
    )

    # --- Totals for VVP ---
    base_total = warehousing_total + buying_transport_cost
    total_cost = base_total + second_leg_added_cost

    cost_per_piece         = (total_cost / pieces) if pieces else 0.0
    cost_per_piece_rounded = math.ceil(cost_per_piece * 100) / 100.0  # round up to 2dp

    st.caption("You are entering inputs for **France / Coquelle**")

    # --- Results (VVP) ---
    st.markdown("---")
    st.subheader("VVP Results")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Cost (€)", f"{total_cost:.2f}")
    with c2:
        st.metric("Cost per Piece (€)", f"{cost_per_piece:.4f}")
    with c3:
        st.metric("Rounded Cost per Piece (€)", f"{cost_per_piece_rounded:.2f}")

    # --- Breakdown (includes second leg if used) ---
    with st.expander("Breakdown"):
        rows = {
            "Inbound Cost (€)": round(inbound_cost, 2),
            "Outbound Cost (€)": round(outbound_cost, 2),
            "Storage Cost (€)": round(storage_cost, 2),
            "Administrative Cost (€)": round(admin_cost, 2),
            "Warehousing Total (1st leg) (€)": round(warehousing_total, 2),
            "Buying Transport Cost (€ TOTAL)": round(buying_transport_cost, 2),
        }
        # If user picked a second leg, show its breakdown too
        if second_leg_breakdown:
            rows.update({"—— Second Leg ——": ""})
            rows.update(second_leg_breakdown)

        rows.update({
            "TOTAL (€)": round(total_cost, 2),
            "Cost per piece (€)": round(cost_per_piece, 4),
        })
        st.write(rows)

    # --- Hand off to P&L ---
    st.markdown("---")
    final_calculator(
        pieces=pieces,
        vvp_cost_per_piece_rounded=cost_per_piece_rounded
    )
