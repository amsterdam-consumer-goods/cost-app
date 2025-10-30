# admin/pages.py — admin pages

from typing import Dict, Any, List
from pathlib import Path
import json as _json
import streamlit as st

from services.config_manager import (
    load_catalog, save_catalog,
    list_warehouses, get_wh_by_id, add_warehouse,
    validate_new_warehouse,
    add_customer as cm_add_customer,
)

# ---------------- Small helpers ----------------

def _warehouse_ids(catalog):
    return [w.get("id") for w in list_warehouses(catalog) if w.get("id")]

def _default_rates():
    return {"inbound": 0.0, "outbound": 0.0, "storage": 0.0, "order_fee": 0.0}

def _default_features():
    return {
        "labeling": {
            "enabled": False,
            "label_per_piece": 0.0,
            "labelling_per_piece": 0.0,
            "cost_per_unit": 0.0,  # legacy compatibility
        },
        "transfer": {
            "mode": "none",          # none | manual | json_lookup
            "manual_cost": 0.0,
            "lookup_file": "data/svz_truck_rates.json",
        },
        "double_stack": False,
        "second_leg": {"enabled": False, "target": None},
    }

def _normalize_features(raw):
    base = _default_features()
    if not isinstance(raw, dict):
        return base

    out = {
        "labeling": dict(base["labeling"]),
        "transfer": dict(base["transfer"]),
        "double_stack": bool(raw.get("double_stack", False)),
        "second_leg": {"enabled": False, "target": None},
    }

    lab = raw.get("labeling", {})
    if isinstance(lab, bool):
        out["labeling"]["enabled"] = lab
    elif isinstance(lab, dict):
        out["labeling"]["enabled"] = bool(lab.get("enabled", False))
        out["labeling"]["label_per_piece"] = float(lab.get("label_per_piece", 0.0) or 0.0)
        out["labeling"]["labelling_per_piece"] = float(lab.get("labelling_per_piece", 0.0) or 0.0)
        cpu = lab.get("cost_per_unit")
        if cpu is not None and out["labeling"]["labelling_per_piece"] == 0.0 and out["labeling"]["label_per_piece"] == 0.0:
            try:
                out["labeling"]["labelling_per_piece"] = float(cpu) or 0.0
            except Exception:
                pass
        out["labeling"]["cost_per_unit"] = float(lab.get("cost_per_unit", 0.0) or 0.0)

    tr = raw.get("transfer", {})
    if isinstance(tr, dict):
        mode = tr.get("mode", "none")
        if mode not in ("none", "manual", "json_lookup"):
            mode = "none"
        out["transfer"]["mode"] = mode
        out["transfer"]["manual_cost"] = float(tr.get("manual_cost", 0.0) or 0.0)
        lf = tr.get("lookup_file", base["transfer"]["lookup_file"])
        if isinstance(lf, str) and lf.strip():
            out["transfer"]["lookup_file"] = lf.strip()

    s2 = raw.get("second_leg", {})
    if isinstance(s2, dict):
        out["second_leg"]["enabled"] = bool(s2.get("enabled", False))
        out["second_leg"]["target"] = s2.get("target")

    return out

def _normalize_rates(raw):
    base = _default_rates()
    if not isinstance(raw, dict):
        return base
    return {
        "inbound":  float(raw.get("inbound",  base["inbound"])  or 0.0),
        "outbound": float(raw.get("outbound", base["outbound"]) or 0.0),
        "storage":  float(raw.get("storage",  base["storage"])  or 0.0),
        "order_fee": float(raw.get("order_fee", base["order_fee"]) or 0.0),
    }

# ---------------- UI blocks ----------------

def _rates_block(prefix: str, rates: Dict[str, float]) -> Dict[str, float]:
    st.subheader("Rates (€)")
    c1, c2 = st.columns(2)
    with c1:
        inbound = st.number_input("Inbound €/pallet", value=float(rates.get("inbound", 0.0)),
                                  key=f"{prefix}_in", min_value=0.0, step=0.1)
        storage = st.number_input("Storage €/pallet/week", value=float(rates.get("storage", 0.0)),
                                  key=f"{prefix}_st", min_value=0.0, step=0.1)
    with c2:
        outbound = st.number_input("Outbound €/pallet", value=float(rates.get("outbound", 0.0)),
                                   key=f"{prefix}_out", min_value=0.0, step=0.1)
        order_fee = st.number_input("Extra cost €", value=float(rates.get("order_fee", 0.0)),
                                    key=f"{prefix}_ord", min_value=0.0, step=0.1)
    return {"inbound": inbound, "outbound": outbound, "storage": storage, "order_fee": order_fee}

