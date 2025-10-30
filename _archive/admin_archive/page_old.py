import json
from pathlib import Path
import streamlit as st

from services.config_manager import (
    load_catalog, save_catalog,
    list_warehouses, get_wh_by_id,
    validate_rates, validate_new_warehouse, add_warehouse, set_wh_rates,
)

# ────────────────────────────────────────────────────────────────────────────────
# Page config
# ────────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Admin – Warehouses", page_icon="🛠️", layout="centered")
st.title("🛠️ Admin: Warehouse Management")

# ────────────────────────────────────────────────────────────────────────────────
# Load catalog
# ────────────────────────────────────────────────────────────────────────────────
catalog = load_catalog()
warehouses = list_warehouses(catalog)
if not warehouses:
    st.warning("No warehouses found.")
    st.stop()

# ────────────────────────────────────────────────────────────────────────────────
# Action selector (controls which block is shown)
# ────────────────────────────────────────────────────────────────────────────────
action = st.radio("Choose action", ["Update existing", "Add new"], horizontal=True, key="action_radio")

# ======================================================================
#                          UPDATE EXISTING
# ======================================================================
if action == "Update existing":
    # Select existing warehouse
    options = {w["name"]: w["id"] for w in warehouses}
    name = st.selectbox("Warehouse", list(options.keys()), key="existing_wh_select")
    wid = options[name]
    wh = get_wh_by_id(catalog, wid)
    rates = wh["rates"]

    # Ensure features dict exists
    feats = wh.get("features", {})
    if not isinstance(feats, dict):
        feats = {}

    st.subheader(f"Edit: {wh['name']} ({wh['id']})")

    # ── Rates
    with st.expander("Rates", expanded=True):
        r = rates
        c1, c2 = st.columns(2)
        with c1:
            inbound = st.number_input("Inbound €/pallet",
                                      min_value=0.0, value=float(r["inbound"]), step=0.1,
                                      key=f"inbound_{wid}")
            storage = st.number_input("Storage €/pallet/week",
                                      min_value=0.0, value=float(r["storage"]), step=0.01,
                                      key=f"storage_{wid}")
        with c2:
            outbound = st.number_input("Outbound €/pallet",
                                       min_value=0.0, value=float(r["outbound"]), step=0.1,
                                       key=f"outbound_{wid}")
            order_fee = st.number_input("Extra Order Cost €",
                                        min_value=0.0, value=float(r.get("order_fee", 0.0)), step=0.1,
                                        key=f"orderfee_{wid}")

    # ── Features
    with st.expander("Features", expanded=False):
        # Labeling
        labeling = st.checkbox("Labeling service available",
                               value=bool(feats.get("labeling", False)),
                               key=f"labeling_{wid}")
        label_costs = feats.get("label_costs", {"label": 0.0, "labelling": 0.0})
        if labeling:
            lc1, lc2 = st.columns(2)
            with lc1:
                label_cost = st.number_input("Label Cost (€/piece)",
                                             min_value=0.0, value=float(label_costs.get("label", 0.0)),
                                             step=0.001, format="%.3f",
                                             key=f"label_cost_{wid}")
            with lc2:
                labelling_cost = st.number_input("Labelling Cost (€/piece)",
                                                 min_value=0.0, value=float(label_costs.get("labelling", 0.0)),
                                                 step=0.001, format="%.3f",
                                                 key=f"labelling_cost_{wid}")

        # Transfer (lookup or manual)
        transfer = st.checkbox("Labelling transfer required (external site)",
                               value=bool(feats.get("transfer", False)),
                               key=f"transfer_{wid}")

        transfer_mode = feats.get("transfer_mode", "lookup")  # "lookup" or "manual"
        transfer_type = feats.get("transfer_type") or "truck_lookup"
        # default path standardization
        default_transfer_path = feats.get("transfer_json", f"data/transfer_rates_{wid}.json")
        transfer_json = default_transfer_path
        double_stack = bool(feats.get("double_stack", False))
        transfer_fixed = float(feats.get("transfer_fixed_per_leg", 0.0))

        if transfer:
            transfer_mode = st.radio("How to provide transfer cost?",
                                     ["lookup", "manual"],
                                     horizontal=True,
                                     index=0 if transfer_mode == "lookup" else 1,
                                     key=f"transfer_mode_{wid}")

            if transfer_mode == "lookup":
                st.caption("Use a pallet→truck_cost table.")
                transfer_type = st.selectbox("Transfer type",
                                             ["truck_lookup"], index=0,
                                             key=f"transfer_type_{wid}")
                double_stack = st.checkbox("Double stack option available",
                                           value=double_stack,
                                           key=f"double_stack_{wid}")

                # Option A: Path input (pre-filled with standardized default)
                transfer_json = st.text_input(
                    "Path to JSON (pallets→truck_cost)",
                    value=default_transfer_path,
                    placeholder=f"data/transfer_rates_{wid}.json",
                    key=f"transfer_json_{wid}"
                )

                # Option B: Upload (writes to standardized file name)
                st.warning("Excel/JSON must contain exactly two columns: 'pallets' and 'truck_cost'.")
                st.markdown("**Or upload file (Option B):**")
                up = st.file_uploader(
                    "Upload JSON or Excel with columns [pallets, truck_cost]",
                    type=["json", "xlsx", "xls"],
                    key=f"transfer_upload_update_{wid}"
                )

                if up is not None:
                    try:
                        import json as _json
                        import pandas as pd  # type: ignore

                        APP_ROOT = Path(__file__).resolve().parents[1]
                        DATA_DIR = APP_ROOT / "data"
                        DATA_DIR.mkdir(parents=True, exist_ok=True)
                        target_rel = Path(f"data/transfer_rates_{wid}.json")
                        target_abs = APP_ROOT / target_rel

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

                        transfer_json = str(target_rel).replace("\\", "/")
                        st.success(f"Lookup table saved to: {transfer_json}")

                    except Exception as ex:
                        st.error(f"Failed to save uploaded file: {ex}")

            else:
                st.caption("Enter a fixed per-leg transfer cost (e.g., one truck run).")
                transfer_fixed = st.number_input("Transfer fixed cost per leg (€)",
                                                 min_value=0.0,
                                                 value=float(transfer_fixed),
                                                 step=1.0,
                                                 key=f"transfer_fixed_{wid}")

        # Second leg
        second_leg_enabled = st.checkbox(
            "Add second leg?",
            value=(feats.get("second_leg", "optional") != "none"),
            key=f"second_leg_enabled_{wid}"
        )


    # ── Save changes
    if st.button("Save changes", type="primary", key=f"save_changes_{wid}"):
        new_rates = {
            "inbound": float(inbound),
            "outbound": float(outbound),
            "storage": float(storage),
            "order_fee": float(order_fee),
        }
        errs = validate_rates(new_rates)
        if errs:
            st.error(" • " + "\n • ".join(errs))
        else:
            set_wh_rates(catalog, wh["id"], new_rates)

            new_feats = {
                "labeling": bool(labeling),
                "transfer": bool(transfer),
                "second_leg": "optional" if second_leg_enabled else "none",
            }
            if labeling:
                new_feats["label_costs"] = {
                    "label": float(st.session_state.get(f"label_cost_{wid}", 0.0)),
                    "labelling": float(st.session_state.get(f"labelling_cost_{wid}", 0.0)),
                }

            if transfer:
                new_feats["transfer_mode"] = transfer_mode
                if transfer_mode == "lookup":
                    new_feats["transfer_type"] = transfer_type
                    if transfer_json:
                        new_feats["transfer_json"] = transfer_json
                    new_feats["double_stack"] = bool(double_stack)
                else:
                    new_feats["transfer_fixed_per_leg"] = float(transfer_fixed)

            wh["features"] = new_feats
            save_catalog(catalog)
            st.success("Saved! catalog.json updated.")

