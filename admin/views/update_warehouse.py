# admin/views/update_warehouse.py
"""
Admin • Update Warehouse

- Transfer modes: "Excel file" (lookup) or "Fixed cost"
- Double Stack only for "Excel file"
- Success banner shows right under the Save button (and persists across rerun once)
"""

import streamlit as st
import sys
import importlib.util
from pathlib import Path

# Manually load config_manager module
_root = Path(__file__).resolve().parents[2]
_cm_path = _root / "services" / "config_manager.py"
_spec = importlib.util.spec_from_file_location("services.config_manager", _cm_path)
_cm = importlib.util.module_from_spec(_spec)
sys.modules["services.config_manager"] = _cm
_spec.loader.exec_module(_cm)

load_catalog = _cm.load_catalog
save_catalog = _cm.save_catalog
list_warehouses = _cm.list_warehouses
get_wh_by_id = _cm.get_wh_by_id

from .helpers import (
    default_rates,
    default_features,
    normalize_rates,
    rates_block,
)


def _is_spedka_id(selected_id: str, wh_name: str | None = None) -> bool:
    sid = (selected_id or "").strip().lower()
    nm = (wh_name or "").strip().lower()
    return sid == "sl_spedka" or "spedka" in nm


def page_update_warehouse():
    st.title("Admin • Update Warehouse")

    # Manual refresh
    ctrl_col, _ = st.columns([1, 3])
    with ctrl_col:
        if st.button("Refresh list"):
            try:
                st.cache_data.clear()
            except Exception:
                pass

    catalog = load_catalog()
    wh_list = list_warehouses(catalog)
    if not wh_list:
        st.info("No warehouses yet. Use 'Add warehouse'.")
        return

    id_list = sorted([w["id"] for w in wh_list if w.get("id")])
    label_map = {
        w["id"]: f"{w.get('name', w['id'])} ({w['id']})"
        for w in wh_list
        if w.get("id")
    }

    # Default selection
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
        "Select warehouse",
        options=id_list,
        index=default_index,
        key="update_wh_select_id",
        format_func=lambda wid: label_map.get(wid, wid),
    )

    # -------- per-warehouse state isolation & cleanup --------
    def skey(name: str) -> str:
        """Stable, per-warehouse widget key."""
        return f"upd__{name}__{selected_id}"

    _prev = st.session_state.get("_last_selected_id")
    if _prev != selected_id:
        # Clear all our page-specific keys so old values don't bleed into the new selection.
        for k in list(st.session_state.keys()):
            if isinstance(k, str) and k.startswith("upd__"):
                del st.session_state[k]
    st.session_state["_last_selected_id"] = selected_id
    # ---------------------------------------------------------

    st.divider()

    # Record & fields
    w_orig = get_wh_by_id(catalog, selected_id) or {
        "id": selected_id,
        "name": selected_id,
        "rates": default_rates(),
        "features": default_features(),
    }

    # NAME
    current_name = str(w_orig.get("name", selected_id)).strip() or selected_id
    new_name = st.text_input(
        "Warehouse Name",
        value=current_name,
        key=skey("wh_name"),
    )

    # RATES
    rates_src = normalize_rates(w_orig.get("rates", {}))
    rates = rates_block(skey("rates"), rates_src)

    # FEATURES
    feats = w_orig.get("features", {}) or {}
    st.subheader("Features")

    # Labelling enabled
    lab_col, _ = st.columns([2, 3])
    with lab_col:
        labeling = st.checkbox(
            "Labelling enabled",
            value=bool(feats.get("labeling", False)),
            key=skey("feat_labeling"),
        )

    # Determine SPEDKA based on id/name (using NEW name field too)
    is_spedka = _is_spedka_id(selected_id, new_name or current_name)

    # SPEDKA: label_options editor (JSON-driven)
    if is_spedka:
        opts = feats.get("label_options", {}) or {}
        if not isinstance(opts, dict):
            opts = {}

        # defaults: from JSON label_options; fallback: from legacy label_costs
        default_simple = float(opts.get("simple", 0.0) or 0.0)
        default_complex = float(opts.get("complex", 0.0) or 0.0)

        if default_simple == 0.0 and default_complex == 0.0:
            legacy = feats.get("label_costs") if isinstance(feats.get("label_costs"), dict) else {}
            legacy_sum = float(legacy.get("label", 0.0) or 0.0) + float(legacy.get("labelling", 0.0) or 0.0)
            # treat legacy as simple
            default_simple = legacy_sum

        # If still empty, use the requested initial values
        if default_simple == 0.0:
            default_simple = 0.03
        if default_complex == 0.0:
            default_complex = 0.042

        c1, c2 = st.columns(2)
        with c1:
            spedka_simple = st.number_input(
                "Simple label (€ / piece)",
                min_value=0.0,
                step=0.001,
                format="%.3f",
                value=float(default_simple) if labeling else 0.0,
                disabled=not labeling,
                key=skey("spedka_simple"),
            )
        with c2:
            spedka_complex = st.number_input(
                "Complex label (€ / piece)",
                min_value=0.0,
                step=0.001,
                format="%.3f",
                value=float(default_complex) if labeling else 0.0,
                disabled=not labeling,
                key=skey("spedka_complex"),
            )

        st.caption("SPEDKA uses two labelling options. Rates are stored in catalog as features.label_options.simple/complex.")

        # Keep legacy fields hidden for SPEDKA (avoid confusion)
        label_per_piece = 0.0
        labelling_per_piece = 0.0

    else:
        # Non-SPEDKA: legacy label_costs editor
        label_costs = feats.get("label_costs") if isinstance(feats.get("label_costs"), dict) else {}
        lc1, lc2 = st.columns(2)
        with lc1:
            label_per_piece = st.number_input(
                "Label (€ / piece)",
                min_value=0.0, step=0.001, format="%.3f",
                value=float(label_costs.get("label", 0.0)) if labeling else 0.0,
                disabled=not labeling,
                key=skey("label_per_piece"),
            )
        with lc2:
            labelling_per_piece = st.number_input(
                "Labelling (€ / piece)",
                min_value=0.0, step=0.001, format="%.3f",
                value=float(label_costs.get("labelling", 0.0)) if labeling else 0.0,
                disabled=not labeling,
                key=skey("labelling_per_piece"),
            )

    st.markdown("---")

    # Transfer
    t1, t2, t3 = st.columns([1.2, 1.2, 1])
    with t1:
        transfer = st.checkbox(
            "Transfer enabled",
            value=bool(feats.get("transfer", False)),
            key=skey("feat_transfer"),
        )

    legacy_mode = str(feats.get("transfer_mode", "")).strip().lower()
    if legacy_mode in ("json_lookup", "lookup", "excel", "excel_lookup"):
        initial_mode = "Excel file"
    elif legacy_mode in ("manual_fixed", "fixed"):
        initial_mode = "Fixed cost"
    else:
        initial_mode = ""

    with t2:
        transfer_mode_label = st.selectbox(
            "Transfer mode",
            options=["", "Excel file", "Fixed cost"],
            index=["", "Excel file", "Fixed cost"].index(initial_mode) if transfer else 0,
            disabled=not transfer,
            help="Excel file: read a pallets→truck_cost table. Fixed cost: single total €.",
            key=skey("transfer_mode"),
        )
    with t3:
        double_stack = st.checkbox(
            "Double Stack (only Excel)",
            value=bool(feats.get("double_stack", False)),
            disabled=not transfer or transfer_mode_label != "Excel file",
            key=skey("double_stack"),
        )

    transfer_excel_val = str(
        feats.get("transfer_excel")
        or feats.get("transfer_json")  # backward compatibility
        or ""
    )
    tfixed = float(feats.get("transfer_fixed", 0.0) or 0.0)

    tj_col, tf_col = st.columns(2)
    with tj_col:
        transfer_excel = st.text_input(
            "Excel file path (for 'Excel file' mode)",
            value=transfer_excel_val,
            disabled=not transfer or transfer_mode_label != "Excel file",
            placeholder="e.g. data/de_transfer_rates.xlsx",
            help="Columns: 'pallets', 'truck_cost' (first sheet).",
            key=skey("transfer_excel"),
        )
    with tf_col:
        transfer_fixed = st.number_input(
            "Fixed transfer amount (TOTAL €)",
            min_value=0.0, step=1.0, value=tfixed,
            disabled=not transfer or transfer_mode_label != "Fixed cost",
            key=skey("transfer_fixed"),
        )

    st.markdown("---")

    # Second-leg
    second_leg = st.checkbox(
        "Second Warehouse Transfer enabled",
        value=bool(feats.get("second_leg", False)),
        key=skey("feat_second_leg"),
    )

    # ---- SUCCESS BANNER PLACEHOLDER (right under the Save button)
    msg_area = st.empty()  # banner burada görünecek

    # Show persisted success message here after rerun
    if "__flash_success" in st.session_state:
        msg_area.success(st.session_state["__flash_success"])
        del st.session_state["__flash_success"]

    # SAVE
    if st.button("Save changes", type="primary", key=skey("save_btn")):
        safe_name = (new_name or "").strip() or selected_id

        features_payload = {
            "labeling": bool(labeling),
            "transfer": bool(transfer),
            "second_leg": bool(second_leg),
        }

        if labeling:
            if is_spedka:
                simple_val = float(st.session_state.get(skey("spedka_simple"), 0.0) or 0.0)
                complex_val = float(st.session_state.get(skey("spedka_complex"), 0.0) or 0.0)

                # Main, data-driven source for user app
                features_payload["label_options"] = {
                    "simple": float(simple_val),
                    "complex": float(complex_val),
                }

                # Backward compatibility (optional): keep label_costs present
                # We'll store "simple" as legacy total-per-piece in label_costs.label
                features_payload["label_costs"] = {
                    "label": float(simple_val),
                    "labelling": 0.0,
                }
            else:
                features_payload["label_costs"] = {
                    "label": float(label_per_piece or 0.0),
                    "labelling": float(labelling_per_piece or 0.0),
                }

        if transfer:
            if transfer_mode_label == "Excel file":
                features_payload["transfer_mode"] = "excel"
                features_payload["transfer_excel"] = str(transfer_excel or "").strip()
                features_payload["double_stack"] = bool(double_stack)
            elif transfer_mode_label == "Fixed cost":
                features_payload["transfer_mode"] = "fixed"
                features_payload["transfer_fixed"] = float(transfer_fixed or 0.0)

        payload = {
            "id": selected_id,
            "name": safe_name,
            "rates": {
                "inbound": float(rates.get("inbound", 0.0)),
                "outbound": float(rates.get("outbound", 0.0)),
                "storage": float(rates.get("storage", 0.0)),
                "order_fee": float(rates.get("order_fee", 0.0)),
            },
            "features": features_payload,
        }

        catalog.setdefault("warehouses", [])
        replaced = False
        for i, wh in enumerate(catalog["warehouses"]):
            if (wh.get("id") or "").strip() == selected_id:
                catalog["warehouses"][i] = payload
                replaced = True
                break
        if not replaced:
            catalog["warehouses"].append(payload)

        try:
            save_catalog(catalog)
        except Exception as e:
            msg_area.error(f"Save failed: {e}")
        else:
            msg_area.success(f"Warehouse '{selected_id}' saved.")
            st.toast("Changes saved.", icon="✅")
            st.session_state["_next_select_id"] = selected_id
            st.session_state["__flash_success"] = f"Warehouse '{selected_id}' saved."
            try:
                st.cache_data.clear()
            except Exception:
                pass
            try:
                st.rerun()
            except AttributeError:
                st.experimental_rerun()

    # DELETE (inline confirm)
    if st.button("Delete warehouse", type="secondary", key=skey("delete_btn")):
        st.session_state["__del_confirm__"] = True

    if st.session_state.get("__del_confirm__"):
        st.warning(f"Are you sure you want to permanently delete '{selected_id}'?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Confirm delete", use_container_width=True, key=skey("confirm_delete_btn")):
                catalog["warehouses"] = [
                    wh for wh in catalog.get("warehouses", [])
                    if (wh.get("id") or "").strip() != selected_id
                ]
                try:
                    save_catalog(catalog)
                except Exception as e:
                    msg_area.error(f"Delete failed: {e}")
                else:
                    msg_area.success(f"Warehouse '{selected_id}' deleted.")
                    st.toast("Deleted.", icon="🗑️")
                    try:
                        st.cache_data.clear()
                    except Exception:
                        pass
                    remaining_ids = sorted(
                        [w.get("id") for w in catalog.get("warehouses", []) if w.get("id")]
                    )
                    if remaining_ids:
                        st.session_state["_next_select_id"] = remaining_ids[0]
                    else:
                        st.session_state.pop("_next_select_id", None)
                        st.session_state.pop("update_wh_select_id", None)
                    if st.session_state.get("last_added_id") == selected_id:
                        st.session_state.pop("last_added_id", None)
                    st.session_state["__flash_success"] = f"Warehouse '{selected_id}' deleted."
                finally:
                    st.session_state["__del_confirm__"] = False
                try:
                    st.rerun()
                except AttributeError:
                    st.experimental_rerun()
        with c2:
            if st.button("Cancel", use_container_width=True, key=skey("cancel_delete_btn")):
                st.session_state["__del_confirm__"] = False

    # ====== DEBUG: CATALOG PATH ======
    st.markdown("---")
    st.subheader("🔍 DEBUG INFO")
    from services.config_manager import get_catalog_path
    catalog_path = get_catalog_path()
    st.code(f"Catalog file location:\n{catalog_path}")

    if catalog_path.exists():
        st.success("✅ File exists!")
        import json
        with open(catalog_path, "r") as f:
            data = json.load(f)
        st.json(data)
    else:
        st.error("❌ File does NOT exist!")


def view():
    page_update_warehouse()
