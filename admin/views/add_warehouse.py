# admin/views/add_warehouse.py
"""
Admin • Add Warehouse (id/rates/features)

Behavior
--------
- Second-leg: simple enable/disable checkbox
- Inline save message: appears directly under the action buttons
- After save: clear Streamlit cache, set `last_added_id`, reset the form
- No rerun: the message remains visible until the user navigates away or resets
"""

from __future__ import annotations

import json
from typing import Any, Dict

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

list_warehouses = _cm.list_warehouses
load_catalog = _cm.load_catalog
save_catalog = _cm.save_catalog

# ---------------- helpers ----------------
def _ensure_state() -> None:
    """Initialize session-state flags used on this page."""
    st.session_state.setdefault("add_preview_open", False)


def _reset_form() -> None:
    """Remove all controlled form keys from session state."""
    for k in [
        "wh_id",
        "wh_name",
        "rate_inbound",
        "rate_outbound",
        "rate_storage",
        "rate_order_fee",
        # features
        "feat_labeling",
        "feat_transfer",
        "feat_second_leg_enabled",
        # labeling extra fields
        "lab_label",
        "lab_labelling",
        # transfer extra fields
        "transfer_mode_label",
        "transfer_excel",
        "transfer_fixed",
        "transfer_double_stack",
    ]:
        if k in st.session_state:
            del st.session_state[k]


def _collect_form_state() -> Dict[str, Any]:
    """Return the current draft payload from session state."""
    features: Dict[str, Any] = {
        "labeling": bool(st.session_state.get("feat_labeling", False)),
        "transfer": bool(st.session_state.get("feat_transfer", False)),
        "second_leg": bool(st.session_state.get("feat_second_leg_enabled", False)),
    }

    # Labeling details when enabled
    if features["labeling"]:
        try:
            label_val = float(st.session_state.get("lab_label") or 0.0)
        except Exception:
            label_val = 0.0
        try:
            labelling_val = float(st.session_state.get("lab_labelling") or 0.0)
        except Exception:
            labelling_val = 0.0
        features["label_costs"] = {
            "label": label_val,
            "labelling": labelling_val,
        }

    # Transfer details when enabled
    if features["transfer"]:
        mode_label = (st.session_state.get("transfer_mode_label") or "").strip()
        if mode_label == "Excel file":
            features["transfer_mode"] = "excel"
            features["transfer_excel"] = str(st.session_state.get("transfer_excel") or "").strip()
            features["double_stack"] = bool(st.session_state.get("transfer_double_stack", False))
        elif mode_label == "Fixed cost":
            features["transfer_mode"] = "fixed"
            try:
                features["transfer_fixed"] = float(st.session_state.get("transfer_fixed") or 0.0)
            except Exception:
                features["transfer_fixed"] = 0.0
        # other/empty -> nothing extra

    return {
        "id": (st.session_state.get("wh_id") or "").strip(),
        "name": (st.session_state.get("wh_name") or "").strip(),
        "rates": {
            "inbound": float(st.session_state.get("rate_inbound") or 0.0),
            "outbound": float(st.session_state.get("rate_outbound") or 0.0),
            "storage": float(st.session_state.get("rate_storage") or 0.0),
            "order_fee": float(st.session_state.get("rate_order_fee") or 0.0),
        },
        "features": features,
    }


def _render_user_label_preview(draft: Dict[str, Any]) -> None:
    """Render a compact, user-facing label preview for the warehouse."""
    st.write("**User label preview**")
    title = draft.get("name") or draft.get("id") or "Unnamed"
    st.markdown(f"### {title}")

    feats = draft.get("features", {}) or {}
    chips = []
    if feats.get("labeling"):
        chips.append("Labeling")
    if feats.get("transfer"):
        chips.append("Transfer")
    if feats.get("second_leg"):
        chips.append("Second-leg")

    st.markdown(" ".join(f"`{c}`" for c in chips) if chips else "_No active features_")
    r = draft.get("rates", {}) or {}
    st.caption(
        f"Rates → In:{r.get('inbound', 0)}  Out:{r.get('outbound', 0)}  "
        f"Storage/w:{r.get('storage', 0)}  Order fee:{r.get('order_fee', 0)}"
    )
    # Labeling preview
    lc = feats.get("label_costs")
    if isinstance(lc, dict):
        st.caption(f"Labeling per piece → label: {lc.get('label',0)} | labelling: {lc.get('labelling',0)}")


