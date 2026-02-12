"""
Warehouse Input UI Components
==============================

Streamlit UI components for warehouse selection and configuration in the main user app.

This module provides:
- Labeling UI (standard or advanced mode detection from catalog)
- Transfer cost calculation UI
- Integration with warehouse calculators

Detection Logic:
- Checks catalog for label_options (simple/complex)
- If present and values > 0 → Shows advanced UI (Simple/Complex checkboxes)
- If not present → Shows standard UI (single Labeling checkbox)

Related Files:
- warehouses/calculators.py: Cost calculation logic
- data/catalog.json: Warehouse configurations
- admin/views/: Admin configuration interface
"""

from __future__ import annotations
import math
from typing import Any, Dict, Tuple
import streamlit as st
from warehouses.calculators import VVPCalculator


# ============================================================================
# DETECTION HELPERS
# ============================================================================

def _has_advanced_labeling(warehouse: Dict[str, Any]) -> bool:
    """
    Check if warehouse uses advanced labeling (simple/complex options).
    
    Detection:
    - Looks for label_options in warehouse features
    - Verifies at least one option has value > 0
    
    Args:
        warehouse: Warehouse configuration dictionary
        
    Returns:
        True if advanced labeling is configured and active, False otherwise
    """
    features = warehouse.get("features", {}) or {}
    label_opts = features.get("label_options")
    
    if not isinstance(label_opts, dict):
        return False
    
    simple = float(label_opts.get("simple", 0.0) or 0.0)
    complex_val = float(label_opts.get("complex", 0.0) or 0.0)
    
    return simple > 0 or complex_val > 0


def _get_warehouse_key(warehouse: Dict[str, Any], warehouse_name: str) -> str:
    """
    Generate unique widget key for warehouse.
    
    Args:
        warehouse: Warehouse configuration
        warehouse_name: Warehouse display name
        
    Returns:
        Sanitized unique key
    """
    wid = str(warehouse.get("id") or warehouse_name)
    return wid.lower().replace(" ", "_").replace("-", "_")


# ============================================================================
# LABELING UI
# ============================================================================

def render_labelling_ui(
    warehouse: Dict[str, Any],
    pieces: int,
    warehouse_name: str
) -> Tuple[bool, float]:
    """
    Render labeling UI and calculate cost.
    
    Automatically detects mode from catalog:
    - Advanced mode: Shows Simple/Complex checkboxes (mutually exclusive)
    - Standard mode: Shows single "This order will be labelled" checkbox
    
    Args:
        warehouse: Warehouse configuration from catalog
        pieces: Number of pieces to label
        warehouse_name: Display name (for widget keys)
        
    Returns:
        Tuple of (labeling_required, total_cost)
        - labeling_required: True if any labeling option selected
        - total_cost: Total labeling cost in euros
    """
    features = warehouse.get("features", {}) or {}
    
    st.markdown("### Labelling")
    
    # -------------------------------------------------------------------------
    # ADVANCED MODE: Simple/Complex Options
    # -------------------------------------------------------------------------
    if _has_advanced_labeling(warehouse):
        label_opts = features.get("label_options", {}) or {}
        
        simple_rate = float(label_opts.get("simple", 0.0) or 0.0)
        complex_rate = float(label_opts.get("complex", 0.0) or 0.0)
        
        # Safety check
        if simple_rate <= 0 and complex_rate <= 0:
            st.info("No labeling options available.")
            return False, 0.0
        
        # Generate unique keys
        wid = _get_warehouse_key(warehouse, warehouse_name)
        simple_key = f"lab_simple_{wid}"
        complex_key = f"lab_complex_{wid}"
        
        # Mutual exclusion callbacks
        def _on_simple_change():
            if st.session_state.get(simple_key):
                st.session_state[complex_key] = False
        
        def _on_complex_change():
            if st.session_state.get(complex_key):
                st.session_state[simple_key] = False
        
        # Render checkboxes
        simple_selected = False
        complex_selected = False
        
        if simple_rate > 0:
            simple_label = f"Simple label (€{simple_rate:.3f} / pc)"
            simple_selected = st.checkbox(
                simple_label,
                key=simple_key,
                on_change=_on_simple_change
            )
        
        if complex_rate > 0:
            complex_label = f"Complex label (€{complex_rate:.3f} / pc)"
            complex_selected = st.checkbox(
                complex_label,
                key=complex_key,
                on_change=_on_complex_change
            )
        
        # Calculate cost
        chosen_rate = 0.0
        if simple_selected and simple_rate > 0:
            chosen_rate = simple_rate
        elif complex_selected and complex_rate > 0:
            chosen_rate = complex_rate
        
        labeling_required = chosen_rate > 0
        label_total = float(chosen_rate) * float(pieces) if labeling_required else 0.0
        
        # Add labelling service cost if present
        label_costs = features.get("label_costs")
        if isinstance(label_costs, dict) and labeling_required:
            labelling_service = float(label_costs.get("labelling", 0.0) or 0.0)
            if labelling_service > 0:
                label_total += labelling_service * float(pieces)
                st.caption(
                    f"Label: €{chosen_rate:.3f}/pc + "
                    f"Service: €{labelling_service:.3f}/pc"
                )
            else:
                st.caption(f"Selected: €{chosen_rate:.3f} / pc")
        else:
            st.caption(f"Selected: €{chosen_rate:.3f} / pc")
        
        return labeling_required, label_total
    
    # -------------------------------------------------------------------------
    # STANDARD MODE: Single Checkbox
    # -------------------------------------------------------------------------
    else:
        label_costs = features.get("label_costs")
        
        # Check if labeling is available
        if not isinstance(label_costs, dict):
            st.info("No labeling configured.")
            return False, 0.0
        
        label_per_piece = float(label_costs.get("label", 0.0) or 0.0)
        labelling_per_piece = float(label_costs.get("labelling", 0.0) or 0.0)
        total_per_piece = label_per_piece + labelling_per_piece
        
        # If no costs, hide UI
        if total_per_piece <= 0:
            st.info("No labeling configured.")
            return False, 0.0
        
        # Single checkbox
        labeling_required = st.checkbox(
            "This order will be labelled.",
            key=f"lab_required_{_get_warehouse_key(warehouse, warehouse_name)}"
        )
        
        # Calculate cost
        label_total = 0.0
        if labeling_required:
            label_total = total_per_piece * float(pieces)
        
        # Show breakdown
        if label_per_piece > 0 and labelling_per_piece > 0:
            st.caption(
                f"Label: €{label_per_piece:.3f}/pc + "
                f"Labelling: €{labelling_per_piece:.3f}/pc = "
                f"€{total_per_piece:.3f}/pc"
            )
        elif label_per_piece > 0:
            st.caption(f"Label: €{label_per_piece:.3f}/pc")
        elif labelling_per_piece > 0:
            st.caption(f"Labelling: €{labelling_per_piece:.3f}/pc")
        
        return labeling_required, label_total


