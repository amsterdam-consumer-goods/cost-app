"""
Netherlands / SVZ — first leg + labelling transfer (JSON lookup) + optional second leg.

First leg (per order):
- Inbound  : €2.75 / pallet
- Outbound : €2.75 / pallet
- Storage  : €1.36 / pallet / week
- Optional pallet cost from app.py: (€/pallet) × pallets → INCLUDED in VVP if > 0

Labelling transfer (SVZ-specific):
- Always priced via JSON lookup (pallets → truck_cost €).
- If "Double stack?" is checked, lookup uses ceil(pallets / 2), else pallets as-is.
- Two independent checkboxes:
    * Warehouse → Labelling
    * Labelling → Warehouse
  Each selected direction adds one truck_cost (same rate table).
- If "Labelling → Warehouse" is selected, an EXTRA warehousing round (in+out+storage) is added.

Second leg (optional):
- Computed via warehouses/second_leg.py using target warehouse rates.
- Returned amount is added to VVP when enabled in the UI.
"""

from __future__ import annotations
import json
import math
from pathlib import Path
import streamlit as st
from .final_calc import final_calculator
from .second_leg import second_leg_ui

# ------------------------------
# Fixed rates (first leg)
# ------------------------------
INBOUND_PER_PALLET = 2.75
OUTBOUND_PER_PALLET = 2.75
STORAGE_PER_PALLET_PER_WEEK = 1.36

# JSON file with truck rates (1..66 pallets → € per truck)
SVZ_TRUCK_RATES_PATH = Path("data/svz_truck_rates.json")


