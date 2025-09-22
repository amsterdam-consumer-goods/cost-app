"""
Internal transfer (2nd leg) calculator

What this does
--------------
- Provides a compact Streamlit UI to optionally add a “second leg”
  (transfer from the primary warehouse to another warehouse).
- Uses simplified warehouse rate sheets (inbound, outbound, storage, fixed fees).
- Does not include labelling costs (handled only in first leg).
- Returns both the additional cost and a breakdown dictionary.
"""

from __future__ import annotations

import streamlit as st


# -------------------------------------------------------------------------
# Rate sheet for all supported warehouses
# (warehousing-only, no labelling costs here)
# -------------------------------------------------------------------------
RATES: dict[str, dict[str, float]] = {
    "Netherlands / SVZ":     {"in": 2.75, "out": 2.75, "storage": 1.36, "fixed_per_order": 0.0},
    "Germany / Offergeld":   {"in": 3.90, "out": 3.12, "storage": 1.40, "fixed_per_order": 0.0},
    "France / Coquelle":     {"in": 4.90, "out": 4.90, "storage": 4.00, "fixed_per_order": 5.50},   # admin fee
    "Slovakia / Arufel":     {"in": 0.0,  "out": 0.0,  "storage": 0.0,  "fixed_per_order": 360.0},  # flat per shipment
    "Netherlands / Mentrex": {"in": 5.10, "out": 5.10, "storage": 1.40, "fixed_per_order": 50.0},   # order fee
    "Romania / Giurgiu":     {"in": 2.30, "out": 2.30, "storage": 1.40, "fixed_per_order": 0.0},
}


def _warehousing_cost(wh: str, pallets: int, weeks: int) -> float:
    """
    Compute inbound + outbound + storage + fixed fees for a warehouse.

    Args:
        wh: Warehouse name (must exist in RATES).
        pallets: Number of pallets stored/transferred.
        weeks: Weeks spent in the warehouse.

    Returns:
        Total cost in EUR (float). Returns 0 if warehouse not in RATES.
    """
    r = RATES.get(wh)
    if not r:
        return 0.0

    inbound = pallets * r["in"]
    outbound = pallets * r["out"]
    storage = pallets * weeks * r["storage"]
    fixed = r.get("fixed_per_order", 0.0)

    return inbound + outbound + storage + fixed


def second_leg_ui(primary_warehouse: str, pallets: int) -> tuple[float, dict]:
    """
    Render a Streamlit UI to optionally add a second leg (internal transfer).

    Args:
        primary_warehouse: Warehouse chosen for the first leg.
        pallets: Number of pallets transferred.

    Returns:
        (added_cost_eur, breakdown_dict)
        - added_cost_eur: total extra cost for this leg
        - breakdown_dict: detailed breakdown (empty if disabled)
    """
    st.markdown("### Internal Transfer (2nd leg) — optional")

    enable = st.checkbox("Add a 2nd Warehouse Leg?")
    if not enable:
        return 0.0, {}
    
    # -------------------------------------------------------------------------
    # Only allow warehouses other than the primary one
    # -------------------------------------------------------------------------
    options = [w for w in RATES.keys() if w != primary_warehouse]
    second_wh = st.selectbox("2nd Warehouse", ["-- Select --"] + options, index=0)

    # -------------------------------------------------------------------------
    # Inputs for 2nd warehouse
    # -------------------------------------------------------------------------
    c1, c2 = st.columns(2)
    with c1:
        weeks2 = st.number_input(
            "Weeks in 2nd Warehouse",
            min_value=0,
            step=1,
            format="%d",
        )
    with c2:
        inter_transport = st.number_input(
            "Inter-Warehouse Transport (€ TOTAL)",
            min_value=0.0,
            step=1.0,
            format="%.2f",
        )

    if second_wh == "-- Select --":
        return 0.0, {}

    # -------------------------------------------------------------------------
    # Compute costs
    # -------------------------------------------------------------------------
    wh_cost = _warehousing_cost(second_wh, pallets, weeks2)
    added_total = inter_transport + wh_cost
    # -------------------------------------------------------------------------
    # Build breakdown dict
    # -------------------------------------------------------------------------
    breakdown = {
        "Second Warehouse": second_wh,
        "Pallets (#)": pallets,
        "Weeks at 2nd WH": weeks2,
        "Inter-Warehouse Transport (€)": round(inter_transport, 2),
        "2nd WH Warehousing (€)": round(wh_cost, 2),
        "2nd Leg Total Add-On (€)": round(added_total, 2),
    }

    return added_total, breakdown
