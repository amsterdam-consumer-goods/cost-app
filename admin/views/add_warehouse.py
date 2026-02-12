"""
Add Warehouse Page
==================

Admin interface for creating new warehouses in the system.

Features:
- Basic warehouse information (ID, name)
- Rate configuration (inbound, outbound, storage, order fee)
- Feature toggles (labeling, transfer, second leg)
- Optional advanced labeling (simple/complex labels via checkbox)
- Standard label_costs for basic configuration
- Transfer configuration (Excel lookup or fixed cost)
- Preview before saving
- Form validation

Labeling Modes:
- Standard: Label + Labelling costs (basic structure)
- Advanced (optional): Simple/Complex label options + Labelling
  - Enabled via checkbox for any warehouse
  - Provides two-tier pricing system

Usage:
- Called by admin router
- Creates new warehouse entries in catalog.json
- Validates data before saving
- Clears cache after successful save

Related Files:
- helpers.py: Shared utilities and UI components
- update_warehouse.py: Warehouse editing interface
- services/config_manager.py: Catalog persistence layer
"""

from __future__ import annotations

import json
from typing import Any, Dict

import streamlit as st
import sys
import importlib.util
from pathlib import Path

# ============================================================================
# MODULE IMPORTS
# ============================================================================

# Manually load config_manager module (avoids sys.path pollution)
_root = Path(__file__).resolve().parents[2]
_cm_path = _root / "services" / "config_manager.py"
_spec = importlib.util.spec_from_file_location("services.config_manager", _cm_path)
_cm = importlib.util.module_from_spec(_spec)
sys.modules["services.config_manager"] = _cm
_spec.loader.exec_module(_cm)

load_catalog = _cm.load_catalog
save_catalog = _cm.save_catalog
list_warehouses = _cm.list_warehouses
upsert_warehouse = _cm.upsert_warehouse

# Import local helpers
from .helpers import (
    default_rates,
    default_features,
    has_advanced_labeling,
    validate_warehouse_data,
    render_rates_inputs,
    render_labeling_inputs,
    render_transfer_inputs,
)


# ============================================================================
# STATE MANAGEMENT
# ============================================================================

def ensure_session_state() -> None:
    """Initialize session state flags for this page."""
    st.session_state.setdefault("add_wh_preview_open", False)
    st.session_state.setdefault("last_added_id", "")


def reset_form() -> None:
    """Clear all form-related session state keys."""
    keys_to_clear = [
        # Basic info
        "new_wh_id",
        "new_wh_name",
        # Rates
        "new_rate_inbound",
        "new_rate_outbound",
        "new_rate_storage",
        "new_rate_order_fee",
        # Features
        "new_feat_labeling",
        "new_feat_transfer",
        "new_feat_second_leg",
        # Labeling - standard
        "new_label_cost",
        "new_labelling_cost",
        # Labeling - SPEDKA
        "new_label_simple",
        "new_label_complex",
        # Transfer
        "new_transfer_mode",
        "new_transfer_excel",
        "new_transfer_fixed",
        "new_double_stack",
    ]
    
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]


# ============================================================================
# DATA COLLECTION
# ============================================================================

