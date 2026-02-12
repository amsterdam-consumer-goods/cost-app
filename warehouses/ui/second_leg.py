"""
Second Warehouse Leg UI Component
==================================

UI for calculating costs when goods are transferred to a second warehouse.

This module provides:
- Second warehouse selection (catalog-driven or legacy fallback)
- Cost calculation (fixed per order OR inbound/outbound/storage)
- Transport cost input
- Storage duration input
- Automatic primary warehouse exclusion

Pricing Models:
1. Fixed per order: Single flat rate (e.g., Slovakia/Arufel)
2. Variable: Inbound + Outbound + Storage + Order fee

Data Sources:
- Primary: data/catalog.json (second_leg configuration)
- Fallback: Legacy hardcoded rates (if catalog unavailable)

Related Files:
- data/catalog.json: Warehouse configurations
- services/config_manager.py: Catalog loading
- ui/generic.py: Main calculator orchestration
"""

from __future__ import annotations
from typing import Optional, TypedDict, Dict, Any, Tuple
import streamlit as st


# ============================================================================
# TYPE DEFINITIONS
# ============================================================================

class WhRates(TypedDict, total=False):
    """Warehouse rate structure for second leg calculation."""
    name: str
    inbound_per_pallet: float
    outbound_per_pallet: float
    storage_per_pallet_per_week: float
    order_fee: float
    fixed_per_order: float


# ============================================================================
# LEGACY RATES (Fallback)
# ============================================================================

