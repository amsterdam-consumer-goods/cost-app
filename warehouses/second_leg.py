# warehouses/second_leg.py
"""
Catalog-driven second-warehouse transfer UI.
Returns (added_cost, breakdown). Uses catalog if available, else legacy rates.
"""

from __future__ import annotations
from typing import Optional, TypedDict, Dict, Any
import streamlit as st

__all__ = ["second_leg_ui"]

class WhRates(TypedDict, total=False):
    name: str
    inbound_per_pallet: float
    outbound_per_pallet: float
    storage_per_pallet_per_week: float
    order_fee: float
    fixed_per_order: float

LEGACY_TARGET_WAREHOUSE_RATES: dict[str, WhRates] = {
    "Slovakia / Arufel": {"name": "Slovakia / Arufel", "fixed_per_order": 360.0},
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

def _build_targets_from_catalog(primary_label: str) -> dict[str, WhRates]:
    """Build {label -> WhRates} from catalog.json; exclude primary warehouse."""
    try:
        from services.config_manager import load_catalog
        from services.catalog_adapter import normalize_catalog
    except Exception:
        return {}
    cat = normalize_catalog(load_catalog())
    out: dict[str, WhRates] = {}
    for w in cat.get("warehouses", []) or []:
        country = (w.get("country") or "").strip()
        name = (w.get("name") or w.get("id") or "Warehouse").strip()
        label = f"{country} / {name}" if country else name
        if label == primary_label:
            continue
        rates = w.get("rates", {}) or {}
        features = w.get("features", {}) or {}
        sec_cfg = features.get("second_leg", {})
        fixed_amount = None
        if isinstance(sec_cfg, dict):
            rules = sec_cfg.get("rules", {})
            if isinstance(rules, dict) and (rules.get("type") or "").lower() == "fixed_per_order":
                fixed_amount = float(rules.get("fixed_amount", features.get("second_leg_fixed", 360.0)))
        elif isinstance(sec_cfg, str) and sec_cfg.lower() == "fixed_per_order":
            fixed_amount = float(features.get("second_leg_fixed", 360.0))
        if fixed_amount is not None:
            out[label] = WhRates(name=label, fixed_per_order=float(fixed_amount))
        else:
            out[label] = WhRates(
                name=label,
                inbound_per_pallet=float(rates.get("inbound", 0.0)),
                outbound_per_pallet=float(rates.get("outbound", 0.0)),
                storage_per_pallet_per_week=float(rates.get("storage", 0.0)),
                order_fee=float(rates.get("order_fee", 0.0)),
            )
    return out

def _effective_targets(primary_label: str) -> dict[str, WhRates]:
    dynamic = _build_targets_from_catalog(primary_label)
    return dynamic if dynamic else LEGACY_TARGET_WAREHOUSE_RATES.copy()

def _compute_second_leg_cost(
    rates_table: dict[str, WhRates],
    target_wh: str,
    pallets: int,
    weeks_second_leg: int,
    transport_cost_second_leg: float,
) -> tuple[float, dict]:
    """Compute second-warehouse cost using the given rates table."""
    rates = rates_table[target_wh]
    breakdown: dict[str, Any] = {"—— Second Warehouse Transfer ——": "", "Target Warehouse": target_wh}
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
        "Transfer Transport (€)": round(transport_cost_second_leg, 2),
        "Transfer Subtotal (€)": round(subtotal, 2),
    })
    return subtotal, breakdown

def second_leg_ui(
    primary_warehouse: str,
    pallets: int,
    pieces: Optional[int] = None,
) -> tuple[float, dict]:
    """Render UI and return (added_cost, breakdown)."""
    enabled = st.checkbox("Second warehouse transfer (optional)")
    if not enabled:
        return 0.0, {}
    rates_table = _effective_targets(primary_warehouse)
    options = list(rates_table.keys())
    if not options:
        st.warning("No target warehouses available.")
        return 0.0, {}
    try:
        default_idx = options.index("Romania / Giurgiu")
    except ValueError:
        default_idx = 0
    target_wh = st.selectbox("Target warehouse", options, index=default_idx)
    c1, c2 = st.columns(2)
    with c1:
        weeks_second_leg = st.number_input(
            "Weeks in storage (at target)", min_value=0, step=1, value=2, format="%d",
            help="Number of weeks the goods will stay at the target warehouse.",
        )
    with c2:
        transport_cost_second_leg = st.number_input(
            "Transfer transport cost (€ total)", min_value=0.0, step=1.0, value=0.0, format="%.2f",
            help="Transportation from the primary to the target warehouse.",
        )
    subtotal, breakdown = _compute_second_leg_cost(
        rates_table=rates_table,
        target_wh=target_wh,
        pallets=int(max(0, pallets)),
        weeks_second_leg=int(max(0, weeks_second_leg)),
        transport_cost_second_leg=float(transport_cost_second_leg),
    )
    added = subtotal
    breakdown.update({"Include in VVP?": True, "Second Warehouse Transfer Added to VVP (€)": round(added, 2)})
    return added, breakdown
