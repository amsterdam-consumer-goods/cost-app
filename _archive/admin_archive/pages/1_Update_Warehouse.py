# admin/pages/1_Update_Warehouse.py
import json as _json
from pathlib import Path
import streamlit as st

from services.config_manager import (
    load_catalog, save_catalog,
    list_warehouses, get_wh_by_id,
    validate_rates,
)

st.title("Update Warehouse")

# Load catalog
catalog = load_catalog()
warehouses = list_warehouses(catalog)
if not warehouses:
    st.warning("No warehouses found in catalog.json.")
    st.stop()

KEY = "upd_"  # page prefix

# Select warehouse
options = {w["name"]: w["id"] for w in warehouses}
selected_name = st.selectbox("Warehouse", list(options.keys()), key=f"{KEY}pick_wh")
wid = options[selected_name]
wh = get_wh_by_id(catalog, wid)
rates = wh["rates"]
feats = wh.get("features", {}) if isinstance(wh.get("features", {}), dict) else {}

st.caption(f"Editing warehouse id: **{wid}**  •  name: **{selected_name}**")

# ---------- Helpers for state ----------
def _state_key(suffix: str) -> str:
    return f"{KEY}{suffix}_{wid}"

def _wipe_keys_for_current_wid():
    # remove existing keys for current warehouse
    for suf in [
        "in","out","st","ord",
        "labeling","label_cost","labelling_cost",
        "transfer","mode","ttype","dstack","tjson","tfixed",
        "secondleg"
    ]:
        st.session_state.pop(_state_key(suf), None)

def _init_defaults_for_current_wid():
    # Rates
    st.session_state[_state_key("in")]  = float(rates.get("inbound", 0.0))
    st.session_state[_state_key("out")] = float(rates.get("outbound", 0.0))
    st.session_state[_state_key("st")]  = float(rates.get("storage", 0.0))
    st.session_state[_state_key("ord")] = float(rates.get("order_fee", 0.0))
    # Features
    st.session_state[_state_key("labeling")] = bool(feats.get("labeling", False))
    lc = feats.get("label_costs", {"label": 0.0, "labelling": 0.0})
    st.session_state[_state_key("label_cost")]     = float(lc.get("label", 0.0))
    st.session_state[_state_key("labelling_cost")] = float(lc.get("labelling", 0.0))
    st.session_state[_state_key("transfer")]       = bool(feats.get("transfer", False))
    st.session_state[_state_key("mode")]           = feats.get("transfer_mode", "lookup")
    st.session_state[_state_key("ttype")]          = feats.get("transfer_type", "truck_lookup")
    st.session_state[_state_key("dstack")]         = bool(feats.get("double_stack", False))
    st.session_state[_state_key("tjson")]          = feats.get("transfer_json", f"data/transfer_rates_{wid}.json")
    st.session_state[_state_key("tfixed")]         = float(feats.get("transfer_fixed_per_leg", 0.0))
    st.session_state[_state_key("secondleg")]      = (feats.get("second_leg", "optional") != "none")

# Warehouse switch detector
wid_flag_key = f"{KEY}current_wid"
if wid_flag_key not in st.session_state:
    st.session_state[wid_flag_key] = wid
    _wipe_keys_for_current_wid()
    _init_defaults_for_current_wid()
elif st.session_state[wid_flag_key] != wid:
    st.session_state[wid_flag_key] = wid
    _wipe_keys_for_current_wid()
    _init_defaults_for_current_wid()

# ---------- Paths for write/verify ----------
PAGE_FILE = Path(__file__).resolve()
PROJECT_ROOT = PAGE_FILE.parents[2]           # cost-app/
CATALOG_FILE = PROJECT_ROOT / "data" / "catalog.json"