def collect_form_data() -> Dict[str, Any]:
    """
    Collect current form values from session state and build warehouse payload.
    
    Returns:
        Complete warehouse configuration dictionary
    """
    warehouse_id = (st.session_state.get("new_wh_id") or "").strip()
    warehouse_name = (st.session_state.get("new_wh_name") or "").strip()
    
    # Rates
    rates = {
        "inbound": float(st.session_state.get("new_rate_inbound", 0.0) or 0.0),
        "outbound": float(st.session_state.get("new_rate_outbound", 0.0) or 0.0),
        "storage": float(st.session_state.get("new_rate_storage", 0.0) or 0.0),
        "order_fee": float(st.session_state.get("new_rate_order_fee", 0.0) or 0.0),
    }
    
    # Features - base toggles
    labeling_enabled = bool(st.session_state.get("new_feat_labeling", False))
    transfer_enabled = bool(st.session_state.get("new_feat_transfer", False))
    second_leg_enabled = bool(st.session_state.get("new_feat_second_leg", False))
    
    features: Dict[str, Any] = {
        "labeling": labeling_enabled,
        "transfer": transfer_enabled,
        "second_leg": second_leg_enabled,
    }
    
    # Labeling details
    if labeling_enabled:
        use_advanced = bool(st.session_state.get("new_use_advanced_labels", False))
        
        if use_advanced:
            # Advanced mode: Simple/Complex labels
            simple = float(st.session_state.get("new_label_simple", 0.0) or 0.0)
            complex_val = float(st.session_state.get("new_label_complex", 0.0) or 0.0)
            labelling = float(st.session_state.get("new_labelling_cost", 0.0) or 0.0)
            
            features["label_options"] = {
                "simple": simple,
                "complex": complex_val,
            }
            # Backward compatibility
            features["label_costs"] = {
                "label": simple,
                "labelling": labelling,
            }
        else:
            # Standard mode: Label + Labelling
            label = float(st.session_state.get("new_label_cost", 0.0) or 0.0)
            labelling = float(st.session_state.get("new_labelling_cost", 0.0) or 0.0)
            
            features["label_costs"] = {
                "label": label,
                "labelling": labelling,
            }
    
    # Transfer details
    if transfer_enabled:
        transfer_mode = st.session_state.get("new_transfer_mode", "")
        
        if transfer_mode == "Excel file":
            features["transfer_mode"] = "excel"
            features["transfer_excel"] = str(st.session_state.get("new_transfer_excel", "")).strip()
            features["double_stack"] = bool(st.session_state.get("new_double_stack", False))
        
        elif transfer_mode == "Fixed cost":
            features["transfer_mode"] = "fixed"
            features["transfer_fixed"] = float(st.session_state.get("new_transfer_fixed", 0.0) or 0.0)
    
    return {
        "id": warehouse_id,
        "name": warehouse_name,
        "rates": rates,
        "features": features,
    }


# ============================================================================
# VALIDATION & PERSISTENCE
# ============================================================================

def save_warehouse(warehouse_data: Dict[str, Any], msg_area) -> bool:
    """
    Validate and save warehouse to catalog.
    
    Args:
        warehouse_data: Complete warehouse configuration
        msg_area: Streamlit container for messages
        
    Returns:
        True if save successful, False otherwise
    """
    # Validate basic data
    is_valid, error_msg = validate_warehouse_data(
        warehouse_data.get("id", ""),
        warehouse_data.get("name", "")
    )
    
    if not is_valid:
        msg_area.error(f"❌ {error_msg}")
        return False
    
    warehouse_id = warehouse_data["id"]
    
    # Check for duplicates
    catalog = load_catalog()
    existing_ids = {w.get("id") for w in list_warehouses(catalog) if w.get("id")}
    
    if warehouse_id in existing_ids:
        msg_area.error(f"❌ Warehouse ID '{warehouse_id}' already exists. Choose a unique ID.")
        return False
    
    # Save to catalog
    try:
        updated_catalog, was_new = upsert_warehouse(catalog, warehouse_id, warehouse_data)
        save_catalog(updated_catalog)
    except Exception as e:
        msg_area.error(f"❌ Save failed: {e}")
        st.error(f"🐛 Debug: {type(e).__name__}: {str(e)}")
        return False
    
    # Verify save
    try:
        reloaded = load_catalog()
        reloaded_ids = {w.get("id") for w in list_warehouses(reloaded) if w.get("id")}
        
        if warehouse_id not in reloaded_ids:
            msg_area.error(f"❌ Verification failed: '{warehouse_id}' not found after save!")
            st.error("🐛 Save appeared to succeed but warehouse missing from reloaded catalog.")
            return False
    
    except Exception as e:
        msg_area.warning(f"⚠️ Could not verify save (but save likely succeeded): {e}")
    
    # Success - cleanup
    try:
        st.cache_data.clear()
    except Exception:
        pass
    
    st.session_state["last_added_id"] = warehouse_id
    msg_area.success(f"✅ Warehouse '{warehouse_id}' created successfully!")
    st.toast("Warehouse saved", icon="✅")
    st.balloons()
    
    reset_form()
    return True


# ============================================================================
# PREVIEW RENDERING
# ============================================================================

