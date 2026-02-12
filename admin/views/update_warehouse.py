"""
Update Warehouse Page
=====================

Admin interface for editing and deleting existing warehouses.

Features:
- Warehouse selection with auto-refresh
- Edit all warehouse properties (rates, features, labels, transfer)
- Optional advanced labeling (simple/complex labels via checkbox)
- Standard label_costs for basic configuration
- Transfer configuration (Excel lookup or fixed cost)
- Delete warehouse with inline confirmation
- State isolation per warehouse (prevents data bleed between selections)
- Success messages with persistence across reruns

Labeling Modes:
- Standard: Label + Labelling costs (basic structure)
- Advanced (optional): Simple/Complex label options + Labelling
  - Enabled via checkbox for any warehouse
  - Automatically detected from existing configuration
  - Provides two-tier pricing system

State Management:
- Uses per-warehouse session keys to prevent data bleed
- Clears old state when switching warehouses
- Persists success messages across reruns

Usage:
- Called by admin router
- Updates existing warehouse entries in catalog.json
- Provides delete functionality with confirmation
- Clears cache after modifications

Related Files:
- helpers.py: Shared utilities and UI components
- add_warehouse.py: Warehouse creation interface
- services/config_manager.py: Catalog persistence layer
"""

from __future__ import annotations
import streamlit as st
from typing import Dict, Any

from services.catalog import (
    load_catalog,
    save_catalog,
    list_warehouses,
    get_wh_by_id,
    get_catalog_path,
)

from .helpers import (
    default_rates,
    default_features,
    normalize_rates,
    has_advanced_labeling,
)


# ============================================================================
# UTILITIES
# ============================================================================

def generate_widget_key(warehouse_id: str, widget_name: str) -> str:
    """
    Generate unique, stable widget key for a specific warehouse.
    
    This prevents state bleed when switching between warehouses.
    
    Args:
        warehouse_id: Warehouse identifier
        widget_name: Widget identifier
        
    Returns:
        Unique session state key
    """
    return f"upd__{widget_name}__{warehouse_id}"


def cleanup_old_warehouse_state(previous_id: str | None) -> None:
    """
    Clear session state from previously selected warehouse.
    
    Args:
        previous_id: Previously selected warehouse ID (if any)
    """
    if not previous_id:
        return
    
    # Remove all keys related to this warehouse
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("upd__") and key.endswith(f"__{previous_id}"):
            del st.session_state[key]


# ============================================================================
# MAIN PAGE
# ============================================================================

