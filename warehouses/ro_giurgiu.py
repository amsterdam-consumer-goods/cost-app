# warehouses/ro_giurgiu.py  (or ro_romania.py if that's your filename)
import math
import streamlit as st
from .final_calc import final_calculator
from .second_leg import second_leg_ui   # <-- add this import

def compute_ro_giurgiu(
    pieces: int,
    pallets: int,
    weeks: int,
    buying_transport_cost: float,
):
    """
    Romania / Giurgiu

    Inputs:
      - buying_transport_cost (€ total)
      - pieces (qty)
      - pallets (#)
      - weeks in storage

    Fixed rates:
      - Inbound  : €2.30 / pallet
      - Outbound : €2.30 / pallet
      - Storage  : €1.40 / pallet / week
      - Labelling (optional):
          * Label      : €0.015 / piece
          * Labelling  : €0.033 / piece
    """

    st.subheader("Romania / Giurgiu")

    # --- Fixed rates ---
    INBOUND_PER_PALLET          = 2.30
    OUTBOUND_PER_PALLET         = 2.30
    STORAGE_PER_PALLET_PER_WEEK = 1.40
    LABEL_PER_PIECE             = 0.015
    LABELLING_PER_PIECE         = 0.033

    # --- Optional labelling ---
    do_labelling = st.checkbox("Labelling required?")

    # --- 1st-leg warehousing components ---
    inbound_cost   = pallets * INBOUND_PER_PALLET
    outbound_cost  = pallets * OUTBOUND_PER_PALLET
    storage_cost   = pallets * weeks * STORAGE_PER_PALLET_PER_WEEK

    # Labelling cost (if any)
    labelling_cost = ((LABEL_PER_PIECE + LABELLING_PER_PIECE) * pieces) if do_labelling else 0.0

    warehousing_total = inbound_cost + outbound_cost + storage_cost

    # ----------------------------
    # Second leg (optional)
    # ----------------------------
    second_leg_added_cost, second_leg_breakdown = second_leg_ui(
        primary_warehouse="Romania / Giurgiu",
        pallets=pallets,
    )

    # --- Totals for VVP ---
    base_total = warehousing_total + labelling_cost + buying_transport_cost
    total_cost = base_total + second_leg_added_cost

    cost_per_piece         = (total_cost / pieces) if pieces else 0.0
    cost_per_piece_rounded = math.ceil(cost_per_piece * 100) / 100.0  # round up to 2dp

    st.caption("You are entering inputs for **Romania / Giurgiu**")

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
            "Inbound Cost (€)": round(inbound_cost, 2),
            "Outbound Cost (€)": round(outbound_cost, 2),
            "Storage Cost (€)": round(storage_cost, 2),
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