LEGACY_TARGET_WAREHOUSE_RATES: Dict[str, WhRates] = {
    "Slovakia / Arufel": {
        "name": "Slovakia / Arufel",
        "fixed_per_order": 360.0
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


# ============================================================================
# CATALOG LOADING
# ============================================================================

def _build_targets_from_catalog(primary_label: str) -> Dict[str, WhRates]:
    """
    Build target warehouse rates from catalog.json.
    
    Process:
    1. Load catalog via config_manager
    2. Normalize warehouse data
    3. Extract rates for each warehouse
    4. Detect pricing model (fixed OR variable)
    5. Exclude primary warehouse from list
    
    Pricing Model Detection:
    - Fixed: second_leg.rules.type == "fixed_per_order"
    - Variable: Use standard rates (inbound/outbound/storage)
    
    Args:
        primary_label: Primary warehouse label to exclude
        
    Returns:
        Dict mapping warehouse label to WhRates
        Empty dict if catalog unavailable
    """
    try:
        from services.catalog.config_manager import load_catalog
        from services.catalog.catalog_adapter import normalize_catalog
    except Exception:
        return {}
    
    catalog = normalize_catalog(load_catalog())
    targets: Dict[str, WhRates] = {}
    
    for warehouse in catalog.get("warehouses", []) or []:
        # Build warehouse label
        country = (warehouse.get("country") or "").strip()
        name = (warehouse.get("name") or warehouse.get("id") or "Warehouse").strip()
        label = f"{country} / {name}" if country else name
        
        # Skip primary warehouse
        if label == primary_label:
            continue
        
        # Extract rates and features
        rates = warehouse.get("rates", {}) or {}
        features = warehouse.get("features", {}) or {}
        second_leg_config = features.get("second_leg", {})
        
        # Detect pricing model
        fixed_amount = None
        
        if isinstance(second_leg_config, dict):
            rules = second_leg_config.get("rules", {})
            if isinstance(rules, dict) and (rules.get("type") or "").lower() == "fixed_per_order":
                fixed_amount = float(rules.get("fixed_amount", features.get("second_leg_fixed", 360.0)))
        elif isinstance(second_leg_config, str) and second_leg_config.lower() == "fixed_per_order":
            fixed_amount = float(features.get("second_leg_fixed", 360.0))
        
        # Store rates
        if fixed_amount is not None:
            targets[label] = WhRates(
                name=label,
                fixed_per_order=float(fixed_amount)
            )
        else:
            targets[label] = WhRates(
                name=label,
                inbound_per_pallet=float(rates.get("inbound", 0.0)),
                outbound_per_pallet=float(rates.get("outbound", 0.0)),
                storage_per_pallet_per_week=float(rates.get("storage", 0.0)),
                order_fee=float(rates.get("order_fee", 0.0)),
            )
    
    return targets


def _effective_targets(primary_label: str) -> Dict[str, WhRates]:
    """
    Get effective target warehouse rates.
    
    Tries catalog first, falls back to legacy rates if unavailable.
    
    Args:
        primary_label: Primary warehouse to exclude
        
    Returns:
        Dict of target warehouse rates
    """
    dynamic_targets = _build_targets_from_catalog(primary_label)
    
    if dynamic_targets:
        return dynamic_targets
    else:
        return LEGACY_TARGET_WAREHOUSE_RATES.copy()


# ============================================================================
# COST CALCULATION
# ============================================================================

def _compute_second_leg_cost(
    rates_table: Dict[str, WhRates],
    target_wh: str,
    pallets: int,
    weeks_second_leg: int,
    transport_cost_second_leg: float,
) -> Tuple[float, Dict]:
    """
    Compute second warehouse leg cost.
    
    Supports two pricing models:
    1. Fixed per order: Single flat rate + transport
    2. Variable: Inbound + Outbound + Storage + Order fee + Transport
    
    Args:
        rates_table: Warehouse rates dictionary
        target_wh: Selected target warehouse label
        pallets: Number of pallets
        weeks_second_leg: Storage duration at target warehouse
        transport_cost_second_leg: Transport cost to target warehouse
        
    Returns:
        Tuple of (total_cost, breakdown_dict)
    """
    rates = rates_table[target_wh]
    
    breakdown: Dict[str, Any] = {
        "—— Second Warehouse Transfer ——": "",
        "Target Warehouse": target_wh,
    }
    
    # Fixed per order model
    if "fixed_per_order" in rates:
        fixed = float(rates["fixed_per_order"])
        subtotal = fixed + float(transport_cost_second_leg)
        
        breakdown.update({
            "Pricing Model": "Fixed per order",
            "Fixed per Order (€)": round(fixed, 2),
            "Transfer Transport (€)": round(transport_cost_second_leg, 2),
            "Transfer Subtotal (€)": round(subtotal, 2),
        })
        
        return subtotal, breakdown
    
    # Variable model (inbound/outbound/storage)
    inbound_cost = pallets * float(rates.get("inbound_per_pallet", 0.0))
    outbound_cost = pallets * float(rates.get("outbound_per_pallet", 0.0))
    storage_rate = float(rates.get("storage_per_pallet_per_week", 0.0))
    storage_cost = pallets * weeks_second_leg * storage_rate
    order_fee = float(rates.get("order_fee", 0.0))
    
    subtotal = inbound_cost + outbound_cost + storage_cost + order_fee + float(transport_cost_second_leg)
    
    breakdown.update({
        "Pricing Model": "Inbound/Outbound/Storage",
        "Inbound (€)": round(inbound_cost, 2),
        "Outbound (€)": round(outbound_cost, 2),
        "Storage (€)": round(storage_cost, 2),
        "Order Fee (€)": round(order_fee, 2),
        "Transfer Transport (€)": round(transport_cost_second_leg, 2),
        "Transfer Subtotal (€)": round(subtotal, 2),
    })
    
    return subtotal, breakdown


# ============================================================================
# UI COMPONENT
# ============================================================================

def second_leg_ui(
    primary_warehouse: str,
    pallets: int,
    pieces: Optional[int] = None,
) -> Tuple[float, Dict]:
    """
    Render second warehouse leg UI and calculate cost.
    
    Workflow:
    1. Show enable checkbox
    2. If enabled, show target warehouse selection
    3. Show storage duration input
    4. Show transport cost input
    5. Calculate and return cost
    
    Args:
        primary_warehouse: Primary warehouse name (excluded from targets)
        pallets: Number of pallets to transfer
        pieces: Number of pieces (optional, not currently used)
        
    Returns:
        Tuple of (added_cost, breakdown_dict)
        - added_cost: Total cost to add to VVP (0 if disabled)
        - breakdown_dict: Detailed cost breakdown for display
    """
    # Enable checkbox
    enabled = st.checkbox("Second warehouse transfer (optional)")
    
    if not enabled:
        return 0.0, {}
    
    # Load target warehouses
    rates_table = _effective_targets(primary_warehouse)
    options = list(rates_table.keys())
    
    if not options:
        st.warning("No target warehouses available.")
        return 0.0, {}
    
    # Target warehouse selection
    try:
        default_idx = options.index("Romania / Giurgiu")
    except ValueError:
        default_idx = 0
    
    target_wh = st.selectbox(
        "Target warehouse",
        options,
        index=default_idx,
        help="Warehouse where goods will be transferred"
    )
    
    # Input fields
    c1, c2 = st.columns(2)
    
    with c1:
        weeks_second_leg = st.number_input(
            "Weeks in storage (at target)",
            min_value=0,
            step=1,
            value=2,
            format="%d",
            help="Storage duration at target warehouse"
        )
    
    with c2:
        transport_cost_second_leg = st.number_input(
            "Transfer transport cost (€ total)",
            min_value=0.0,
            step=1.0,
            value=0.0,
            format="%.2f",
            help="Transport from primary to target warehouse"
        )
    
    # Calculate cost
    subtotal, breakdown = _compute_second_leg_cost(
        rates_table=rates_table,
        target_wh=target_wh,
        pallets=int(max(0, pallets)),
        weeks_second_leg=int(max(0, weeks_second_leg)),
        transport_cost_second_leg=float(transport_cost_second_leg),
    )
    
    # Add to breakdown
    breakdown.update({
        "Include in VVP?": True,
        "Second Warehouse Transfer Added to VVP (€)": round(subtotal, 2),
    })
    
    return subtotal, breakdown