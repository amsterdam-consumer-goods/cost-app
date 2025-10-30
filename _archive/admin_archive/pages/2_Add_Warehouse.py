import json as _json
from pathlib import Path
import streamlit as st

from services.config_manager import (
    load_catalog, save_catalog,
    validate_new_warehouse, add_warehouse,
)

st.title("Add Warehouse")
KEY = "newwh_"

catalog = load_catalog()

c1, c2 = st.columns(2)
with c1:
    wid = st.text_input("ID (e.g. nl_svz)", key=f"{KEY}id").strip()
    wname = st.text_input("Name (e.g. SVZ NL)", key=f"{KEY}name").strip()
    wcountry = st.text_input("Country", value="Netherlands", key=f"{KEY}country")
    wactive = st.checkbox("Active", value=True, key=f"{KEY}active")
with c2:
    inbound = st.number_input("Inbound €/pallet", 0.0, step=0.1, key=f"{KEY}in")
    outbound = st.number_input("Outbound €/pallet", 0.0, step=0.1, key=f"{KEY}out")
    storage = st.number_input("Storage €/pallet/week", 0.0, step=0.01, key=f"{KEY}st")
    order_fee = st.number_input("Extra order cost €", 0.0, step=0.1, key=f"{KEY}ord")

st.markdown("### Features")
labeling = st.checkbox("Labeling service available", value=False, key=f"{KEY}labeling")
if labeling:
    lc1, lc2 = st.columns(2)
    with lc1:
        label_cost = st.number_input("Label cost (€/piece)", 0.0, step=0.001, format="%.3f", key=f"{KEY}label_cost")
    with lc2:
        labelling_cost = st.number_input("Labelling cost (€/piece)", 0.0, step=0.001, format="%.3f", key=f"{KEY}labelling_cost")

transfer = st.checkbox("Labelling transfer required (external site)", value=False, key=f"{KEY}transfer")
transfer_json = ""
double_stack = False
if transfer:
    st.caption("Provide a pallet→truck_cost table (JSON path or upload).")
    double_stack = st.checkbox("Double stack option available", value=False, key=f"{KEY}dstack")
    st.selectbox("Transfer type", ["truck_lookup"], index=0, key=f"{KEY}ttype")

    # Option A
    transfer_json = st.text_input("Path to JSON (e.g. data/transfer_rates_<id>.json)", value="", key=f"{KEY}tjson")

    # Option B (upload → standardized name)
    st.warning("Excel/JSON must contain exactly two columns: 'pallets' and 'truck_cost'.")
    up = st.file_uploader("Upload JSON or Excel with [pallets, truck_cost]", type=["json", "xlsx", "xls"], key=f"{KEY}upload")
    if up is not None:
        try:
            import pandas as pd  # type: ignore
            APP_ROOT = Path(__file__).resolve().parents[1]
            DATA_DIR = APP_ROOT / "data"
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            target_rel = Path(f"data/transfer_rates_{(wid or 'new').strip()}.json")
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
        except Exception as e:
            st.error(f"Failed to save uploaded file: {e}")

second_leg_enabled = st.checkbox("Add second leg?", value=True, key=f"{KEY}secondleg")

if st.button("Create warehouse", type="primary", key=f"{KEY}create"):
    new_wh = {
        "id": wid,
        "name": wname,
        "country": wcountry,
        "active": bool(wactive),
        "rates": {
            "inbound": float(inbound),
            "outbound": float(outbound),
            "storage": float(storage),
            "order_fee": float(order_fee),
        },
        "features": {
            "labeling": bool(labeling),
            "transfer": bool(transfer),
            "second_leg": "optional" if second_leg_enabled else "none",
        },
    }
    if labeling:
        new_wh["features"]["label_costs"] = {
            "label": float(st.session_state.get(f"{KEY}label_cost", 0.0)),
            "labelling": float(st.session_state.get(f"{KEY}labelling_cost", 0.0)),
        }
    if transfer:
        new_wh["features"]["transfer_type"] = "truck_lookup"
        if transfer_json:
            new_wh["features"]["transfer_json"] = transfer_json
        new_wh["features"]["double_stack"] = bool(double_stack)

    errs = validate_new_warehouse(catalog, new_wh)
    if errs:
        st.error(" • " + "\n • ".join(errs))
    else:
        add_warehouse(catalog, new_wh)
        save_catalog(catalog)
        st.success(f"Warehouse '{wname}' created. It will now appear in dropdowns.")
