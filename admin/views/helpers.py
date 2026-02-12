"""
Warehouse Configuration Helpers
================================

This module provides utility functions for managing warehouse configurations
in the admin interface. It handles:

- Default data structures for rates and features
- Data normalization and validation
- UI component rendering for rates and features
- File upload handling for transfer rate tables
- Advanced labeling support (optional simple/complex pricing)

Labeling System:
- Standard mode: Label + Labelling (basic cost structure)
- Advanced mode: Simple/Complex labels + Labelling (optional upgrade)
  - Any warehouse can use advanced mode via checkbox
  - Provides two-tier pricing flexibility

Used by: add_warehouse.py, update_warehouse.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st


# ============================================================================
# DEFAULT STRUCTURES
# ============================================================================

def default_rates() -> Dict[str, float]:
    """
    Return default warehouse rate structure with zero values.
    
    Returns:
        Dict with keys: inbound, outbound, storage, order_fee
    """
    return {
        "inbound": 0.0,
        "outbound": 0.0,
        "storage": 0.0,
        "order_fee": 0.0,
    }


def default_features() -> Dict[str, Any]:
    """
    Return default warehouse features structure.
    
    Includes:
    - labeling: Basic label_costs structure
    - label_options: SPEDKA-style simple/complex options
    - transfer: Transfer configuration (mode, costs, lookup file)
    - double_stack: Boolean flag for double-stacking capability
    - second_leg: Second warehouse transfer configuration
    
    Returns:
        Complete features dictionary with all default values
    """
    return {
        "labeling": False,
        "label_costs": {
            "label": 0.0,
            "labelling": 0.0,
        },
        "label_options": {
            "simple": 0.0,
            "complex": 0.0,
        },
        "transfer": False,
        "transfer_mode": "none",
        "transfer_excel": "",
        "transfer_fixed": 0.0,
        "double_stack": False,
        "second_leg": False,
    }


# ============================================================================
# WAREHOUSE IDENTIFICATION
# ============================================================================

def has_advanced_labeling(features: Dict[str, Any]) -> bool:
    """
    Check if warehouse uses advanced labeling (simple/complex options).
    
    Detection logic:
    - Checks if label_options exists and has valid values
    
    Args:
        features: Warehouse features dictionary
        
    Returns:
        True if advanced labeling is configured, False otherwise
    """
    label_opts = features.get("label_options")
    if not isinstance(label_opts, dict):
        return False
    
    simple = float(label_opts.get("simple", 0.0) or 0.0)
    complex_val = float(label_opts.get("complex", 0.0) or 0.0)
    
    return simple > 0 or complex_val > 0


# ============================================================================
# DATA NORMALIZATION
# ============================================================================

def normalize_rates(raw: Any) -> Dict[str, float]:
    """
    Normalize rates data to standard structure, filling missing values with defaults.
    
    Args:
        raw: Raw rates data (dict or any type)
        
    Returns:
        Normalized rates dict with all required keys
    """
    base = default_rates()
    if not isinstance(raw, dict):
        return base
        
    return {
        "inbound": float(raw.get("inbound", base["inbound"]) or 0.0),
        "outbound": float(raw.get("outbound", base["outbound"]) or 0.0),
        "storage": float(raw.get("storage", base["storage"]) or 0.0),
        "order_fee": float(raw.get("order_fee", base["order_fee"]) or 0.0),
    }


def normalize_features(raw: Any) -> Dict[str, Any]:
    """
    Normalize features data to standard structure.
    
    Handles legacy formats and ensures all required keys are present.
    Supports both label_costs (legacy) and label_options (SPEDKA) formats.
    
    Args:
        raw: Raw features data
        
    Returns:
        Normalized features dict with standard structure
    """
    base = default_features()
    if not isinstance(raw, dict):
        return base
        
    out = dict(base)
    
    # Labeling
    out["labeling"] = bool(raw.get("labeling", False))
    
    # Label costs (legacy format for non-SPEDKA warehouses)
    label_costs = raw.get("label_costs")
    if isinstance(label_costs, dict):
        out["label_costs"] = {
            "label": float(label_costs.get("label", 0.0) or 0.0),
            "labelling": float(label_costs.get("labelling", 0.0) or 0.0),
        }
    
    # Label options (SPEDKA format)
    label_options = raw.get("label_options")
    if isinstance(label_options, dict):
        out["label_options"] = {
            "simple": float(label_options.get("simple", 0.0) or 0.0),
            "complex": float(label_options.get("complex", 0.0) or 0.0),
        }
    
    # Transfer
    out["transfer"] = bool(raw.get("transfer", False))
    out["transfer_mode"] = str(raw.get("transfer_mode", "none"))
    out["transfer_excel"] = str(raw.get("transfer_excel", ""))
    out["transfer_fixed"] = float(raw.get("transfer_fixed", 0.0) or 0.0)
    out["double_stack"] = bool(raw.get("double_stack", False))
    
    # Second leg
    out["second_leg"] = bool(raw.get("second_leg", False))
    
    return out


# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_rates_inputs(prefix: str, rates: Dict[str, float]) -> Dict[str, float]:
    """
    Render rate input fields and return updated values.
    
    Args:
        prefix: Unique prefix for widget keys (ensures isolation between warehouses)
        rates: Current rate values
        
    Returns:
        Dictionary with updated rate values from user input
    """
    st.subheader("Rates (€)")
    
    c1, c2 = st.columns(2)
    with c1:
        inbound = st.number_input(
            "Inbound €/pallet",
            value=float(rates.get("inbound", 0.0)),
            key=f"{prefix}_rate_inbound",
            min_value=0.0,
            step=0.5,
            format="%.2f",
        )
        storage = st.number_input(
            "Storage €/pallet/week",
            value=float(rates.get("storage", 0.0)),
            key=f"{prefix}_rate_storage",
            min_value=0.0,
            step=0.5,
            format="%.2f",
        )
    
    with c2:
        outbound = st.number_input(
            "Outbound €/pallet",
            value=float(rates.get("outbound", 0.0)),
            key=f"{prefix}_rate_outbound",
            min_value=0.0,
            step=0.5,
            format="%.2f",
        )
        order_fee = st.number_input(
            "Order fee €",
            value=float(rates.get("order_fee", 0.0)),
            key=f"{prefix}_rate_order_fee",
            min_value=0.0,
            step=0.5,
            format="%.2f",
        )
    
    return {
        "inbound": float(inbound),
        "outbound": float(outbound),
        "storage": float(storage),
        "order_fee": float(order_fee),
    }


def render_labeling_inputs(
    prefix: str,
    warehouse_id: str,
    warehouse_name: str,
    features: Dict[str, Any],
    labeling_enabled: bool,
) -> Dict[str, Any]:
    """
    Render labeling configuration inputs.
    
    Supports two modes:
    1. Standard mode: Label + Labelling (basic cost structure)
    2. Advanced mode: Simple/Complex labels + Labelling (optional upgrade)
    
    The advanced mode is optional for ALL warehouses via checkbox.
    
    Args:
        prefix: Unique widget key prefix
        warehouse_id: Warehouse identifier
        warehouse_name: Warehouse display name
        features: Current feature configuration
        labeling_enabled: Whether labeling is currently enabled
        
    Returns:
        Dictionary with updated labeling configuration
    """
    if not labeling_enabled:
        return {
            "type": "label_costs",
            "label_costs": {"label": 0.0, "labelling": 0.0},
        }
    
    st.markdown("**Label Configuration**")
    
    # Check if advanced labeling is currently enabled
    label_opts = features.get("label_options", {}) or {}
    has_advanced = has_advanced_labeling(features)
    
    # Checkbox for advanced mode
    use_advanced = st.checkbox(
        "Enable advanced labeling (Simple/Complex options)",
        value=has_advanced,
        key=f"{prefix}_use_advanced_labels",
        help="Use two-tier labeling system with different costs for simple and complex labels"
    )
    
    # Get current values
    label_costs = features.get("label_costs", {}) or {}
    current_label = float(label_costs.get("label", 0.0) or 0.0)
    current_labelling = float(label_costs.get("labelling", 0.0) or 0.0)
    
    current_simple = float(label_opts.get("simple", 0.0) or 0.0)
    current_complex = float(label_opts.get("complex", 0.0) or 0.0)
    
    # If switching from standard to advanced, use label value as simple default
    if use_advanced and current_simple == 0.0 and current_label > 0.0:
        current_simple = current_label
    
    # If switching from advanced to standard, use simple value as label default
    if not use_advanced and current_label == 0.0 and current_simple > 0.0:
        current_label = current_simple
    
    if use_advanced:
        # ADVANCED MODE
        st.caption("⚡ Advanced mode: Two-tier labeling system")
        
        c1, c2, c3 = st.columns(3)
        
        with c1:
            # Label input (disabled in advanced mode)
            st.number_input(
                "Label (€/piece)",
                min_value=0.0,
                step=0.001,
                format="%.3f",
                value=0.0,
                disabled=True,
                key=f"{prefix}_label_cost_disabled",
                help="Disabled in advanced mode - use Simple label instead"
            )
        
        with c2:
            simple = st.number_input(
                "Simple label (€/piece)",
                min_value=0.0,
                step=0.001,
                format="%.3f",
                value=current_simple,
                key=f"{prefix}_label_simple",
                help="Standard label application cost"
            )
        
        with c3:
            complex_val = st.number_input(
                "Complex label (€/piece)",
                min_value=0.0,
                step=0.001,
                format="%.3f",
                value=current_complex,
                key=f"{prefix}_label_complex",
                help="Complex label with additional requirements"
            )
        
        # Labelling (always available)
        labelling = st.number_input(
            "Labelling service (€/piece)",
            min_value=0.0,
            step=0.001,
            format="%.3f",
            value=current_labelling,
            key=f"{prefix}_labelling_cost",
            help="Service fee per piece (applies to both simple and complex)"
        )
        
        return {
            "type": "label_options",
            "label_options": {
                "simple": float(simple),
                "complex": float(complex_val),
            },
            "label_costs": {
                "label": float(simple),  # For backward compatibility
                "labelling": float(labelling),
            }
        }
    
    else:
        # STANDARD MODE
        st.caption("Standard mode: Basic cost structure")
        
        c1, c2 = st.columns(2)
        
        with c1:
            label = st.number_input(
                "Label (€/piece)",
                min_value=0.0,
                step=0.001,
                format="%.3f",
                value=current_label,
                key=f"{prefix}_label_cost",
                help="Label material cost per piece"
            )
        
        with c2:
            labelling = st.number_input(
                "Labelling service (€/piece)",
                min_value=0.0,
                step=0.001,
                format="%.3f",
                value=current_labelling,
                key=f"{prefix}_labelling_cost",
                help="Labeling service fee per piece"
            )
        
        return {
            "type": "label_costs",
            "label_costs": {
                "label": float(label),
                "labelling": float(labelling),
            }
        }


def render_transfer_inputs(
    prefix: str,
    warehouse_id: str,
    features: Dict[str, Any],
    transfer_enabled: bool,
) -> Dict[str, Any]:
    """
    Render transfer configuration inputs.
    
    Supports two modes:
    - Excel file: Uses lookup table (pallets -> truck_cost)
    - Fixed cost: Single fixed transfer cost
    
    Args:
        prefix: Unique widget key prefix
        warehouse_id: Warehouse identifier (used for default file paths)
        features: Current feature configuration
        transfer_enabled: Whether transfer is currently enabled
        
    Returns:
        Dictionary with updated transfer configuration
    """
    st.markdown("**Transfer Configuration**")
    
    # Determine initial mode
    legacy_mode = str(features.get("transfer_mode", "")).strip().lower()
    if legacy_mode in ("json_lookup", "lookup", "excel", "excel_lookup"):
        initial_mode = "Excel file"
    elif legacy_mode in ("manual_fixed", "fixed"):
        initial_mode = "Fixed cost"
    else:
        initial_mode = ""
    
    # Mode selection
    transfer_mode = st.selectbox(
        "Transfer mode",
        options=["", "Excel file", "Fixed cost"],
        index=["", "Excel file", "Fixed cost"].index(initial_mode) if transfer_enabled else 0,
        disabled=not transfer_enabled,
        help="Excel file: pallets→truck_cost lookup table. Fixed cost: single total amount.",
        key=f"{prefix}_transfer_mode",
    )
    
    # Double stack (only for Excel mode)
    double_stack = st.checkbox(
        "Double stack available",
        value=bool(features.get("double_stack", False)),
        disabled=not transfer_enabled or transfer_mode != "Excel file",
        help="Halves pallet count when looking up truck costs",
        key=f"{prefix}_double_stack",
    )
    
    # Mode-specific inputs
    transfer_excel = ""
    transfer_fixed = 0.0
    
    if transfer_mode == "Excel file":
        transfer_excel = st.text_input(
            "Excel file path",
            value=str(features.get("transfer_excel") or features.get("transfer_json") or ""),
            disabled=not transfer_enabled,
            placeholder=f"e.g., data/transfer_rates_{warehouse_id}.json",
            help="Path to JSON/Excel file with 'pallets' and 'truck_cost' columns",
            key=f"{prefix}_transfer_excel",
        )
    
    elif transfer_mode == "Fixed cost":
        transfer_fixed = st.number_input(
            "Fixed transfer cost (€ total)",
            min_value=0.0,
            step=1.0,
            value=float(features.get("transfer_fixed", 0.0) or 0.0),
            disabled=not transfer_enabled,
            key=f"{prefix}_transfer_fixed",
        )
    
    # Convert mode label to canonical format
    if transfer_mode == "Excel file":
        mode_canonical = "excel"
    elif transfer_mode == "Fixed cost":
        mode_canonical = "fixed"
    else:
        mode_canonical = "none"
    
    return {
        "transfer_mode": mode_canonical if transfer_enabled else "none",
        "transfer_excel": str(transfer_excel).strip() if transfer_enabled else "",
        "transfer_fixed": float(transfer_fixed) if transfer_enabled else 0.0,
        "double_stack": bool(double_stack) if transfer_enabled else False,
    }


# ============================================================================
# VALIDATION
# ============================================================================

def validate_warehouse_data(warehouse_id: str, warehouse_name: str) -> tuple[bool, str]:
    """
    Validate warehouse data before saving.
    
    Args:
        warehouse_id: Warehouse ID to validate
        warehouse_name: Warehouse name to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - (True, "") if valid
        - (False, error_message) if invalid
    """
    if not warehouse_id or not warehouse_id.strip():
        return False, "Warehouse ID is required"
    
    if not warehouse_name or not warehouse_name.strip():
        return False, "Warehouse name is required"
    
    # Check for invalid characters in ID
    wid = warehouse_id.strip()
    if not all(c.isalnum() or c in "_-" for c in wid):
        return False, "Warehouse ID can only contain letters, numbers, underscores, and hyphens"
    
    return True, ""


# ============================================================================
# FILE UPLOAD HANDLING
# ============================================================================

def handle_transfer_file_upload(
    uploaded_file,
    warehouse_id: str,
    app_root: Path,
) -> tuple[bool, str, str]:
    """
    Handle uploaded transfer rate file (JSON or Excel).
    
    Args:
        uploaded_file: Streamlit uploaded file object
        warehouse_id: Warehouse ID for default naming
        app_root: Application root directory
        
    Returns:
        Tuple of (success, file_path, error_message)
        - (True, path, "") if successful
        - (False, "", error_msg) if failed
    """
    try:
        data_dir = app_root / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        target_rel = Path(f"data/transfer_rates_{warehouse_id}.json")
        target_abs = app_root / target_rel
        
        if uploaded_file.name.lower().endswith(".json"):
            content = json.loads(uploaded_file.getvalue().decode("utf-8"))
            with open(target_abs, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
        
        else:  # Excel
            try:
                import pandas as pd
            except ImportError:
                return False, "", "Excel upload requires pandas. Please install pandas or upload JSON."
            
            df = pd.read_excel(uploaded_file)
            cols_lower = {c: c.lower() for c in df.columns}
            df = df.rename(columns=cols_lower)
            
            if not {"pallets", "truck_cost"}.issubset(df.columns):
                return False, "", "Excel must contain columns: 'pallets' and 'truck_cost'"
            
            data = [
                {
                    "pallets": int(row.pallets),
                    "truck_cost": float(row.truck_cost),
                }
                for row in df[["pallets", "truck_cost"]].itertuples(index=False)
            ]
            
            with open(target_abs, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        file_path = str(target_rel).replace("\\", "/")
        return True, file_path, ""
    
    except Exception as e:
        return False, "", f"Failed to process file: {str(e)}"


# ============================================================================
# WAREHOUSE LIST UTILITIES
# ============================================================================

def get_warehouse_ids(catalog: Dict[str, Any], list_warehouses_func) -> List[str]:
    """
    Extract warehouse IDs from catalog.
    
    Args:
        catalog: Catalog dictionary
        list_warehouses_func: Function to list warehouses from catalog
        
    Returns:
        Sorted list of warehouse IDs
    """
    return sorted([
        w.get("id")
        for w in list_warehouses_func(catalog)
        if w.get("id")
    ])