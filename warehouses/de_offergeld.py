# warehouses/ger_offergeld.py
import math
import streamlit as st
from .final_calc import final_calculator
from .second_leg import second_leg_ui   # <-- NEW (second-leg hook)


def compute_de_offergeld(pieces: int, pallets: int, weeks: int,
                   buying_transport_cost: float, pallet_unit_cost: float):
    """
    Germany / Offergeld

    Inputs:
      - buying_transport_cost (€ total)
      - pieces (qty)
      - pallets (#)
      - weeks in storage

    Fixed rates:
      - Inbound  : 3.90 € / pallet
      - Outbound : 3.12 € / pallet
      - Storage  : 1.40 € / pallet / week
      - Optional labelling (per piece):
          * Label      : 0.015 €
          * Labelling  : 0.035 €
    """

    st.subheader("Germany / Offergeld")

    # --- Options ---
    st.markdown("### Labelling")
    do_labelling = st.checkbox("Labelling required?")

    # --- Fixed rates ---
    INBOUND_PER_PALLET   = 3.90
    OUTBOUND_PER_PALLET  = 3.12
    STORAGE_PER_PALLET_W = 1.40

    LABEL_PER_PIECE      = 0.015
    LABELLING_PER_PIECE  = 0.035

    # --- Warehousing (1st leg) ---
    inbound_cost   = pallets * INBOUND_PER_PALLET
    outbound_cost  = pallets * OUTBOUND_PER_PALLET
    storage_cost   = pallets * weeks * STORAGE_PER_PALLET_W
    warehousing_total = inbound_cost + outbound_cost + storage_cost

    # --- Labelling (optional) ---
    if do_labelling:
        label_cost_per_order     = pieces * LABEL_PER_PIECE
        labelling_cost_per_order = pieces * LABELLING_PER_PIECE
        labelling_total          = label_cost_per_order + labelling_cost_per_order
    else:
        label_cost_per_order     = 0.0
        labelling_cost_per_order = 0.0
        labelling_total          = 0.0

    # ===============================
    # SECOND LEG UI + COST (optional)
    # ===============================
    second_leg_added_cost, second_leg_breakdown = second_leg_ui(
        primary_warehouse="Germany / Offergeld",
        pallets=pallets,
    )

    # --- Totals (VVP) ---
    base_total = warehousing_total + labelling_total + buying_transport_cost
    total_cost = base_total + second_leg_added_cost    # <-- add 2nd leg if any

    cost_per_piece = (total_cost / pieces) if pieces else 0.0
    cost_per_piece_rounded = math.ceil(cost_per_piece * 100) / 100.0  # round up to 2dp

    st.caption("You are entering inputs for **Germany / Offergeld**")

    # --- Results ---
    st.markdown("---")
    st.subheader("VVP Results")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Cost (€)", f"{total_cost:.2f}")
    with c2:
        st.metric("Cost per Piece (€)", f"{cost_per_piece:.4f}")
    with c3:
        st.metric("Rounded Cost per Piece (€)", f"{cost_per_piece_rounded:.2f}")

    # --- Breakdown ---
    with st.expander("Breakdown"):
        rows = {
            # 1st leg
            "Inbound Cost (€)": round(inbound_cost, 2),
            "Outbound Cost (€)": round(outbound_cost, 2),
            "Storage Cost (€)": round(storage_cost, 2),
            "Warehousing Total (1st leg) (€)": round(warehousing_total, 2),

            # labelling
            "Labelling applied?": do_labelling,
            "Label Cost (€)": round(label_cost_per_order, 2),
            "Labelling Cost (€)": round(labelling_cost_per_order, 2),
            "Labelling Total (€)": round(labelling_total, 2),

            # transport
            "Buying Transport Cost (€ TOTAL)": round(buying_transport_cost, 2),
        }

        # append second-leg details if used
        if second_leg_breakdown:
            rows.update({"—— Second Leg ——": ""})
            rows.update(second_leg_breakdown)

        # totals
        rows.update({
            "TOTAL (€)": round(total_cost, 2),
            "Cost per piece (€)": round(cost_per_piece, 4),
        })

        st.write(rows)

    # --- Hand off to the Final Calculator (P&L) ---
    st.markdown("---")
    final_calculator(
        pieces=pieces,
        vvp_cost_per_piece_rounded=cost_per_piece_rounded
    )