@st.cache_data(show_spinner=False)
def _load_truck_rates(path: Path) -> dict[int, float]:
    """Load {pallet:int -> truck_cost:float} from JSON (dict or list format)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        st.error(f"SVZ truck rates file not found: {path}")
        return {}
    except Exception as e:
        st.error(f"Failed to read SVZ truck rates JSON: {e}")
        return {}

    rates: dict[int, float] = {}
    if isinstance(data, dict):
        for k, v in data.items():
            try:
                rates[int(k)] = float(v)
            except Exception:
                continue
    elif isinstance(data, list):
        for row in data:
            try:
                rates[int(row["pallets"])] = float(row["truck_cost"])
            except Exception:
                continue
    return rates


def _lookup_truck_cost(rates: dict[int, float], pallets_for_lookup: int) -> float:
    """Return truck cost for given pallet count (clamped 1..66; fallback to nearest lower key)."""
    if not rates:
        return 0.0
    n = max(1, min(66, int(pallets_for_lookup)))
    if n in rates:
        return rates[n]
    lower_or_equal = sorted([k for k in rates.keys() if k <= n])
    return rates[lower_or_equal[-1]] if lower_or_equal else 0.0


def compute_nl_svz(
    pieces: int,
    pallets: int,
    weeks: int,
    buying_transport_cost: float,
    pallet_unit_cost: float,
) -> None:
    """Render Netherlands / SVZ calculator and VVP results (with JSON-based labelling transfer)."""
    st.subheader("Netherlands / SVZ")

    # -------------------------
    # First-leg warehousing (one round)
    # -------------------------
    inbound_cost = pallets * INBOUND_PER_PALLET
    outbound_cost = pallets * OUTBOUND_PER_PALLET
    storage_cost = pallets * weeks * STORAGE_PER_PALLET_PER_WEEK
    warehousing_one_round = inbound_cost + outbound_cost + storage_cost

    # -------------------------
    # Labelling (per piece) + transfer (JSON lookup)
    # -------------------------
    st.markdown("### Labelling")
    labelling_required = st.checkbox("Labelling required?")
    LABEL_PER_PIECE = 0.015
    LABELLING_PER_PIECE = 0.045

    labelling_per_piece_total = (LABEL_PER_PIECE + LABELLING_PER_PIECE) * pieces if labelling_required else 0.0

    double_stack = False
    wh_to_lab = False
    lab_to_wh = False

    if labelling_required:
        st.subheader("Labelling Transfer")
        double_stack = st.checkbox("Double stack?")
        wh_to_lab = st.checkbox("Warehouse → Labelling")
        lab_to_wh = st.checkbox("Labelling → Warehouse")
        if not (wh_to_lab or lab_to_wh):
            st.info("Select at least one transfer leg (WH→Labelling and/or Labelling→WH).")

    rates = _load_truck_rates(SVZ_TRUCK_RATES_PATH)
    pallets_for_transfer = math.ceil(pallets / 2) if (labelling_required and double_stack) else pallets
    truck_cost = _lookup_truck_cost(rates, pallets_for_transfer) if labelling_required else 0.0

    wh_to_lab_cost = truck_cost if (labelling_required and wh_to_lab) else 0.0
    lab_to_wh_cost = truck_cost if (labelling_required and lab_to_wh) else 0.0
    labelling_transfer_total = wh_to_lab_cost + lab_to_wh_cost

    # Extra warehousing if goods return from labelling back to warehouse
    extra_warehousing_on_return = warehousing_one_round if (labelling_required and lab_to_wh) else 0.0

    # -------------------------
    # Optional pallet cost from app.py
    # -------------------------
    pallet_cost_total = (pallet_unit_cost or 0.0) * pallets if (pallet_unit_cost or 0) > 0 else 0.0

    # -------------------------
    # Second leg (optional)
    # -------------------------
    second_leg_added_cost, second_leg_breakdown = second_leg_ui(
        primary_warehouse="Netherlands / SVZ",
        pallets=pallets,
    )

    # -------------------------
    # Totals for VVP
    # -------------------------
    warehousing_total = warehousing_one_round + extra_warehousing_on_return
    base_total = (
        warehousing_total
        + buying_transport_cost
        + pallet_cost_total
        + labelling_per_piece_total
        + labelling_transfer_total
    )
    total_cost = base_total + second_leg_added_cost

    cost_per_piece = (total_cost / pieces) if pieces else 0.0
    cost_per_piece_rounded = math.ceil(cost_per_piece * 100) / 100.0

    st.caption("You are entering inputs for **Netherlands / SVZ**")

    # -------------------------
    # Results (VVP)
    # -------------------------
    st.markdown("---")
    st.subheader("VVP Results")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Cost (€)", f"{total_cost:.2f}")
    with c2:
        st.metric("Cost per piece (€)", f"{cost_per_piece:.4f}")
    with c3:
        st.metric("Rounded Cost per piece (€)", f"{cost_per_piece_rounded:.2f}")

    # -------------------------
    # Breakdown
    # -------------------------
    with st.expander("Breakdown"):
        rows = {
            # First leg
            "Inbound Cost (€)": round(inbound_cost, 2),
            "Outbound Cost (€)": round(outbound_cost, 2),
            "Storage Cost (€)": round(storage_cost, 2),
            "Warehousing Total (1st leg) (€)": round(warehousing_one_round, 2),

            # Return warehousing (if any)
            "Extra Warehousing on Return (€)": round(extra_warehousing_on_return, 2),

            # Pallet cost
            "Pallet Unit Cost (€/pallet)": round(pallet_unit_cost or 0.0, 2),
            "Pallets (#)": pallets,
            "Pallet Cost Total (€)": round(pallet_cost_total, 2),

            # Buying transport
            "Buying Transport Cost (€ total)": round(buying_transport_cost, 2),

            # Labelling (per piece)
            "Labelling applied?": bool(labelling_required),
            "Labelling per-piece Total (€)": round(labelling_per_piece_total, 2),

            # SVZ labelling transfer (JSON lookup)
            "—— Labelling Transfer ——": "",
            "Double Stack Applied?": bool(labelling_required and double_stack),
            "Labelling Transfer Pallets Used (#)": pallets_for_transfer if labelling_required else 0,
            "Truck Cost per direction (€)": round(truck_cost, 2),
            "WH → Labelling (€)": round(wh_to_lab_cost, 2),
            "Labelling → WH (€)": round(lab_to_wh_cost, 2),
            "Labelling Transfer Total (€)": round(labelling_transfer_total, 2),
        }

        if second_leg_breakdown:
            rows.update(second_leg_breakdown)

        rows.update({
            "Warehousing Total (incl. return) (€)": round(warehousing_total, 2),
            "TOTAL (€)": round(total_cost, 2),
            "Cost per piece (€)": round(cost_per_piece, 4),
        })
        st.write(rows)

    # -------------------------
    # Hand off to P&L
    # -------------------------
    st.markdown("---")
    final_calculator(pieces=pieces, vvp_cost_per_piece_rounded=cost_per_piece_rounded)