def render_preview(warehouse_data: Dict[str, Any]) -> None:
    """
    Render preview panel showing warehouse configuration.
    
    Args:
        warehouse_data: Warehouse configuration to preview
    """
    st.divider()
    st.subheader("📋 Preview")
    
    # Raw JSON
    st.write("**Configuration (JSON)**")
    st.code(json.dumps(warehouse_data, indent=2), language="json")
    
    # User-friendly summary
    st.write("**Summary**")
    st.markdown(f"### {warehouse_data.get('name', 'Unnamed')} ({warehouse_data.get('id', 'no-id')})")
    
    # Feature badges
    features = warehouse_data.get("features", {}) or {}
    badges = []
    if features.get("labeling"):
        badges.append("`Labeling`")
    if features.get("transfer"):
        badges.append("`Transfer`")
    if features.get("second_leg"):
        badges.append("`Second-leg`")
    
    if badges:
        st.markdown(" ".join(badges))
    else:
        st.markdown("_No active features_")
    
    # Rates summary
    rates = warehouse_data.get("rates", {}) or {}
    st.caption(
        f"Rates → In: €{rates.get('inbound', 0):.2f} | "
        f"Out: €{rates.get('outbound', 0):.2f} | "
        f"Storage: €{rates.get('storage', 0):.2f}/week | "
        f"Order fee: €{rates.get('order_fee', 0):.2f}"
    )
    
    # Labeling details
    if features.get("labeling"):
        label_opts = features.get("label_options")
        label_costs = features.get("label_costs")
        
        if isinstance(label_opts, dict):
            st.caption(
                f"Label options → Simple: €{label_opts.get('simple', 0):.3f} | "
                f"Complex: €{label_opts.get('complex', 0):.3f}"
            )
        elif isinstance(label_costs, dict):
            st.caption(
                f"Label costs → Label: €{label_costs.get('label', 0):.3f} | "
                f"Labelling: €{label_costs.get('labelling', 0):.3f}"
            )


# ============================================================================
# MAIN PAGE
# ============================================================================