# ============================================================================
# TRANSFER UI
# ============================================================================

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
    
    Transfer is only available if:
    1. Transfer feature is enabled in warehouse config
    2. Labeling is required (transfer moves labeled goods)
    
    Supports two modes:
    - Excel lookup: Pallet count → truck cost lookup from JSON table
    - Fixed cost: Single predetermined transfer cost
    
    Args:
        warehouse: Warehouse configuration
        pallets: Number of pallets to transfer
        inbound_per: Inbound cost per pallet (for extra warehousing)
        outbound_per: Outbound cost per pallet (for extra warehousing)
        labelling_required: Whether labeling is required
        warehouse_name: Display name
        
    Returns:
        Tuple of (transfer_total, extra_warehousing_on_return)
        - transfer_total: Total transfer cost in euros
        - extra_warehousing_on_return: Additional warehousing cost for round trip
    """
    features = warehouse.get("features", {}) or {}
    
    # Check if transfer is enabled
    if not bool(features.get("transfer", False)):
        return 0.0, 0.0
    
    # Transfer only available if labeling
    has_labeling = (
        isinstance(features.get("label_costs"), dict) or 
        isinstance(features.get("label_options"), dict)
    )
    
    if has_labeling and not labelling_required:
        return 0.0, 0.0
    
    st.subheader("Labelling Transfer")
    
    # Determine mode
    mode_raw = str(features.get("transfer_mode", "")).strip().lower()
    
    if mode_raw in ("json_lookup", "lookup", "excel", "excel_lookup"):
        mode = "excel"
    elif mode_raw in ("manual_fixed", "fixed"):
        mode = "fixed"
    else:
        mode = mode_raw
    
    # Route to appropriate handler
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
    """
    Render Excel-based transfer UI.
    
    Loads truck costs from JSON table and allows double-stacking option.
    
    Args:
        warehouse: Warehouse configuration
        pallets: Number of pallets
        inbound_per: Inbound cost per pallet
        outbound_per: Outbound cost per pallet
        features: Warehouse features dict
        warehouse_name: Display name
        
    Returns:
        Tuple of (transfer_total, extra_warehousing)
    """
    wid = _get_warehouse_key(warehouse, warehouse_name)
    double_stack_flag = bool(features.get("double_stack", False))
    
    # Double stack option
    double_stack = False
    if double_stack_flag:
        double_stack = st.checkbox(
            "Double Stackable",
            value=False,
            key=f"ds_{wid}"
        )
    
    # Transfer direction checkboxes
    wh_to_lab = st.checkbox(
        "Warehouse → Labelling",
        value=False,
        key=f"wh2lab_{wid}"
    )
    
    lab_to_wh = st.checkbox(
        "Labelling → Warehouse",
        value=False,
        key=f"lab2wh_{wid}"
    )
    
    if not (wh_to_lab or lab_to_wh):
        st.info("Select at least one transfer leg.")
        return 0.0, 0.0
    
    # Load truck rates
    lookup_path = str(features.get("transfer_excel") or "")
    rates_excel = VVPCalculator.load_truck_rates(lookup_path)
    
    # Adjust pallet count if double-stacking
    pallets_for_lookup = math.ceil(pallets / 2) if (double_stack and pallets > 0) else pallets
    
    # Calculate truck cost
    calculator = VVPCalculator(warehouse)
    truck_cost = calculator._lookup_truck_cost(rates_excel, pallets_for_lookup)
    
    # Calculate per leg
    wh_to_lab_cost = truck_cost if wh_to_lab else 0.0
    lab_to_wh_cost = truck_cost if lab_to_wh else 0.0
    transfer_total = wh_to_lab_cost + lab_to_wh_cost
    
    # Extra warehousing if round trip
    extra_warehousing = 0.0
    if wh_to_lab and lab_to_wh:
        extra_warehousing = float(pallets) * (inbound_per + outbound_per)
    
    # Show info
    st.caption(f"Truck cost per leg: €{truck_cost:.2f}")
    if double_stack and pallets > 0:
        st.caption(f"Double-stacked: {pallets} pallets → {pallets_for_lookup} truck slots")
    
    return transfer_total, extra_warehousing


def _render_transfer_fixed(features: Dict[str, Any]) -> Tuple[float, float]:
    """
    Render fixed transfer cost UI.
    
    Args:
        features: Warehouse features dict
        
    Returns:
        Tuple of (fixed_cost, 0.0)
    """
    fixed = float(features.get("transfer_fixed", 0.0))
    st.info(f"Fixed transfer: €{fixed:,.2f}")
    return fixed, 0.0