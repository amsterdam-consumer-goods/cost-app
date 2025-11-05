"""UI components for warehouse input forms."""

from __future__ import annotations
import math
from typing import Any, Dict, Tuple
import streamlit as st
from warehouses.calculators import VVPCalculator


def render_labelling_ui(
    warehouse: Dict[str, Any],
    pieces: int,
    warehouse_name: str
) -> Tuple[bool, float]:
    """
    Render labelling checkbox and calculate cost.
    
    Returns:
        (labelling_required, label_total)
    """
    features = warehouse.get("features", {}) or {}
    lab = features.get("label_costs")
    
    if not isinstance(lab, dict) or not ("label" in lab or "labelling" in lab):
        return False, 0.0
    
    st.markdown("### Labelling")
    labelling_required = st.checkbox(
        "This order will be labelled.",
        key=f"lab_required_{warehouse_name}"
    )
    
    label_total = 0.0
    if labelling_required:
        label_per_piece = float(lab.get("label", 0.0))
        labelling_per_piece = float(lab.get("labelling", 0.0))
        label_total = (label_per_piece + labelling_per_piece) * float(pieces)
    
    st.caption(
        f"Per piece — label: {lab.get('label', 0)} / labelling: {lab.get('labelling', 0)}"
    )
    
    return labelling_required, label_total


def render_transfer_ui(
    warehouse: Dict[str, Any],
    pallets: int,
    inbound_per: float,
    outbound_per: float,
    labelling_required: bool,
    warehouse_name: str
) -> Tuple[float, float]:
    """
    Render transfer UI and calculate costs.
    
    Returns:
        (transfer_total, extra_warehousing_on_return)
    """
    features = warehouse.get("features", {}) or {}
    
    if not bool(features.get("transfer", False)):
        return 0.0, 0.0
    
    # Skip if labelling feature exists but not required
    if isinstance(features.get("label_costs"), dict) and not labelling_required:
        return 0.0, 0.0
    
    st.subheader("Labelling Transfer")
    
    mode_raw = str(features.get("transfer_mode", "")).strip().lower()
    if mode_raw in ("json_lookup", "lookup", "excel_lookup"):
        mode = "excel"
    elif mode_raw in ("manual_fixed", "fixed"):
        mode = "fixed"
    else:
        mode = mode_raw
    
    if mode == "excel":
        return _render_transfer_excel(
            warehouse, pallets, inbound_per, outbound_per, features, warehouse_name
        )
    elif mode == "fixed":
        return _render_transfer_fixed(features)
    else:
        st.caption("Transfer disabled or unsupported mode.")
        return 0.0, 0.0


def _render_transfer_excel(
    warehouse: Dict[str, Any],
    pallets: int,
    inbound_per: float,
    outbound_per: float,
    features: Dict[str, Any],
    warehouse_name: str
) -> Tuple[float, float]:
    """Render Excel-based transfer UI."""
    wid = str(warehouse.get("id") or warehouse_name).lower().replace(" ", "_")
    double_stack_flag = bool(features.get("double_stack", False))
    
    double_stack = False
    if double_stack_flag:
        double_stack = st.checkbox("Double Stackable", value=False, key=f"ds_{wid}")
    
    wh_to_lab = st.checkbox("Warehouse → Labelling", value=False, key=f"wh2lab_{wid}")
    lab_to_wh = st.checkbox("Labelling → Warehouse", value=False, key=f"lab2wh_{wid}")
    
    if not (wh_to_lab or lab_to_wh):
        st.info("Select at least one transfer leg (WH→Lab and/or Lab→WH).")
        return 0.0, 0.0
    
    lookup_path = str(features.get("transfer_excel") or "")
    rates_excel = VVPCalculator.load_truck_rates(lookup_path)
    
    pallets_for_lookup = math.ceil(pallets / 2) if (double_stack and pallets > 0) else pallets
    
    calculator = VVPCalculator(warehouse)
    truck_cost = calculator._lookup_truck_cost(rates_excel, pallets_for_lookup)
    
    wh_to_lab_cost = truck_cost if wh_to_lab else 0.0
    lab_to_wh_cost = truck_cost if lab_to_wh else 0.0
    transfer_total = wh_to_lab_cost + lab_to_wh_cost
    
    extra_warehousing = 0.0
    if wh_to_lab and lab_to_wh:
        extra_warehousing = float(pallets) * (inbound_per + outbound_per)
    
    return transfer_total, extra_warehousing


def _render_transfer_fixed(features: Dict[str, Any]) -> Tuple[float, float]:
    """Render fixed transfer cost UI."""
    fixed = float(features.get("transfer_fixed", 0.0))
    st.info(f"Fixed transfer (catalog): €{fixed:,.2f}")
    return fixed, 0.0