# ======================================================================
#                           ADD NEW
# ======================================================================
elif action == "Add new":
    st.subheader("Add a new warehouse")

    c1, c2 = st.columns(2)
    with c1:
        wid_new = st.text_input("ID (e.g. nl_svz)", key="new_id").strip()
        wname = st.text_input("Name (e.g. SVZ NL)", key="new_name").strip()
        wcountry = st.text_input("Country", value="Netherlands", key="new_country")
        wactive = st.checkbox("Active", value=True, key="new_active")
    with c2:
        inbound_n = st.number_input("Inbound €/pallet", min_value=0.0, value=0.0, step=0.1, key="new_in")
        outbound_n = st.number_input("Outbound €/pallet", min_value=0.0, value=0.0, step=0.1, key="new_out")
        storage_n = st.number_input("Storage €/pallet/week", min_value=0.0, value=0.0, step=0.01, key="new_sto")
        order_fee_n = st.number_input("Extra order cost €", min_value=0.0, value=0.0, step=0.1, key="new_ordfee")

    st.markdown("### Features")
    labeling_n = st.checkbox("Labeling service available", value=False, key="new_labeling")
    if labeling_n:
        lc1, lc2 = st.columns(2)
        with lc1:
            label_cost_n = st.number_input("Label cost (€/piece)", min_value=0.0, value=0.0,
                                           step=0.001, format="%.3f", key="new_label_cost")
        with lc2:
            labelling_cost_n = st.number_input("Labelling cost (€/piece)", min_value=0.0, value=0.0,
                                               step=0.001, format="%.3f", key="new_labelling_cost")

    transfer_n = st.checkbox("Labelling transfer required (external site)", value=False, key="new_transfer")
    transfer_json_n = ""
    double_stack_n = False
    transfer_mode_n = "lookup"  # keep simple for Add New; can extend if needed
    if transfer_n:
        st.caption("Provide a pallet→truck_cost table (JSON path or upload).")
        double_stack_n = st.checkbox("Double stack option available", value=False, key="new_double_stack")
        st.selectbox("Transfer type", ["truck_lookup"], index=0, key="new_transfer_type")

        # Option A
        transfer_json_n = st.text_input("Path to JSON (e.g. data/xyz.json)", value="", key="new_transfer_json_path")

        # Option B (upload → standardized name)
        st.warning("Excel/JSON must contain exactly two columns: 'pallets' and 'truck_cost'.")
        up_new = st.file_uploader("Upload JSON or Excel with [pallets, truck_cost]",
                                  type=["json", "xlsx", "xls"], key="new_transfer_upload")
        if up_new is not None:
            try:
                import json as _json
                import pandas as pd  # type: ignore

                DATA_DIR = Path(__file__).resolve().parents[1] / "data"
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                target_rel_new = Path(f"data/transfer_rates_{(wid_new or 'new').strip()}.json")
                target_abs_new = Path(__file__).resolve().parents[1] / target_rel_new

                if up_new.name.lower().endswith(".json"):
                    content = _json.loads(up_new.getvalue().decode("utf-8"))
                    with open(target_abs_new, "w", encoding="utf-8") as f:
                        _json.dump(content, f, ensure_ascii=False, indent=2)
                else:
                    df = pd.read_excel(up_new)
                    cols_lower = {c: c.lower() for c in df.columns}
                    df = df.rename(columns=cols_lower)
                    if not {"pallets", "truck_cost"}.issubset(df.columns):
                        st.error("Excel must have columns: pallets, truck_cost")
                        st.stop()
                    data = [
                        {"pallets": int(r.pallets), "truck_cost": float(r.truck_cost)}
                        for r in df[["pallets", "truck_cost"]].itertuples(index=False)
                    ]
                    with open(target_abs_new, "w", encoding="utf-8") as f:
                        _json.dump(data, f, ensure_ascii=False, indent=2)

                transfer_json_n = str(target_rel_new).replace("\\", "/")
                st.success(f"Saved lookup to {transfer_json_n}")
            except Exception as e:
                st.error(f"Failed to save uploaded file: {e}")

    second_leg_enabled_n = st.checkbox("Add second leg?", value=True, key="new_second_leg_enabled")

    if st.button("Create warehouse", type="primary", key="create_wh"):
        new_wh = {
            "id": wid_new,
            "name": wname,
            "country": wcountry,
            "active": bool(wactive),
            "rates": {
                "inbound": float(inbound_n),
                "outbound": float(outbound_n),
                "storage": float(storage_n),
                "order_fee": float(order_fee_n),
            },
            "features": {
                "labeling": bool(labeling_n),
                "transfer": bool(transfer_n),
                "second_leg": "optional" if second_leg_enabled_n else "none"
            }
        }
        if labeling_n:
            new_wh["features"]["label_costs"] = {
                "label": float(st.session_state.get("new_label_cost", 0.0)),
                "labelling": float(st.session_state.get("new_labelling_cost", 0.0)),
            }
        if transfer_n:
            new_wh["features"]["transfer_type"] = "truck_lookup"
            if transfer_json_n:
                new_wh["features"]["transfer_json"] = transfer_json_n
            new_wh["features"]["double_stack"] = bool(double_stack_n)

        errs = validate_new_warehouse(catalog, new_wh)
        if errs:
            st.error(" • " + "\n • ".join(errs))
        else:
            add_warehouse(catalog, new_wh)
            save_catalog(catalog)
            st.success(f"Warehouse '{wname}' created. It will now appear in dropdowns.")