def _features_block(
    prefix: str,
    features: Dict[str, Any],
    warehouse_ids: List[str],
    wid: str | None = None,
) -> Dict[str, Any]:
    from pathlib import Path
    try:
        import pandas as pd  # optional for Excel uploads
        _has_pandas = True
    except Exception:
        _has_pandas = False

    feats = _normalize_features(features)

    with st.expander("Features", expanded=False):
        # Labeling
        labeling_enabled = st.checkbox(
            "Labeling service available",
            value=bool(feats.get("labeling", {}).get("enabled", False)),
            key=f"{prefix}_labeling_en",
        )
        label_per_piece = float(feats["labeling"].get("label_per_piece", 0.0) or 0.0)
        labelling_per_piece = float(feats["labeling"].get("labelling_per_piece", 0.0) or 0.0)
        if labeling_enabled:
            c1, c2 = st.columns(2)
            with c1:
                label_per_piece = st.number_input(
                    "Label Cost (€/piece)",
                    min_value=0.0, value=label_per_piece, step=0.001, format="%.3f",
                    key=f"{prefix}_label_cost",
                )
            with c2:
                labelling_per_piece = st.number_input(
                    "Labelling Cost (€/piece)",
                    min_value=0.0, value=labelling_per_piece, step=0.001, format="%.3f",
                    key=f"{prefix}_labelling_cost",
                )

        # Transfer (Option A/B aligned)
        transfer_required = st.checkbox(
            "Labelling transfer required (external site)",
            value=(feats.get("transfer", {}).get("mode", "none") != "none"),
            key=f"{prefix}_transfer_req",
        )

        transfer_mode_out = "none"
        transfer_lookup_file = feats.get("transfer", {}).get("lookup_file") or (
            f"data/transfer_rates_{wid}.json" if wid else "data/transfer_rates.json"
        )
        transfer_manual_cost = float(feats.get("transfer", {}).get("manual_cost", 0.0) or 0.0)
        double_stack = bool(feats.get("double_stack", False))

        if transfer_required:
            mode_choice = st.radio(
                "How to provide transfer cost?",
                ["lookup (JSON table)", "manual (fixed per leg)"],
                horizontal=True,
                index=0 if feats.get("transfer", {}).get("mode") in ("json_lookup", "lookup") else 1,
                key=f"{prefix}_transfer_mode",
            )

            if mode_choice.startswith("lookup"):
                transfer_mode_out = "json_lookup"

                double_stack = st.checkbox(
                    "Double stack option available",
                    value=double_stack,
                    key=f"{prefix}_double_stack",
                )

                st.markdown("**Option A: Upload file (JSON/Excel)**")
                st.caption("File must have columns: pallets, truck_cost.")
                up = st.file_uploader(
                    "Upload JSON or Excel",
                    type=["json", "xlsx", "xls"],
                    key=f"{prefix}_transfer_upload",
                )

                st.markdown("**Option B: Enter a path**")
                transfer_lookup_file = st.text_input(
                    "Path to JSON (pallets → truck_cost)",
                    value=str(transfer_lookup_file),
                    placeholder=f"data/transfer_rates_{wid}.json" if wid else "data/transfer_rates.json",
                    key=f"{prefix}_transfer_json",
                )

                if up is not None:
                    try:
                        APP_ROOT = Path(__file__).resolve().parents[1]
                        DATA_DIR = APP_ROOT / "data"
                        DATA_DIR.mkdir(parents=True, exist_ok=True)
                        target_rel = Path(f"data/transfer_rates_{wid}.json" if wid else "data/transfer_rates.json")
                        target_abs = APP_ROOT / target_rel

                        if up.name.lower().endswith(".json"):
                            content = _json.loads(up.getvalue().decode("utf-8"))
                            with open(target_abs, "w", encoding="utf-8") as f:
                                _json.dump(content, f, ensure_ascii=False, indent=2)
                        else:
                            if not _has_pandas:
                                st.error("Excel upload requires pandas. Upload JSON or install pandas.")
                                st.stop()
                            import pandas as pd  # type: ignore
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

                        transfer_lookup_file = str(target_rel).replace("\\", "/")
                        st.success(f"Lookup table saved to: {transfer_lookup_file}")
                    except Exception as ex:
                        st.error(f"Failed to save uploaded file: {ex}")

            else:
                transfer_mode_out = "manual"
                transfer_manual_cost = st.number_input(
                    "Transfer fixed cost per leg (€)",
                    min_value=0.0, value=float(transfer_manual_cost), step=1.0,
                    key=f"{prefix}_transfer_fixed",
                )

        # Second leg: admin only toggles availability; target chosen in user app
        second_leg_enabled = st.checkbox(
            "Add second leg?",
            value=bool(feats.get("second_leg", {}).get("enabled", False)),
            key=f"{prefix}_secondleg",
        )

    return {
        "labeling": {
            "enabled": bool(labeling_enabled),
            "label_per_piece": float(label_per_piece or 0.0),
            "labelling_per_piece": float(labelling_per_piece or 0.0),
            "cost_per_unit": float(feats.get("labeling", {}).get("cost_per_unit", 0.0) or 0.0),
        },
        "transfer": {
            "mode": transfer_mode_out,
            "manual_cost": float(transfer_manual_cost or 0.0),
            "lookup_file": transfer_lookup_file,
        },
        "double_stack": bool(double_stack),
        "second_leg": {"enabled": bool(second_leg_enabled)},
    }