# ---------- Rates (NO value= !!! rely on key & session_state) ----------
with st.expander("Rates", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        st.number_input("Inbound €/pallet", min_value=0.0, step=0.1, key=_state_key("in"))
        st.number_input("Storage €/pallet/week", min_value=0.0, step=0.01, key=_state_key("st"))
    with c2:
        st.number_input("Outbound €/pallet", min_value=0.0, step=0.1, key=_state_key("out"))
        st.number_input("Extra order cost €", min_value=0.0, step=0.1, key=_state_key("ord"))

# ---------- Features (NO value= !!! rely on key & session_state) ----------
with st.expander("Features", expanded=False):
    st.checkbox("Labeling service available", key=_state_key("labeling"))
    if st.session_state[_state_key("labeling")]:
        c1, c2 = st.columns(2)
        with c1:
            st.number_input("Label cost (€/piece)", min_value=0.0, step=0.001, format="%.3f", key=_state_key("label_cost"))
        with c2:
            st.number_input("Labelling cost (€/piece)", min_value=0.0, step=0.001, format="%.3f", key=_state_key("labelling_cost"))

    st.checkbox("Labelling transfer required (external site)", key=_state_key("transfer"))

    if st.session_state[_state_key("transfer")]:
        st.radio("How to provide transfer cost?", ["lookup", "manual"], horizontal=True, key=_state_key("mode"))

        if st.session_state[_state_key("mode")] == "lookup":
            st.caption("Use a pallet→truck_cost table.")
            st.selectbox("Transfer type", ["truck_lookup"], index=0, key=_state_key("ttype"))
            st.checkbox("Double stack option available", key=_state_key("dstack"))

            st.text_input(
                "Path to JSON (pallets→truck_cost)",
                placeholder=f"data/transfer_rates_{wid}.json",
                key=_state_key("tjson"),
            )

            st.warning("Excel/JSON must contain exactly two columns: 'pallets' and 'truck_cost'.")
            st.markdown("**Or upload file (Option B):**")
            up = st.file_uploader(
                "Upload JSON or Excel with columns [pallets, truck_cost]",
                type=["json", "xlsx", "xls"],
                key=_state_key("upload"),
            )
            if up is not None:
                try:
                    import pandas as pd  # type: ignore
                    DATA_DIR = PROJECT_ROOT / "data"
                    DATA_DIR.mkdir(parents=True, exist_ok=True)
                    target_rel = Path(f"data/transfer_rates_{wid}.json")
                    target_abs = PROJECT_ROOT / target_rel

                    if up.name.lower().endswith(".json"):
                        content = _json.loads(up.getvalue().decode("utf-8"))
                        with open(target_abs, "w", encoding="utf-8") as f:
                            _json.dump(content, f, ensure_ascii=False, indent=2)
                    else:
                        df = pd.read_excel(up)
                        cols_lower = {c: c.lower() for c in df.columns}
                        df = df.rename(columns=cols_lower)
                        if not {"pallets", "truck_cost"}.issubset(df.columns):
                            st.error("Excel must contain columns: pallets, truck_cost")
                            st.stop()
                        data = [
                            {"pallets": int(r.pallets), "truck_cost": float(r.truck_cost)}
                            for r in df[["pallets", "truck_cost"]].itertuples(index=False)
                        ]
                        with open(target_abs, "w", encoding="utf-8") as f:
                            _json.dump(data, f, ensure_ascii=False, indent=2)

                    st.session_state[_state_key("tjson")] = str(target_rel).replace("\\", "/")
                    st.success(f"Lookup table saved to: {st.session_state[_state_key('tjson')]}")
                except Exception as ex:
                    st.error(f"Failed to save uploaded file: {ex}")
        else:
            st.caption("Enter a fixed per-leg transfer cost (e.g., one truck run).")
            st.number_input("Transfer fixed cost per leg (€)", min_value=0.0, step=1.0, key=_state_key("tfixed"))

    st.checkbox("Add second leg?", key=_state_key("secondleg"))

# ---------- SAVE ----------
if st.button("Save changes", type="primary", key=f"{KEY}save_{wid}"):
    import json

    new_rates = {
        "inbound": float(st.session_state[_state_key("in")]),
        "outbound": float(st.session_state[_state_key("out")]),
        "storage": float(st.session_state[_state_key("st")]),
        "order_fee": float(st.session_state[_state_key("ord")]),
    }
    errs = validate_rates(new_rates)
    if errs:
        st.error(" • " + "\n • ".join(errs))
        st.stop()

    new_feats = {
        "labeling": bool(st.session_state[_state_key("labeling")]),
        "transfer": bool(st.session_state[_state_key("transfer")]),
        "second_leg": "optional" if bool(st.session_state[_state_key("secondleg")]) else "none",
    }
    if new_feats["labeling"]:
        new_feats["label_costs"] = {
            "label": float(st.session_state.get(_state_key("label_cost"), 0.0)),
            "labelling": float(st.session_state.get(_state_key("labelling_cost"), 0.0)),
        }
    if new_feats["transfer"]:
        mode = st.session_state.get(_state_key("mode"), "lookup")
        new_feats["transfer_mode"] = mode
        if mode == "lookup":
            new_feats["transfer_type"] = st.session_state.get(_state_key("ttype"), "truck_lookup")
            tj = st.session_state.get(_state_key("tjson"), f"data/transfer_rates_{wid}.json")
            if tj:
                new_feats["transfer_json"] = tj
            new_feats["double_stack"] = bool(st.session_state.get(_state_key("dstack"), False))
        else:
            new_feats["transfer_fixed_per_leg"] = float(st.session_state.get(_state_key("tfixed"), 0.0))

    # mutate in memory & persist
    wh["rates"] = new_rates
    wh["features"] = new_feats

    CATALOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CATALOG_FILE.open("w", encoding="utf-8") as f:
        _json.dump(catalog, f, ensure_ascii=False, indent=2)

    # verify by re-read
    confirm = _json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    saved_wh = next((w for w in confirm.get("warehouses", []) if w.get("id") == wid), None)

    st.success(f"Saved to: {CATALOG_FILE}")
    st.json({
        "warehouse_id": wid,
        "saved_rates": (saved_wh or {}).get("rates"),
        "saved_features": (saved_wh or {}).get("features"),
    })
