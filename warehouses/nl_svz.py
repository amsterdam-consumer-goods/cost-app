# warehouses/nl_svz.py
import math
import streamlit as st
from .final_calc import final_calculator
from .second_leg import second_leg_ui   # <-- NEW

def compute_nl_svz(pieces: int, pallets: int, weeks: int,
                   buying_transport_cost: float, pallet_unit_cost: float):
    """
    Netherlands / SVZ
      - Inbound  : €2.75 / pallet
      - Outbound : €2.75 / pallet
      - Storage  : €1.36 / pallet / week
      - Shuttle  : €450 / transfer leg (WH→Lab or Lab→WH)
      - Label per piece     : €0.015
      - Labelling per piece : €0.045
    """
    st.subheader("Netherlands / SVZ")

    INBOUND_PER_PALLET  = 2.75
    OUTBOUND_PER_PALLET = 2.75
    STORAGE_PER_PALLET_PER_WEEK = 1.36
    SHUTTLE_PER_TRIP    = 450.0
    LABEL_PER_PIECE     = 0.015
    LABELLING_PER_PIECE = 0.045

    # ---- Warehousing (first leg) ----
    inbound_cost  = pallets * INBOUND_PER_PALLET
    outbound_cost = pallets * OUTBOUND_PER_PALLET
    storage_cost  = pallets * weeks * STORAGE_PER_PALLET_PER_WEEK
    warehousing_one_round = inbound_cost + outbound_cost + storage_cost

    # ---- Labelling flow (gated) ----
    st.markdown("### Labelling")
    labelling_required = st.checkbox("Labelling required?")
    wh_to_lab = lab_to_wh = False

    if labelling_required:
        st.subheader("Labelling Transfer")
        wh_to_lab = st.checkbox("Warehouse → Labelling")
        lab_to_wh = st.checkbox("Labelling → Warehouse")

        # Guard: labelling requires at least one transfer leg
        if labelling_required and not (wh_to_lab or lab_to_wh):
            st.info("Select at least one transfer leg (WH→Labelling and/or Labelling→WH).")


    transfer_cost = 0.0
    if labelling_required:
        if wh_to_lab: transfer_cost += SHUTTLE_PER_TRIP
        if lab_to_wh: transfer_cost += SHUTTLE_PER_TRIP

    extra_warehousing_on_return = warehousing_one_round if (labelling_required and lab_to_wh) else 0.0
    labelling_cost = ((LABEL_PER_PIECE + LABELLING_PER_PIECE) * pieces) if labelling_required else 0.0

    # ---- SECOND LEG UI & COST (before totals) ----
    second_leg_added_cost, second_leg_breakdown = second_leg_ui(  # <-- NEW
        primary_warehouse="Netherlands / SVZ",
        pallets=pallets,
    )

    # ---- Totals (VVP) ----
    warehousing_total = warehousing_one_round + extra_warehousing_on_return
    base_total = (
        warehousing_total
        + labelling_cost
        + transfer_cost
        + buying_transport_cost
    )
    total_cost = base_total + second_leg_added_cost  # varsa 2. bacak ekliyorsun zaten


    cost_per_piece = (total_cost / pieces) if pieces else 0.0
    cost_per_piece_rounded = math.ceil(cost_per_piece * 100) / 100.0

    st.caption("You are entering inputs for **Netherlands / SVZ**")

    # ---- Results ----
    st.markdown("---")
    st.subheader("VVP Results")
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Total Cost (€)", f"{total_cost:.2f}")
    with c2: st.metric("Cost per piece (€)", f"{cost_per_piece:.4f}")
    with c3: st.metric("Rounded Cost per piece (€)", f"{cost_per_piece_rounded:.2f}")

    with st.expander("Breakdown"):
        rows = {
            "Inbound Cost (€)": round(inbound_cost, 2),
            "Outbound Cost (€)": round(outbound_cost, 2),
            "Storage Cost (€)": round(storage_cost, 2),
            "Extra Warehousing on Return (€)": round(extra_warehousing_on_return, 2),
            "Labelling Required": labelling_required,
            "WH → Labelling": wh_to_lab if labelling_required else None,
            "Labelling → WH": lab_to_wh if labelling_required else None,
            "Labelling Cost (€)": round(labelling_cost, 2),
            "Labelling Transfer Cost (€)": round(transfer_cost, 2),
            "Buying Transport Cost (€)": round(buying_transport_cost, 2),
        }
        if second_leg_breakdown:                          # <-- NEW
            rows.update({"--- 2nd Leg ---": ""})
            rows.update(second_leg_breakdown)
        rows.update({
            "Warehousing Total (1st leg) (€)": round(warehousing_total, 2),
            "TOTAL (€)": round(total_cost, 2),
            "Cost per piece (€)": round(cost_per_piece, 4),
        })
        st.write(rows)

    st.markdown("---")
    final_calculator(pieces=pieces, vvp_cost_per_piece_rounded=cost_per_piece_rounded)