# ---------------- Pages ----------------

def page_update_warehouse():
    st.title("Admin • Update Warehouse")
    catalog = load_catalog()

    wh_list = list_warehouses(catalog)
    if not wh_list:
        st.info("No warehouses yet. Use 'Add warehouse'.")
        return

    # dropdown shows "Name (id)"
    options = {f"{w.get('name', w.get('id',''))} ({w.get('id','')})": w.get("id") for w in wh_list if w.get("id")}
    display = st.selectbox("Select warehouse", list(options.keys()))
    wid = options[display]

    # current warehouse object (keep existing name; no name input)
    w = get_wh_by_id(catalog, wid) or {"id": wid, "name": wid, "rates": _default_rates(), "features": _default_features()}

    # editors
    rates_src = _normalize_rates(w.get("rates", {}))
    rates = _rates_block("upd", rates_src)

    features_src = _normalize_features(w.get("features", {}))
    features = _features_block("upd", features_src, [x["id"] for x in wh_list if x.get("id")], wid=wid)

    # save
    if st.button("Save changes", type="primary"):
        payload = {
            "id": wid,
            "name": w.get("name", wid),  # keep existing display name
            "rates": {
                "inbound": float(rates.get("inbound", 0.0)),
                "outbound": float(rates.get("outbound", 0.0)),
                "storage": float(rates.get("storage", 0.0)),
                "order_fee": float(rates.get("order_fee", 0.0)),
            },
            "features": features,
        }

        ws = list_warehouses(catalog)
        catalog.setdefault("warehouses", [])
        replaced = False
        for i, wh in enumerate(ws):
            if wh.get("id") == wid:
                catalog["warehouses"][i] = payload
                replaced = True
                break
        if not replaced:
            catalog["warehouses"].append(payload)

        save_catalog(catalog)
        st.success(f"Warehouse '{wid}' saved.")
        st.rerun()

def page_add_warehouse():
    st.title("Admin • Add Warehouse")
    catalog = load_catalog()

    wids = _warehouse_ids(catalog)

    wid = st.text_input("Warehouse ID (unique, e.g., 'nl_svz')")
    name = st.text_input("Display name")

    base_rates = _default_rates()
    base_features = _default_features()

    rates = _rates_block("new", base_rates)
    features = _features_block("new", base_features, wids + ([wid] if wid else []), wid=wid)

    if st.button("Create", type="primary"):
        if not wid:
            st.error("Warehouse ID required.")
            return
        if wid in wids:
            st.error("Warehouse ID must be unique.")
            return

        wh = {
            "id": wid,
            "name": name or wid,
            "rates": {
                "inbound": float(rates.get("inbound", 0.0)),
                "outbound": float(rates.get("outbound", 0.0)),
                "storage": float(rates.get("storage", 0.0)),
                "order_fee": float(rates.get("order_fee", 0.0)),
            },
            "features": features,
        }

        errs = validate_new_warehouse(catalog, wh)
        if errs:
            for e in errs:
                st.error(e)
            return

        add_warehouse(catalog, wh)
        save_catalog(catalog)
        st.success(f"Warehouse '{wid}' created.")
        st.rerun()

def page_add_customer():
    st.title("Admin • Add Customer")
    catalog = load_catalog()

    name = st.text_input("Customer name")

    if "addr_count" not in st.session_state:
        st.session_state.addr_count = 1

    if st.button("Add another address"):
        st.session_state.addr_count += 1

    addresses: List[str] = []
    for i in range(st.session_state.addr_count):
        addr = st.text_input(f"Address #{i+1} (single line)", key=f"addr_{i}", placeholder="e.g., Main St 10, 1011AB Amsterdam, NL")
        addresses.append(addr.strip())

    if st.button("Create customer", type="primary"):
        if not (name and name.strip()):
            st.error("Name required.")
            return
        addresses_clean = [a for a in addresses if a]
        if not addresses_clean:
            st.error("Please enter at least one address line.")
            return

        cid, _cust = cm_add_customer(catalog, name.strip(), addresses_clean)
        save_catalog(catalog)
        st.success(f"Customer created with ID: {cid}")
        st.rerun()

# ---------------- Router ----------------

_PAGES = {
    "Update warehouse": page_update_warehouse,
    "Add warehouse": page_add_warehouse,
    "Add customer": page_add_customer,
}

def admin_router(choice: str):
    _PAGES.get(choice, page_update_warehouse)()
