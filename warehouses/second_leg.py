"""
Second-leg (internal transfer) UI and calculation.

Flow
----
- User enables "Second leg".
- Selects the target warehouse (where the goods will be transferred to).
- Inputs:
    * Second-leg weeks in storage (at the target warehouse)
    * Second-leg transport cost (total € for moving to target warehouse)
- The second-leg warehousing cost is computed from the TARGET warehouse rates:
    inbound €/pallet, outbound €/pallet, storage €/pallet/week, optional order fee.
  For Slovakia / Arufel, second leg is a fixed €360 per order (no in/out/storage).
- Return the amount to add into VVP (if enabled) and a transparent breakdown.

API
---
second_leg_ui(primary_warehouse: str, pallets: int, pieces: int | None = None)
    -> tuple[float, dict]
"""

from __future__ import annotations
from typing import Optional, TypedDict
import streamlit as st


class WhRates(TypedDict, total=False):
    name: str
    inbound_per_pallet: float       # €/pallet
    outbound_per_pallet: float      # €/pallet
    storage_per_pallet_per_week: float  # €/pallet/week
    order_fee: float                # €/order (optional)
    fixed_per_order: float          # for flat pricing (e.g., Slovakia / Arufel)


# Target-warehouse rate table (as given)
TARGET_WAREHOUSE_RATES: dict[str, WhRates] = {
    "Slovakia / Arufel": {
        "name": "Slovakia / Arufel",
        "fixed_per_order": 360.0,  # per 1 order fixed price of 360
    },
    "Romania / Giurgiu": {
        "name": "Romania / Giurgiu",
        "inbound_per_pallet": 2.30,
        "outbound_per_pallet": 2.30,
        "storage_per_pallet_per_week": 1.40,
    },
    "Netherlands / SVZ": {
        "name": "Netherlands / SVZ",
        "inbound_per_pallet": 2.75,
        "outbound_per_pallet": 2.75,
        "storage_per_pallet_per_week": 1.36,
    },
    "Netherlands / Mentrex": {
        "name": "Netherlands / Mentrex",
        "inbound_per_pallet": 5.10,
        "outbound_per_pallet": 5.10,
        "storage_per_pallet_per_week": 1.40,
    },
    "France / Coquelle": {
        "name": "France / Coquelle",
        "inbound_per_pallet": 5.20,
        "outbound_per_pallet": 5.40,
        "storage_per_pallet_per_week": 4.00,
        "order_fee": 5.50,
    },
    "Germany / Offergeld": {
        "name": "Germany / Offergeld",
        "inbound_per_pallet": 3.30,
        "outbound_per_pallet": 3.12,
        "storage_per_pallet_per_week": 1.40,
    },
}


def _compute_second_leg_cost(
    target_wh: str,
    pallets: int,
    weeks_second_leg: int,
    transport_cost_second_leg: float,
) -> tuple[float, dict]:
    """Compute the second-leg cost based on the target warehouse's rates."""
    rates = TARGET_WAREHOUSE_RATES[target_wh]
    breakdown: dict[str, object] = {
        "—— Second Leg ——": "",
        "Target Warehouse": target_wh,
    }

    if "fixed_per_order" in rates:
        # Slovakia / Arufel: flat per order
        fixed = float(rates["fixed_per_order"])
        subtotal = fixed + float(transport_cost_second_leg)
        breakdown.update({
            "Pricing Model": "Fixed per order",
            "Fixed per order (€)": round(fixed, 2),
            "Second-leg Transport (€)": round(transport_cost_second_leg, 2),
            "Second-leg Subtotal (€)": round(subtotal, 2),
        })
        return subtotal, breakdown

    # Pallet/Week-based model
    in_cost = pallets * float(rates.get("inbound_per_pallet", 0.0))
    out_cost = pallets * float(rates.get("outbound_per_pallet", 0.0))
    storage_rate = float(rates.get("storage_per_pallet_per_week", 0.0))
    storage_cost = pallets * weeks_second_leg * storage_rate
    order_fee = float(rates.get("order_fee", 0.0))
    subtotal = in_cost + out_cost + storage_cost + order_fee + float(transport_cost_second_leg)

    breakdown.update({
        "Pricing Model": "Inbound/Outbound/Storage",
        "Inbound (€)": round(in_cost, 2),
        "Outbound (€)": round(out_cost, 2),
        "Storage (€)": round(storage_cost, 2),
        "Order Fee (€)": round(order_fee, 2),
        "Second-leg Transport (€)": round(transport_cost_second_leg, 2),
        "Second-leg Subtotal (€)": round(subtotal, 2),
    })
    return subtotal, breakdown


def second_leg_ui(
    primary_warehouse: str,
    pallets: int,
    pieces: Optional[int] = None,  # kept for signature compatibility; not used here
) -> tuple[float, dict]:
    """Render second-leg UI and return (cost_to_add_into_vvp, breakdown_dict)."""
    with st.expander("Second Leg (optional)"):
        enabled = st.checkbox("Enable second leg")
        if not enabled:
            return 0.0, {}

        # Target warehouse selection
        options = list(TARGET_WAREHOUSE_RATES.keys())
        default_idx = options.index("Romania / Giurgiu") if "Romania / Giurgiu" in options else 0
        target_wh = st.selectbox("Target warehouse", options, index=default_idx)

        # Inputs specific to second leg
        c1, c2 = st.columns(2)
        with c1:
            weeks_second_leg = st.number_input(
                "Weeks in storage (second leg)",
                min_value=0,
                step=1,
                value=2,
                format="%d",
                help="Number of weeks the goods will stay at the target warehouse.",
            )
        with c2:
            transport_cost_second_leg = st.number_input(
                "Second-leg transport cost (€ total)",
                min_value=0.0,
                step=1.0,
                value=0.0,
                format="%.2f",
                help="Transportation from the primary to the target warehouse.",
            )

        # Do the calculation
        subtotal, breakdown = _compute_second_leg_cost(
            target_wh=target_wh,
            pallets=int(max(0, pallets)),
            weeks_second_leg=int(max(0, weeks_second_leg)),
            transport_cost_second_leg=float(transport_cost_second_leg),
        )

        # Include toggle (whether to add to VVP)
        include = st.checkbox("Include second-leg subtotal in VVP?", value=True)
        added = subtotal if include else 0.0
        breakdown.update({
            "Include in VVP?": include,
            "Second-leg Added to VVP (€)": round(added, 2),
        })

        return added, breakdown

