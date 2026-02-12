"""UI components for warehouse input forms."""

from __future__ import annotations
import math
from typing import Any, Dict, Tuple
import streamlit as st
from warehouses.calculators import VVPCalculator


def _is_spedka(warehouse: Dict[str, Any]) -> bool:
    """Detect SPEDKA warehouse by id/name."""
    wid = str(warehouse.get("id") or "").strip().lower()
    name = str(warehouse.get("name") or "").strip().lower()
    return wid == "sl_spedka" or "spedka" in name


def render_labelling_ui(
    warehouse: Dict[str, Any],
    pieces: int,
    warehouse_name: str
) -> Tuple[bool, float]:
    """
    Render labelling checkbox(es) and calculate cost.

    Returns:
        (labelling_required, label_total)
    """
    features = warehouse.get("features", {}) or {}

    st.markdown("### Labelling")

    # --- SPEDKA special: two options from JSON (admin-editable) ---
    if _is_spedka(warehouse):
        opts = features.get("label_options", {}) or {}
        if not isinstance(opts, dict):
            opts = {}

        simple_rate = float(opts.get("simple", 0.0) or 0.0)
        complex_rate = float(opts.get("complex", 0.0) or 0.0)

        # Safety fallback: if label_options missing, fall back to legacy label_costs sum
        if simple_rate <= 0 and complex_rate <= 0:
            lab = features.get("label_costs")
            if isinstance(lab, dict):
                fallback = float(lab.get("label", 0.0) or 0.0) + float(lab.get("labelling", 0.0) or 0.0)
                # fallback => treat as "simple"
                simple_rate = fallback

        # If still nothing, disable labelling UI completely
        if simple_rate <= 0 and complex_rate <= 0:
            return False, 0.0

        wid = str(warehouse.get("id") or warehouse_name).lower().replace(" ", "_")
        simple_key = f"lab_simple_{wid}"
        complex_key = f"lab_complex_{wid}"

        def _on_simple_change():
            if st.session_state.get(simple_key):
                st.session_state[complex_key] = False

        def _on_complex_change():
            if st.session_state.get(complex_key):
                st.session_state[simple_key] = False

        simple_label = f"Simple label ({simple_rate:.3f} € / pc)" if simple_rate > 0 else "Simple label"
        complex_label = f"Complex label ({complex_rate:.3f} € / pc)" if complex_rate > 0 else "Complex label"

        simple = st.checkbox(simple_label, key=simple_key, on_change=_on_simple_change)
        complex_ = st.checkbox(complex_label, key=complex_key, on_change=_on_complex_change)

        chosen_rate = 0.0
        if simple and simple_rate > 0:
            chosen_rate = simple_rate
        elif complex_ and complex_rate > 0:
            chosen_rate = complex_rate

        labelling_required = chosen_rate > 0
        label_total = float(chosen_rate) * float(pieces) if labelling_required else 0.0

        st.caption(f"Per piece — selected labelling: {chosen_rate:.3f} € / pc")
        return labelling_required, label_total

    # --- Default (all other warehouses): old single checkbox behavior from label_costs ---
    lab = features.get("label_costs")
    if not isinstance(lab, dict) or not ("label" in lab or "labelling" in lab):
        return False, 0.0

    labelling_required = st.checkbox(
        "This order will be labelled.",
        key=f"lab_required_{warehouse_name}"
    )

    label_total = 0.0
    if labelling_required:
        label_per_piece = float(lab.get("label", 0.0) or 0.0)
        labelling_per_piece = float(lab.get("labelling", 0.0) or 0.0)
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
    has_labelling_feature = isinstance(features.get("label_costs"), dict) or isinstance(features.get("label_options"), dict)
    if has_labelling_feature and not labelling_required:
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
