# warehouses/final_calc.py
"""
Final calculator page and final P&L step with automatic France delivery cost lookup.
SVZ kuralı: FR oto-delivery sadece SVZ warehouse seçiliyken çalışır.
Eşleştirme esnek: id tam eşleşmesi + 'svz' token/alt-dize kontrolü.
"""

from __future__ import annotations
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

# -------------------------------------------------------------------------
# SVZ allow-list ve esnek eşleştirme için pattern'lar
# -------------------------------------------------------------------------
ALLOWED_AUTO_FR_WAREHOUSES: set[str] = {
    "nl_svz",   # ana id
    "svz",      # olası kısa alias
}
ALLOWED_TOKEN_HINTS: tuple[str, ...] = (
    "svz",      # id içinde bu token varsa SVZ say
)

# ---------------------------- Cache Helpers ------------------------------

@st.cache_data(show_spinner=False, ttl=300)
def _load_json_with_mtime(path: str, mtime: float):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _safe_read_json(path: str):
    if not os.path.exists(path):
        return None
    try:
        mtime = os.path.getmtime(path)
        return _load_json_with_mtime(path, mtime)
    except Exception as e:
        st.error(f"Could not read JSON file.\n\nError: {e}")
        return None

def _load_customers_from_catalog() -> tuple[List[Dict[str, Any]], Optional[str]]:
    """
    CRITICAL FIX: Remove @st.cache_data to always load fresh customer data.
    This ensures newly added customers appear immediately in the dropdown.
    """
    try:
        from services.catalog import load as load_catalog, path as catalog_path
        from services.catalog_adapter import normalize_catalog
    except Exception:
        return [], None

    try:
        cat = normalize_catalog(load_catalog())
        rows = cat.get("customers") or cat.get("clients") or []
        if not isinstance(rows, list):
            return [], None

        norm_rows: List[Dict[str, Any]] = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            name = str(r.get("name", "")).strip()
            if not name:
                continue
            addrs_raw = r.get("addresses") or r.get("warehouses") or []
            seen, addrs = set(), []
            for a in (addrs_raw if isinstance(addrs_raw, list) else [addrs_raw]):
                s = str(a).strip()
                if s and s not in seen:
                    addrs.append(s)
                    seen.add(s)
            norm_rows.append({"name": name, "addresses": addrs})
        p = catalog_path()
        return norm_rows, (str(p) if p else "data/catalog.json")
    except Exception:
        return [], None

BASE_DIR = Path(__file__).resolve().parents[1]
FR_JSON_PATH = BASE_DIR / "data" / "fr_delivery_rates.json"