def show() -> None:
    """Render the Add Warehouse page."""
    ensure_session_state()
    
    st.title("Admin • Add Warehouse")
    st.caption("Create a new warehouse configuration")
    
    # -------------------------------------------------------------------------
    # BASIC INFORMATION
    # -------------------------------------------------------------------------
    st.subheader("Basic Information")
    
    st.text_input(
        "Warehouse ID",
        key="new_wh_id",
        placeholder="e.g., nl_svz, de_offergeld",
        help="Unique identifier (letters, numbers, underscores, hyphens only)"
    )
    
    st.text_input(
        "Warehouse Name",
        key="new_wh_name",
        placeholder="e.g., SVZ Logistics NL",
        help="Display name for the warehouse"
    )
    
    st.divider()
    
    # -------------------------------------------------------------------------
    # RATES
    # -------------------------------------------------------------------------
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.number_input(
            "Inbound (€/pallet)",
            key="new_rate_inbound",
            min_value=0.0,
            step=0.5,
            format="%.2f"
        )
    
    with c2:
        st.number_input(
            "Outbound (€/pallet)",
            key="new_rate_outbound",
            min_value=0.0,
            step=0.5,
            format="%.2f"
        )
    
    with c3:
        st.number_input(
            "Storage (€/pallet/week)",
            key="new_rate_storage",
            min_value=0.0,
            step=0.5,
            format="%.2f"
        )
    
    with c4:
        st.number_input(
            "Order fee (€)",
            key="new_rate_order_fee",
            min_value=0.0,
            step=0.5,
            format="%.2f"
        )
    
    st.divider()
    
    # -------------------------------------------------------------------------
    # FEATURES
    # -------------------------------------------------------------------------
    st.subheader("Features")
    
    # Feature toggles
    f1, f2, f3 = st.columns(3)
    
    with f1:
        labeling_enabled = st.checkbox("Labeling", key="new_feat_labeling")
    
    with f2:
        transfer_enabled = st.checkbox("Transfer", key="new_feat_transfer")
    
    with f3:
        st.checkbox("Second Warehouse Transfer", key="new_feat_second_leg")
    
    # ---- Labeling Configuration ----
    if labeling_enabled:
        st.markdown("---")
        
        # Checkbox for advanced mode
        use_advanced = st.checkbox(
            "Enable advanced labeling (Simple/Complex options)",
            key="new_use_advanced_labels",
            help="Use two-tier labeling system"
        )
        
        if use_advanced:
            st.caption("⚡ Advanced mode: Two-tier labeling system")
            
            c1, c2, c3 = st.columns(3)
            
            with c1:
                # Label (disabled in advanced mode)
                st.number_input(
                    "Label (€/piece)",
                    min_value=0.0,
                    step=0.001,
                    format="%.3f",
                    value=0.0,
                    disabled=True,
                    key="new_label_cost_disabled",
                    help="Disabled in advanced mode"
                )
            
            with c2:
                st.number_input(
                    "Simple label (€/piece)",
                    key="new_label_simple",
                    min_value=0.0,
                    step=0.001,
                    format="%.3f",
                    value=0.03,
                    help="Standard label cost"
                )
            
            with c3:
                st.number_input(
                    "Complex label (€/piece)",
                    key="new_label_complex",
                    min_value=0.0,
                    step=0.001,
                    format="%.3f",
                    value=0.042,
                    help="Complex label cost"
                )
            
            st.number_input(
                "Labelling service (€/piece)",
                key="new_labelling_cost",
                min_value=0.0,
                step=0.001,
                format="%.3f",
                value=0.0,
                help="Service fee (applies to both simple and complex)"
            )
        
        else:
            st.markdown("**Standard Labeling**")
            
            c1, c2 = st.columns(2)
            
            with c1:
                st.number_input(
                    "Label (€/piece)",
                    key="new_label_cost",
                    min_value=0.0,
                    step=0.001,
                    format="%.3f",
                    help="Label material cost"
                )
            
            with c2:
                st.number_input(
                    "Labelling service (€/piece)",
                    key="new_labelling_cost",
                    min_value=0.0,
                    step=0.001,
                    format="%.3f",
                    help="Labeling service fee"
                )
    
    # ---- Transfer Configuration ----
    if transfer_enabled:
        st.markdown("---")
        st.markdown("**Transfer Configuration**")
        
        t1, t2, t3 = st.columns([1.2, 1.2, 1])
        
        with t1:
            transfer_mode = st.selectbox(
                "Transfer mode",
                options=["", "Excel file", "Fixed cost"],
                key="new_transfer_mode",
                help="Excel file: pallets→truck_cost lookup. Fixed cost: single amount."
            )
        
        with t2:
            if transfer_mode == "Excel file":
                st.checkbox(
                    "Double Stack",
                    key="new_double_stack",
                    help="Halves pallet count when looking up costs"
                )
        
        # Mode-specific fields
        if transfer_mode == "Excel file":
            st.text_input(
                "Excel file path",
                key="new_transfer_excel",
                placeholder="e.g., data/transfer_rates_nl_svz.json",
                help="Path to JSON/Excel with 'pallets' and 'truck_cost' columns"
            )
        
        elif transfer_mode == "Fixed cost":
            st.number_input(
                "Fixed transfer amount (€ total)",
                key="new_transfer_fixed",
                min_value=0.0,
                step=1.0,
                help="Single fixed cost per transfer leg"
            )
    
    st.divider()
    
    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------
    a1, a2, a3 = st.columns(3)
    
    with a1:
        if st.button("📋 Preview", use_container_width=True):
            st.session_state.add_wh_preview_open = True
            st.rerun()
    
    # Message area (inline, under buttons)
    msg_area = st.empty()
    
    with a2:
        if st.button("💾 Save", use_container_width=True, type="primary"):
            warehouse_data = collect_form_data()
            save_warehouse(warehouse_data, msg_area)
    
    with a3:
        if st.button("🔄 Reset", use_container_width=True):
            reset_form()
            msg_area.info("Form cleared")
            st.rerun()
    
    # -------------------------------------------------------------------------
    # PREVIEW PANEL
    # -------------------------------------------------------------------------
    if st.session_state.get("add_wh_preview_open", False):
        warehouse_data = collect_form_data()
        render_preview(warehouse_data)
        
        b1, b2 = st.columns(2)
        
        with b1:
            if st.button("Close preview", use_container_width=True):
                st.session_state.add_wh_preview_open = False
                st.rerun()
        
        with b2:
            if st.button("Save from preview", use_container_width=True, type="primary"):
                st.session_state.add_wh_preview_open = False
                if save_warehouse(warehouse_data, msg_area):
                    st.rerun()


# ============================================================================
# ALIASES (for compatibility with different import styles)
# ============================================================================

def view() -> None:
    """Alias for router compatibility."""
    show()


def page_add_warehouse() -> None:
    """Alias for legacy imports."""
    show()