def page_update_warehouse():
    """Render the Update Warehouse page."""
    
    st.title("Admin • Update Warehouse")
    st.caption("Edit or delete existing warehouse configurations")
    
    # -------------------------------------------------------------------------
    # WAREHOUSE SELECTION
    # -------------------------------------------------------------------------
    
    # Manual refresh button
    ctrl_col, _ = st.columns([1, 3])
    with ctrl_col:
        if st.button("🔄 Refresh list"):
            try:
                st.cache_data.clear()
            except Exception:
                pass
            st.rerun()
    
    # Load warehouses
    catalog = load_catalog()
    warehouse_list = list_warehouses(catalog)
    
    if not warehouse_list:
        st.info("No warehouses yet. Use 'Add warehouse' to create one.")
        return
    
    # Build selection data
    id_list = sorted([w["id"] for w in warehouse_list if w.get("id")])
    label_map = {
        w["id"]: f"{w.get('name', w['id'])} ({w['id']})"
        for w in warehouse_list
        if w.get("id")
    }
    
    # Determine default selection
    pending = st.session_state.pop("_next_select_id", None)
    last_added = st.session_state.get("last_added_id")
    current = st.session_state.get("update_wh_select_id")
    
    if pending in id_list:
        default_id = pending
    elif last_added in id_list:
        default_id = last_added
    elif current in id_list:
        default_id = current
    else:
        default_id = id_list[0]
    
    default_index = id_list.index(default_id)
    
    selected_id = st.selectbox(
        "Select warehouse to edit",
        options=id_list,
        index=default_index,
        key="update_wh_select_id",
        format_func=lambda wid: label_map.get(wid, wid),
    )
    
    # -------------------------------------------------------------------------
    # STATE ISOLATION & CLEANUP
    # -------------------------------------------------------------------------
    
    # Track last selection to detect changes
    prev_id = st.session_state.get("_last_selected_id")
    
    if prev_id != selected_id:
        # Warehouse changed - cleanup old state
        cleanup_old_warehouse_state(prev_id)
        st.session_state["_last_selected_id"] = selected_id
    
    # Helper for generating widget keys
    def skey(name: str) -> str:
        return generate_widget_key(selected_id, name)
    
    st.divider()
    
    # -------------------------------------------------------------------------
    # LOAD WAREHOUSE DATA
    # -------------------------------------------------------------------------
    
    warehouse = get_wh_by_id(catalog, selected_id) or {
        "id": selected_id,
        "name": selected_id,
        "rates": default_rates(),
        "features": default_features(),
    }
    
    features = warehouse.get("features", {}) or {}
    rates = normalize_rates(warehouse.get("rates", {}))
    
    # -------------------------------------------------------------------------
    # BASIC INFORMATION
    # -------------------------------------------------------------------------
    
    st.subheader("Basic Information")
    
    current_name = str(warehouse.get("name", selected_id)).strip() or selected_id
    new_name = st.text_input(
        "Warehouse Name",
        value=current_name,
        key=skey("wh_name"),
    )
    
    st.divider()
    
    # -------------------------------------------------------------------------
    # RATES
    # -------------------------------------------------------------------------
    
    st.subheader("Rates (€)")
    
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        new_inbound = st.number_input(
            "Inbound (€/pallet)",
            value=float(rates.get("inbound", 0.0)),
            key=skey("rate_inbound"),
            min_value=0.0,
            step=0.5,
            format="%.2f"
        )
    
    with c2:
        new_outbound = st.number_input(
            "Outbound (€/pallet)",
            value=float(rates.get("outbound", 0.0)),
            key=skey("rate_outbound"),
            min_value=0.0,
            step=0.5,
            format="%.2f"
        )
    
    with c3:
        new_storage = st.number_input(
            "Storage (€/pallet/week)",
            value=float(rates.get("storage", 0.0)),
            key=skey("rate_storage"),
            min_value=0.0,
            step=0.5,
            format="%.2f"
        )
    
    with c4:
        new_order_fee = st.number_input(
            "Order fee (€)",
            value=float(rates.get("order_fee", 0.0)),
            key=skey("rate_order_fee"),
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
    lab_col, trans_col, leg_col = st.columns(3)
    
    with lab_col:
        labeling_enabled = st.checkbox(
            "Labeling",
            value=bool(features.get("labeling", False)),
            key=skey("feat_labeling"),
        )
    
    with trans_col:
        transfer_enabled = st.checkbox(
            "Transfer",
            value=bool(features.get("transfer", False)),
            key=skey("feat_transfer"),
        )
    
    with leg_col:
        second_leg_enabled = st.checkbox(
            "Second Warehouse Transfer",
            value=bool(features.get("second_leg", False)),
            key=skey("feat_second_leg"),
        )
    
    # ---- Labeling Configuration ----
    if labeling_enabled:
        st.markdown("---")
        
        # Check if currently using advanced mode
        use_advanced_current = has_advanced_labeling(features)
        
        # Checkbox for advanced mode
        use_advanced = st.checkbox(
            "Enable advanced labeling (Simple/Complex options)",
            value=use_advanced_current,
            key=skey("use_advanced_labels"),
            help="Use two-tier labeling system"
        )
        
        # Get current values
        label_costs = features.get("label_costs", {}) or {}
        label_opts = features.get("label_options", {}) or {}
        
        current_label = float(label_costs.get("label", 0.0) or 0.0)
        current_labelling = float(label_costs.get("labelling", 0.0) or 0.0)
        current_simple = float(label_opts.get("simple", 0.0) or 0.0)
        current_complex = float(label_opts.get("complex", 0.0) or 0.0)
        
        # Smart defaults when switching modes
        if use_advanced and current_simple == 0.0 and current_label > 0.0:
            current_simple = current_label
        if not use_advanced and current_label == 0.0 and current_simple > 0.0:
            current_label = current_simple
        
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
                    key=skey("label_cost_disabled"),
                    help="Disabled in advanced mode"
                )
            
            with c2:
                spedka_simple = st.number_input(
                    "Simple label (€/piece)",
                    min_value=0.0,
                    step=0.001,
                    format="%.4f",
                    value=current_simple,
                    key=skey("spedka_simple"),
                    help="Standard label cost"
                )
            
            with c3:
                spedka_complex = st.number_input(
                    "Complex label (€/piece)",
                    min_value=0.0,
                    step=0.001,
                    format="%.4f",
                    value=current_complex,
                    key=skey("spedka_complex"),
                    help="Complex label cost"
                )
            
            labelling_per_piece = st.number_input(
                "Labelling service (€/piece)",
                min_value=0.0,
                step=0.001,
                format="%.3f",
                value=current_labelling,
                key=skey("labelling_per_piece"),
                help="Service fee (applies to both)"
            )
        
        else:
            st.markdown("**Standard Labeling**")
            
            c1, c2 = st.columns(2)
            
            with c1:
                label_per_piece = st.number_input(
                    "Label (€/piece)",
                    min_value=0.0,
                    step=0.001,
                    format="%.3f",
                    value=current_label,
                    key=skey("label_per_piece"),
                    help="Label material cost"
                )
            
            with c2:
                labelling_per_piece = st.number_input(
                    "Labelling service (€/piece)",
                    min_value=0.0,
                    step=0.001,
                    format="%.3f",
                    value=current_labelling,
                    key=skey("labelling_per_piece"),
                    help="Labeling service fee"
                )
    
    # ---- Transfer Configuration ----
    if transfer_enabled:
        st.markdown("---")
        st.markdown("**Transfer Configuration**")
        
        # Determine initial mode
        legacy_mode = str(features.get("transfer_mode", "")).strip().lower()
        if legacy_mode in ("json_lookup", "lookup", "excel", "excel_lookup"):
            initial_mode = "Excel file"
        elif legacy_mode in ("manual_fixed", "fixed"):
            initial_mode = "Fixed cost"
        else:
            initial_mode = ""
        
        t1, t2, t3 = st.columns([1.2, 1.2, 1])
        
        with t1:
            transfer_mode = st.selectbox(
                "Transfer mode",
                options=["", "Excel file", "Fixed cost"],
                index=["", "Excel file", "Fixed cost"].index(initial_mode),
                key=skey("transfer_mode"),
                help="Excel file: pallets→truck_cost lookup. Fixed cost: single amount."
            )
        
        with t2:
            double_stack = st.checkbox(
                "Double Stack",
                value=bool(features.get("double_stack", False)),
                disabled=transfer_mode != "Excel file",
                key=skey("double_stack"),
                help="Only available for Excel file mode"
            )
        
        # Mode-specific fields
        transfer_excel_val = str(
            features.get("transfer_excel")
            or features.get("transfer_json")  # backward compatibility
            or ""
        )
        transfer_fixed_val = float(features.get("transfer_fixed", 0.0) or 0.0)
        
        tj_col, tf_col = st.columns(2)
        
        with tj_col:
            transfer_excel = st.text_input(
                "Excel file path",
                value=transfer_excel_val,
                disabled=transfer_mode != "Excel file",
                placeholder="e.g., data/transfer_rates_nl_svz.json",
                help="Path to JSON/Excel with 'pallets' and 'truck_cost' columns",
                key=skey("transfer_excel"),
            )
        
        with tf_col:
            transfer_fixed = st.number_input(
                "Fixed transfer cost (€ total)",
                min_value=0.0,
                step=1.0,
                value=transfer_fixed_val,
                disabled=transfer_mode != "Fixed cost",
                key=skey("transfer_fixed"),
            )
    
    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------
    
    # Message area (appears under action buttons)
    msg_area = st.empty()
    
    # Show persisted success message after rerun
    if "__flash_success" in st.session_state:
        msg_area.success(st.session_state["__flash_success"])
        del st.session_state["__flash_success"]
    
    # Save button
    if st.button("💾 Save changes", type="primary", key=skey("save_btn")):
        # Build updated warehouse payload
        safe_name = (new_name or "").strip() or selected_id
        
        features_payload = {
            "labeling": bool(labeling_enabled),
            "transfer": bool(transfer_enabled),
            "second_leg": bool(second_leg_enabled),
        }
        
        # Labeling details
        if labeling_enabled:
            use_advanced = bool(st.session_state.get(skey("use_advanced_labels"), False))
            
            if use_advanced:
                # Advanced mode: Simple/Complex
                simple_val = float(st.session_state.get(skey("spedka_simple"), 0.0) or 0.0)
                complex_val = float(st.session_state.get(skey("spedka_complex"), 0.0) or 0.0)
                labelling_val = float(st.session_state.get(skey("labelling_per_piece"), 0.0) or 0.0)
                
                # Primary: label_options
                features_payload["label_options"] = {
                    "simple": simple_val,
                    "complex": complex_val,
                }
                
                # Backward compatibility: label_costs
                features_payload["label_costs"] = {
                    "label": simple_val,
                    "labelling": labelling_val,
                }
            
            else:
                # Standard mode: Label + Labelling
                label_val = float(st.session_state.get(skey("label_per_piece"), 0.0) or 0.0)
                labelling_val = float(st.session_state.get(skey("labelling_per_piece"), 0.0) or 0.0)
                
                features_payload["label_costs"] = {
                    "label": label_val,
                    "labelling": labelling_val,
                }
        
        # Transfer details
        if transfer_enabled:
            if transfer_mode == "Excel file":
                features_payload["transfer_mode"] = "excel"
                features_payload["transfer_excel"] = str(transfer_excel or "").strip()
                features_payload["double_stack"] = bool(double_stack)
            
            elif transfer_mode == "Fixed cost":
                features_payload["transfer_mode"] = "fixed"
                features_payload["transfer_fixed"] = float(transfer_fixed or 0.0)
        
        # Complete payload
        payload = {
            "id": selected_id,
            "name": safe_name,
            "rates": {
                "inbound": float(new_inbound),
                "outbound": float(new_outbound),
                "storage": float(new_storage),
                "order_fee": float(new_order_fee),
            },
            "features": features_payload,
        }
        
        # Update catalog
        catalog.setdefault("warehouses", [])
        replaced = False
        
        for i, wh in enumerate(catalog["warehouses"]):
            if (wh.get("id") or "").strip() == selected_id:
                catalog["warehouses"][i] = payload
                replaced = True
                break
        
        if not replaced:
            catalog["warehouses"].append(payload)
        
        # Save
        try:
            save_catalog(catalog)
        except Exception as e:
            msg_area.error(f"❌ Save failed: {e}")
        else:
            msg_area.success(f"✅ Warehouse '{selected_id}' saved successfully!")
            st.toast("Changes saved", icon="✅")
            st.session_state["_next_select_id"] = selected_id
            st.session_state["__flash_success"] = f"✅ Warehouse '{selected_id}' saved"
            
            try:
                st.cache_data.clear()
            except Exception:
                pass
            
            st.rerun()
    
    # -------------------------------------------------------------------------
    # DELETE
    # -------------------------------------------------------------------------
    
    st.divider()
    
    if st.button("🗑️ Delete warehouse", type="secondary", key=skey("delete_btn")):
        st.session_state["__del_confirm__"] = True
    
    # Inline confirmation
    if st.session_state.get("__del_confirm__"):
        st.warning(f"⚠️ Are you sure you want to permanently delete '{selected_id}'?")
        
        c1, c2 = st.columns(2)
        
        with c1:
            if st.button("✅ Confirm delete", use_container_width=True, key=skey("confirm_delete")):
                # Remove from catalog
                catalog["warehouses"] = [
                    wh for wh in catalog.get("warehouses", [])
                    if (wh.get("id") or "").strip() != selected_id
                ]
                
                try:
                    save_catalog(catalog)
                except Exception as e:
                    msg_area.error(f"❌ Delete failed: {e}")
                else:
                    msg_area.success(f"🗑️ Warehouse '{selected_id}' deleted")
                    st.toast("Warehouse deleted", icon="🗑️")
                    
                    try:
                        st.cache_data.clear()
                    except Exception:
                        pass
                    
                    # Update navigation
                    remaining_ids = sorted([
                        w.get("id") for w in catalog.get("warehouses", [])
                        if w.get("id")
                    ])
                    
                    if remaining_ids:
                        st.session_state["_next_select_id"] = remaining_ids[0]
                    else:
                        st.session_state.pop("_next_select_id", None)
                        st.session_state.pop("update_wh_select_id", None)
                    
                    if st.session_state.get("last_added_id") == selected_id:
                        st.session_state.pop("last_added_id", None)
                    
                    st.session_state["__flash_success"] = f"🗑️ Warehouse '{selected_id}' deleted"
                
                finally:
                    st.session_state["__del_confirm__"] = False
                    st.rerun()
        
        with c2:
            if st.button("Cancel", use_container_width=True, key=skey("cancel_delete")):
                st.session_state["__del_confirm__"] = False
                st.rerun()
    
    # -------------------------------------------------------------------------
    # DEBUG INFO
    # -------------------------------------------------------------------------
    
    with st.expander("🔍 Debug Info", expanded=False):
        from services.catalog.config_manager import get_catalog_path
        
        catalog_path = get_catalog_path()
        st.code(f"Catalog file: {catalog_path}")
        
        if catalog_path.exists():
            st.success("✅ File exists")
            
            import json
            with open(catalog_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            st.json(data)
        else:
            st.error("❌ File does not exist")


# ============================================================================
# ALIAS
# ============================================================================

def view():
    """Alias for router compatibility."""
    page_update_warehouse()