@st.cache_data(show_spinner=False, ttl=300)
def _load_fr_table() -> list[dict]:
    if not FR_JSON_PATH.exists():
        st.warning(f"France delivery rates JSON not found: {FR_JSON_PATH}")
        return []
    try:
        with open(FR_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        st.error(f"France delivery rates JSON could not be read: {e}")
        return []
    out: list[dict] = []
    for r in (data if isinstance(data, list) else []):
        try:
            d = str(r.get("dept", "")).zfill(2)[:2]
            p = int(r.get("pallets"))
            t = float(r.get("total"))
            if d and 1 <= int(d) <= 95 and p >= 1 and t >= 0:
                out.append({"dept": d, "pallets": p, "total": t})
        except Exception:
            continue
    return out

# ---------------------------- Address Utils ------------------------------

def _fr_guess_zip(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    m = re.search(r"\b(\d{5})\b", s)
    return m.group(1) if m else None

def _is_es_address(s: Optional[str]) -> bool:
    if not s:
        return False
    s_l = s.lower()
    es_words = ("spain", "españa", "espana", "espagne", "spanje")
    if any(w in s_l for w in es_words):
        return True
    if re.search(r"\bES\b|\bES-\b|\(ES\)", s, flags=re.IGNORECASE):
        return True
    return False

def _is_fr_address(s: Optional[str]) -> bool:
    if not s:
        return False
    if _is_es_address(s):
        return False
    s_l = s.lower()
    if ("france" in s_l) or ("frankrijk" in s_l):
        return True
    if re.search(r"\bFR\b|\bFR-\b|\(FR\)", s, flags=re.IGNORECASE):
        return True
    m = re.search(r"\b(\d{5})\b", s_l)
    if m:
        try:
            d = int(m.group(1)[:2])
            if 1 <= d <= 95:
                if re.search(r"\bFR\b|\bFR-\b|\(FR\)|france|frankrijk", s, flags=re.IGNORECASE):
                    return True
        except Exception:
            pass
    return False

# ---------------------------- Warehouse Gate -----------------------------

def _normalize_id(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    x = str(s).strip().lower()
    x = re.sub(r"[^a-z0-9]+", "_", x)
    x = re.sub(r"_+", "_", x).strip("_")
    return x

def _tokens(s: str) -> List[str]:
    return [t for t in re.split(r"[_\-\s/\\]+", s) if t]

def _current_warehouse_id() -> Optional[str]:
    candidates = (
        "warehouse_id",
        "selected_warehouse_id",
        "selected_warehouse",
        "warehouse",
        "wh_id",
        "current_warehouse_id",
    )
    for key in candidates:
        if key in st.session_state and st.session_state.get(key):
            return _normalize_id(st.session_state.get(key))
    return None

def _is_allowed_auto_fr() -> bool:
    wid = _current_warehouse_id()
    if not wid:
        return False
    if wid in ALLOWED_AUTO_FR_WAREHOUSES:
        return True
    toks = set(_tokens(wid))
    if any(hint in wid for hint in ALLOWED_TOKEN_HINTS):
        return True
    if any(hint in toks for hint in ALLOWED_TOKEN_HINTS):
        return True
    return False

# ---------------------------- FR Table Lookup ----------------------------

def _fr_effective_pallets(pallets_in: int) -> int:
    p = int(pallets_in or 0)
    if p <= 0:
        return 1
    if p >= 33:
        return 33
    return p

def _fr_lookup_total(zip_code: str, pallets_in: int) -> float:
    table = _load_fr_table()
    if not table:
        return 0.0
    dept = str(zip_code)[:2].zfill(2)
    try:
        if not (1 <= int(dept) <= 95):
            return 0.0
    except Exception:
        return 0.0
    eff_p = _fr_effective_pallets(pallets_in)
    drows = [r for r in table if r["dept"] == dept]
    if not drows:
        return 0.0
    exact = next((r for r in drows if r["pallets"] == eff_p), None)
    if exact:
        return float(exact["total"])
    lowers = [r for r in drows if r["pallets"] <= eff_p]
    if lowers:
        lowers.sort(key=lambda x: x["pallets"])
        return float(lowers[-1]["total"])
    drows.sort(key=lambda x: x["pallets"])
    return float(drows[0]["total"])

# ---------------------------- UI Helpers --------------------------------

def _get_customers(data: List[Dict[str, Any]]) -> List[str]:
    names = [str(x.get("name", "")).strip() for x in data]
    names = [n for n in names if n and n.lower() != "nan"]
    names.sort()
    return names

def _get_addresses_for(data: List[Dict[str, Any]], customer: str) -> List[str]:
    for row in data:
        if str(row.get("name", "")).strip().casefold() == customer.strip().casefold():
            raw = row.get("addresses", []) or []
            out, seen = [], set()
            for x in raw:
                s = str(x).strip()
                if s and s not in seen:
                    out.append(s)
                    seen.add(s)
            return out
    return []

# ---------------------------- Main Entry --------------------------------

def final_calculator(pieces: int, vvp_cost_per_piece_rounded: float):
    st.subheader("Final Calculator")

    # CRITICAL FIX: Always load fresh customer data (no caching)
    rows, catalog_source = _load_customers_from_catalog()
    used_source: Optional[str] = None
    if rows:
        used_source = catalog_source or "data/catalog.json"
    else:
        legacy = _safe_read_json("data/customers.json")
        if legacy is None:
            st.error("Customer data not found in catalog.json or data/customers.json.")
            st.stop()
        rows = legacy if isinstance(legacy, list) else []
        used_source = os.path.abspath("data/customers.json")

    customers = _get_customers(rows)
    
    # CRITICAL FIX: Reset customer selection when list changes
    if "final_calc_customers_hash" not in st.session_state:
        st.session_state["final_calc_customers_hash"] = str(customers)
    elif st.session_state["final_calc_customers_hash"] != str(customers):
        # Customer list changed, reset selection
        st.session_state["final_calc_customers_hash"] = str(customers)
        if "final_calc_selected_customer" in st.session_state:
            del st.session_state["final_calc_selected_customer"]
        if "final_calc_selected_warehouse" in st.session_state:
            del st.session_state["final_calc_selected_warehouse"]
    
    customer = st.selectbox(
        "Customer", 
        ["-- Select --"] + customers, 
        index=0,
        key="final_calc_selected_customer"
    ) if customers else None

    customer_wh = None
    if customer and customer != "-- Select --":
        addrs = _get_addresses_for(rows, customer)
        if addrs:
            customer_wh = st.selectbox(
                "Customer Warehouse", 
                ["-- Select --"] + addrs, 
                index=0,
                key="final_calc_selected_warehouse"
            )
        else:
            st.warning("No warehouse address found for the selected customer.")

    # ---------------------------------------------------------------------
    # France auto-delivery: FR adres + ALLOWED warehouse
    # ---------------------------------------------------------------------
    st.session_state.pop("__fr_auto_delivery_total", None)
    is_allowed_fr = _is_allowed_auto_fr()

    if customer_wh and customer_wh != "-- Select --" and _is_fr_address(customer_wh) and is_allowed_fr:
        guess_zip = _fr_guess_zip(customer_wh)
        pallets_global = int(st.session_state.get("pallets", 0))
        if guess_zip and pallets_global > 0:
            fr_auto_total = _fr_lookup_total(guess_zip, pallets_global)
            if fr_auto_total and fr_auto_total > 0:
                st.session_state["__fr_auto_delivery_total"] = float(fr_auto_total)
                eff_p = _fr_effective_pallets(pallets_global)
                st.caption(
                    f"🇫🇷 France delivery auto-cost: dept **{guess_zip[:2]}**, "
                    f"pallets **{eff_p}{' (full truck)' if eff_p == 33 else ''}** "
                    f"→ **€{fr_auto_total:.2f}** (FR JSON)"
                )
            else:
                st.warning("France auto-cost lookup failed (check fr_delivery_rates.json).")
        elif guess_zip and pallets_global <= 0:
            st.info("Enter pallet count at the beginning to enable France auto-cost.")
        else:
            st.warning("France address detected but no 5-digit postal code was found in the address.")
    else:
        if customer_wh and customer_wh != "-- Select --" and _is_fr_address(customer_wh) and not is_allowed_fr:
            st.info("FR address detected, but auto-delivery is only enabled for SVZ.")
        st.session_state.pop("__fr_auto_delivery_total", None)

    # ---------------- Numbers & Summary ----------------
    c1, c2, c3 = st.columns(3)
    with c1:
        purchase_price_per_piece = st.number_input(
            "Purchase Price per Piece (€)", min_value=0.0, step=0.001, format="%.3f"
        )
    with c2:
        sales_price_per_piece = st.number_input(
            "Sales Price per Piece (€)", min_value=0.0, step=0.001, format="%.3f"
        )
    with c3:
        default_delivery = float(st.session_state.get("__fr_auto_delivery_total", 0.0))
        delivery_transport_total = st.number_input(
            "Delivery Transportation Cost (TOTAL €)",
            min_value=0.0,
            step=1.0,
            value=default_delivery,
            format="%.2f",
            help="Total delivery transport cost for this order (not per piece).",
        )

    unit_vvp = float(vvp_cost_per_piece_rounded)
    unit_purchase = float(purchase_price_per_piece)
    unit_delivery = (delivery_transport_total / pieces) if pieces else 0.0

    unit_gross_cost = unit_vvp + unit_purchase
    total_gross_cost = unit_gross_cost * pieces
    total_revenue = sales_price_per_piece * pieces
    gross_profit = total_revenue - total_gross_cost
    net_profit = total_revenue - total_gross_cost - delivery_transport_total

    gross_margin_pct = (gross_profit / total_revenue * 100.0) if total_revenue > 0 else 0.0
    net_margin_pct = (net_profit / total_revenue * 100.0) if total_revenue > 0 else 0.0
    total_cost = (unit_gross_cost * pieces) + delivery_transport_total

    st.caption(
        f"Rounded VVP Cost / pc: **€{unit_vvp:.2f}**  |  "
        f"Purchase / pc: **€{unit_purchase:.3f}**  |  "
        f"Delivery Transport / pc: **€{unit_delivery:.4f}**  |  "
        f"Pieces: **{pieces}**"
    )

    st.markdown("---")
    st.subheader("Summary")

    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        st.metric("Total Cost (€)", f"{total_cost:.2f}")
    with r1c2:
        st.metric("Unit Cost (€ / pc)", f"{unit_gross_cost:.3f}")
    with r1c3:
        st.metric("Total Revenue (€)", f"{total_revenue:.2f}")

    g_col, n_col = st.columns(2)
    with g_col:
        st.metric("Gross Profit (€)", f"{gross_profit:.2f}")
        st.metric("Gross Margin (%)", f"{gross_margin_pct:.2f}", delta=f"{gross_margin_pct:.2f}%", delta_color="normal")
    with n_col:
        st.metric("Net Profit (€)", f"{net_profit:.2f}")
        st.metric("Net Margin (%)", f"{net_margin_pct:.2f}", delta=f"{net_margin_pct:.2f}%", delta_color="normal")

    with st.expander("Breakdown"):
        st.write({
            "Customer": customer if customer and customer != "-- Select --" else None,
            "Customer warehouse": customer_wh if customer_wh and customer_wh != "-- Select --" else None,
            "Unit VVP cost (€ / pc)": round(unit_vvp, 2),
            "Unit purchase cost (€ / pc)": round(unit_purchase, 3),
            "Delivery transport (TOTAL €)": round(delivery_transport_total, 2),
            "Delivery transport (€ / pc)": round(unit_delivery, 4),
            "Unit gross cost (€ / pc) [VVP + Purchase]": round(unit_gross_cost, 3),
            "Sales price (€ / pc)": round(sales_price_per_piece, 3),
            "Quantity (pcs)": pieces,
            "Total cost (€) [Unit gross × qty]": round(total_gross_cost, 2),
            "Total revenue (€)": round(total_revenue, 2),
            "Gross profit (€) [Revenue − Total cost]": round(gross_profit, 2),
            "Gross margin (%)": round(gross_margin_pct, 2),
            "Net profit (€) [Revenue − Total cost − DeliveryTOTAL]": round(net_profit, 2),
            "Net margin (%)": round(net_margin_pct, 2),
        })

    src_txt = used_source or "(no source)"
    st.caption(f"Data source: `{src_txt}`")

    # --- return compact summary for exports (generic.py picks this up) ---
    export_payload = {
        "customer": customer if customer and customer != "-- Select --" else None,
        "customer_warehouse": customer_wh if customer_wh and customer_wh != "-- Select --" else None,
        "unit_vvp_cpp": round(unit_vvp, 2),
        "unit_purchase_cpp": round(unit_purchase, 3),
        "unit_delivery_cpp": round(unit_delivery, 4),
        "unit_gross_cpp": round(unit_gross_cost, 3),  # VVP + Purchase
        "sales_price_cpp": round(sales_price_per_piece, 3),
        "pieces": int(pieces),
        "delivery_transport_total": round(delivery_transport_total, 2),
        "total_gross_cost": round(total_gross_cost, 2),
        "total_revenue": round(total_revenue, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_margin_pct": round(gross_margin_pct, 2),
        "net_profit": round(net_profit, 2),
        "net_margin_pct": round(net_margin_pct, 2),
        "total_cost": round(total_cost, 2),
        "data_source": src_txt,
    }
    return export_payload