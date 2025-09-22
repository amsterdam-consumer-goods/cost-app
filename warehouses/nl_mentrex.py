import math
import streamlit as st
from .final_calc import final_calculator
from .second_leg import second_leg_ui


def compute_nl_mentrex(
    pieces: int,
    pallets: int,
    weeks: int,
    buying_transport_cost: float,
):
    """
    Netherlands / Mentrex — first leg.
    - Warehousing (in/out/storage) + order fixed fee when inbound happens.
    - Optional 2nd leg, fully added to VVP.
    """

    st.subheader("Netherlands / Mentrex")

    INBOUND_PER_PALLET  = 5.10
    OUTBOUND_PER_PALLET = 5.10
    STORAGE_PER_PALLET_PER_WEEK = 1.40
    ORDER_FIXED_FEE = 50.0

    inbound_cost  = pallets * INBOUND_PER_PALLET
    outbound_cost = pallets * OUTBOUND_PER_PALLET
    storage_cost  = pallets * weeks * STORAGE_PER_PALLET_PER_WEEK
    order_fee     = ORDER_FIXED_FEE if (pallets > 0 and pieces > 0) else 0.0

    warehousing_total = inbound_cost + outbound_cost + storage_cost + order_fee

    # 2nd leg
    second_leg_added_cost, second_leg_breakdown = second_leg_ui(
        primary_warehouse="Netherlands / Mentrex",
        pieces=pieces,
        pallets=pallets,
    )

    base_total = warehousing_total + buying_transport_cost
    total_cost = base_total + second_leg_added_cost

    cost_per_piece = (total_cost / pieces) if pieces else 0.0
    cost_per_piece_rounded = math.ceil(cost_per_piece * 100) / 100.0

    st.caption("You are entering inputs for **Netherlands / Mentrex**")

    st.markdown("---")
    st.subheader("VVP Results")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Cost (€)", f"{total_cost:.2f}")
    with c2:
        st.metric("Cost per Piece (€)", f"{cost_per_piece:.4f}")
    with c3:
        st.metric("Rounded Cost per Piece (€)", f"{cost_per_piece_rounded:.2f}")

    with st.expander("Breakdown"):
        rows = {
            "Inbound Cost (€)": round(inbound_cost, 2),
            "Outbound Cost (€)": round(outbound_cost, 2),
            "Storage Cost (€)": round(storage_cost, 2),
            "Order Fixed Cost (€)": round(order_fee, 2),
            "Buying Transport Cost (€ total)": round(buying_transport_cost, 2),
            "Warehousing Total (1st leg) (€)": round(warehousing_total, 2),
        }
        if second_leg_breakdown:
            rows.update(second_leg_breakdown)
        rows.update({
            "TOTAL (€)": round(total_cost, 2),
            "Cost per piece (€)": round(cost_per_piece, 4),
        })
        st.write(rows)

    st.markdown("---")
    final_calculator(pieces=pieces, vvp_cost_per_piece_rounded=cost_per_piece_rounded)