# ---------------- page ----------------
def show() -> None:
    """Render the Add Warehouse page."""
    _ensure_state()
    st.title("Admin • Add Warehouse")

    st.subheader("Basic info")
    st.text_input("Warehouse ID", key="wh_id", placeholder="e.g., nl_svz")
    st.text_input("Name", key="wh_name", placeholder="e.g., SVZ Logistics")

    st.divider()
    st.subheader("Rates")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.number_input("Inbound €/pallet", key="rate_inbound", min_value=0.0, step=0.5, format="%.2f")
    with c2:
        st.number_input("Outbound €/pallet", key="rate_outbound", min_value=0.0, step=0.5, format="%.2f")
    with c3:
        st.number_input("Storage €/pallet/week", key="rate_storage", min_value=0.0, step=0.5, format="%.2f")
    with c4:
        st.number_input("Order fee €", key="rate_order_fee", min_value=0.0, step=0.5, format="%.2f")

    st.divider()
    st.subheader("Features")
    f1, f2, f3 = st.columns(3)
    with f1:
        st.checkbox("Labeling", key="feat_labeling")
    with f2:
        st.checkbox("Transfer", key="feat_transfer")
    with f3:
        st.checkbox("Second Warehouse Transfer", key="feat_second_leg_enabled")

    # ---- Labeling options (only when checked) ----
    if st.session_state.get("feat_labeling", False):
        st.markdown("##### Labeling rates (per piece)")
        l1, l2 = st.columns(2)
        with l1:
            st.number_input(
                "Label (€ / piece)",
                key="lab_label",
                min_value=0.0,
                step=0.001,
                format="%.3f",
            )
        with l2:
            st.number_input(
                "Labelling (€ / piece)",
                key="lab_labelling",
                min_value=0.0,
                step=0.001,
                format="%.3f",
            )
        st.markdown("---")
    else:
        for k in ["lab_label", "lab_labelling"]:
            if k in st.session_state:
                del st.session_state[k]
    # ----------------------------------------------

    # ---- Transfer options (only when checked) ----
    if st.session_state.get("feat_transfer", False):
        st.markdown("##### Transfer options")
        t1, t2, t3 = st.columns([1.2, 1.2, 1])
        with t1:
            st.selectbox(
                "Mode",
                options=["", "Excel file", "Fixed cost"],
                key="transfer_mode_label",
                help="Excel file: pallets→truck_cost tablosu okur. Fixed cost: tek toplam €.",
            )
        # Excel mode fields
        if (st.session_state.get("transfer_mode_label") or "") == "Excel file":
            e1, e2 = st.columns([2, 1])
            with e1:
                st.text_input(
                    "Excel file path",
                    key="transfer_excel",
                    placeholder="e.g. data/de_transfer_rates.xlsx",
                    help="İlk sayfada 'pallets' ve 'truck_cost' kolonları.",
                )
            with e2:
                st.checkbox("Double Stack", key="transfer_double_stack")
        # Fixed mode fields
        elif (st.session_state.get("transfer_mode_label") or "") == "Fixed cost":
            st.number_input(
                "Fixed transfer amount (TOTAL €)",
                key="transfer_fixed",
                min_value=0.0,
                step=1.0,
            )
        st.markdown("---")
    else:
        # transfer kapalıysa ilgili state'i temizleyelim ki payload'a sızmasın
        for k in ["transfer_mode_label", "transfer_excel", "transfer_fixed", "transfer_double_stack"]:
            if k in st.session_state:
                del st.session_state[k]
    # ---------------------------------------------

    st.divider()
    a1, a2, a3 = st.columns(3)
    with a1:
        if st.button("Preview", use_container_width=True):
            st.session_state.add_preview_open = True

    # Inline message area — directly under action buttons
    msg_area = st.empty()

    def _do_save() -> None:
        """Validate, persist in catalog, clear cache, and reset the form."""
        draft = _collect_form_state()

        # Validation
        if not draft.get("id"):
            msg_area.error("Warehouse ID is required.")
            return
        if not draft.get("name"):
            msg_area.error("Name is required.")
            return

        catalog = load_catalog()
        ws = list_warehouses(catalog)
        ids = {w.get("id") for w in ws if w.get("id")}
        if draft["id"] in ids:
            msg_area.error("Warehouse ID must be unique.")
            return

        catalog.setdefault("warehouses", []).append(draft)
        try:
            save_catalog(catalog)
        except Exception as e:  # noqa: BLE001
            msg_area.error(f"Save failed: {e}")
            return

        # Success
        try:
            st.cache_data.clear()
        except Exception:  # noqa: BLE001
            pass

        st.session_state["last_added_id"] = draft["id"]
        msg_area.success(f"Warehouse '{draft['id']}' added.")
        st.toast("Saved successfully.", icon="✅")
        st.balloons()
        _reset_form()

    with a2:
        if st.button("Save", use_container_width=True):
            _do_save()

    with a3:
        if st.button("Reset form", use_container_width=True):
            _reset_form()
            msg_area.info("Form cleared.")

    # Preview panel
    if st.session_state.add_preview_open:
        st.divider()
        st.subheader("Preview")
        draft = _collect_form_state()
        st.write("**Draft payload**")
        st.code(json.dumps(draft, indent=2))
        _render_user_label_preview(draft)

        b1, b2 = st.columns(2)
        with b1:
            if st.button("Close preview", use_container_width=True):
                st.session_state.add_preview_open = False
        with b2:
            if st.button("Save from preview", use_container_width=True):
                # Close panel first, then use the same save flow:
                st.session_state.add_preview_open = False
                _do_save()


def view() -> None:
    """Alias for router compatibility."""
    show()


def page_add_warehouse() -> None:
    """Alias for legacy imports."""
    show()
