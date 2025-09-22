# warehouses/sk_arufel.py
import math
import streamlit as st
from .final_calc import final_calculator
from .second_leg import second_leg_ui  # <-- add this

def compute_sk_arufel(
    pieces: int,
    pallets: int,
    weeks: int,                    # kept for signature consistency (not used in cost)
    buying_transport_cost: float,
):
    """
    Slovakia / Arufel

    Fixed rates:
      - Warehouse fixed charge (per shipment): €360 (applies only if there is an inbound)
      - Labelling (if selected): €0.03 per piece (label + labelling total)
    """

    st.subheader("Slovakia / Arufel")

    # --- Fixed rates ---
    WH_FIXED_PER_SHIPMENT = 360.0
    LABELLING_PER_PIECE   = 0.03  # label + labelling total

    # --- Options ---
    do_labelling = st.checkbox("Labelling required?")

    # --- 1st-leg components ---
    warehouse_fixed = WH_FIXED_PER_SHIPMENT if (pallets > 0 and pieces > 0) else 0.0
    labelling_cost  = (LABELLING_PER_PIECE * pieces) if do_labelling else 0.0

    warehousing_total = warehouse_fixed  # no in/out/storage breakdown for this WH

    # ----------------------------
    # Second leg (optional)
    # ----------------------------
    second_leg_added_cost, second_leg_breakdown = second_leg_ui(
        primary_warehouse="Slovakia / Arufel",
        pallets=pallets,
    )

    # --- Totals for VVP ---
    base_total = warehousing_total + labelling_cost + buying_transport_cost
    total_cost = base_total + second_leg_added_cost

    cost_per_piece         = (total_cost / pieces) if pieces else 0.0
    cost_per_piece_rounded = math.ceil(cost_per_piece * 100) / 100.0  # round up to 2dp

    st.caption("You are entering inputs for **Slovakia / Arufel**")

    # --- Results (VVP) ---
    st.markdown("---")
    st.subheader("VVP Results")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Cost (€)", f"{total_cost:.2f}")
    with c2:
        st.metric("Cost per piece (€)", f"{cost_per_piece:.4f}")
    with c3:
        st.metric("Rounded Cost per piece (€)", f"{cost_per_piece_rounded:.2f}")

    # --- Breakdown (includes 2nd leg if used) ---
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
