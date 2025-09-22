# warehouses/second_leg.py
import streamlit as st

# Minimal warehouse rate sheet for warehousing-only legs (no labelling here).
# If a warehouse has an extra per-order fixed fee, include it as "fixed_per_order".
RATES = {
    "Netherlands / SVZ":      {"in": 2.75, "out": 2.75, "storage": 1.36, "fixed_per_order": 0.0},
    "Germany / Offergeld":    {"in": 3.90, "out": 3.12, "storage": 1.40, "fixed_per_order": 0.0},
    "France / Coquelle":      {"in": 4.90, "out": 4.90, "storage": 4.00, "fixed_per_order": 5.50},  # admin per inbound
    "Slovakia / Arufel":      {"in": 0.0,  "out": 0.0,  "storage": 0.0,  "fixed_per_order": 360.0}, # fixed warehousing
    "Netherlands / Mentrex":  {"in": 5.10, "out": 5.10, "storage": 1.40, "fixed_per_order": 50.0},
    "Romania / Giurgiu":      {"in": 2.30, "out": 2.30, "storage": 1.40, "fixed_per_order": 0.0},
}

def _warehousing_cost(wh: str, pallets: int, weeks: int) -> float:
    """Inbound + Outbound + Storage + Fixed (no labelling)."""
    r = RATES.get(wh)
    if not r:
        return 0.0
    inbound  = pallets * r["in"]
    outbound = pallets * r["out"]
    storage  = pallets * weeks * r["storage"]
    fixed    = r.get("fixed_per_order", 0.0)
    return inbound + outbound + storage + fixed

def second_leg_ui(primary_warehouse: str, pallets: int) -> tuple[float, dict]:
    """
    Renders a compact 'Internal transfer (2nd leg)' UI.
    Returns (added_cost_eur, breakdown_dict).

    If the user doesn't enable it, returns (0.0, {}).
    """
    st.markdown("### Internal Transfer (2nd leg) — optional")
    enable = st.checkbox("Add a 2nd Warehouse Leg?")

    if not enable:
        return 0.0, {}

    # Only allow warehouses other than the first leg
    options = [w for w in RATES.keys() if w != primary_warehouse]
    second_wh = st.selectbox("2nd Warehouse", ["-- Select --"] + options, index=0)

    c1, c2 = st.columns(2)
    with c1:
        weeks2 = st.number_input("Weeks in 2nd Warehouse", min_value=0, step=1, format="%d")
    with c2:
        inter_transport = st.number_input("Inter-Warehouse Transport (€ TOTAL)", min_value=0.0, step=1.0, format="%.2f")

    if second_wh == "-- Select --":
        return 0.0, {}

    wh_cost = _warehousing_cost(second_wh, pallets, weeks2)
    added_total = inter_transport + wh_cost

    breakdown = {
        "Second Warehouse": second_wh,
        "Pallets (#)": pallets,
        "Weeks at 2nd WH": weeks2,
        "Inter-Warehouse Transport (€)": round(inter_transport, 2),
        "2nd WH Warehousing (€)": round(wh_cost, 2),
        "2nd Leg Total Add-On (€)": round(added_total, 2),
    }
    return added_total, breakdown
