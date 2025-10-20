# admin/pages/helpers.py
"""
Shared helpers for admin pages: default structures, normalization, and UI blocks.
"""

from __future__ import annotations

from typing import Any, Dict, List
from pathlib import Path
import json as _json

import streamlit as st


# ---------------- Small helpers ----------------
def warehouse_ids(catalog: Dict[str, Any], list_warehouses_func) -> List[str]:
    """Return a list of warehouse IDs from the catalog using the provided lister."""
    return [w.get("id") for w in list_warehouses_func(catalog) if w.get("id")]


def default_rates() -> Dict[str, float]:
    """Return default (zeroed) rate fields."""
    return {"inbound": 0.0, "outbound": 0.0, "storage": 0.0, "order_fee": 0.0}


def default_features() -> Dict[str, Any]:
    """Return the default features structure."""
    return {
        "labeling": {
            "enabled": False,
            "label_per_piece": 0.0,
            "labelling_per_piece": 0.0,  # legacy alias
            "cost_per_unit": 0.0,  # legacy compatibility
        },
        "transfer": {
            "mode": "none",  # none | manual | json_lookup
            "manual_cost": 0.0,
            "lookup_file": "data/svz_truck_rates.json",
        },
        "double_stack": False,
        "second_leg": {"enabled": False, "target": None},
    }


def normalize_features(raw: Any) -> Dict[str, Any]:
    """Normalize a features payload into the current canonical structure."""
    base = default_features()
    if not isinstance(raw, dict):
        return base

    out: Dict[str, Any] = {
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
        out["labeling"]["label_per_piece"] = float(
            lab.get("label_per_piece", 0.0) or 0.0
        )
        out["labeling"]["labelling_per_piece"] = float(
            lab.get("labelling_per_piece", 0.0) or 0.0
        )
        cpu = lab.get("cost_per_unit")
        if (
            cpu is not None
            and out["labeling"]["labelling_per_piece"] == 0.0
            and out["labeling"]["label_per_piece"] == 0.0
        ):
            try:
                out["labeling"]["labelling_per_piece"] = float(cpu) or 0.0
            except Exception:  # noqa: BLE001
                pass
        out["labeling"]["cost_per_unit"] = float(
            lab.get("cost_per_unit", 0.0) or 0.0
        )

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


def normalize_rates(raw: Any) -> Dict[str, float]:
    """Normalize a rates payload, filling missing values with defaults."""
    base = default_rates()
    if not isinstance(raw, dict):
        return base
    return {
        "inbound": float(raw.get("inbound", base["inbound"]) or 0.0),
        "outbound": float(raw.get("outbound", base["outbound"]) or 0.0),
        "storage": float(raw.get("storage", base["storage"]) or 0.0),
        "order_fee": float(raw.get("order_fee", base["order_fee"]) or 0.0),
    }


# ---------------- UI blocks ----------------
def rates_block(prefix: str, rates: Dict[str, float]) -> Dict[str, float]:
    """Render a rates input block and return the updated values."""
    st.subheader("Rates (€)")
    c1, c2 = st.columns(2)
    with c1:
        inbound = st.number_input(
            "Inbound €/pallet",
            value=float(rates.get("inbound", 0.0)),
            key=f"{prefix}_in",
            min_value=0.0,
            step=0.1,
        )
        storage = st.number_input(
            "Storage €/pallet/week",
            value=float(rates.get("storage", 0.0)),
            key=f"{prefix}_st",
            min_value=0.0,
            step=0.1,
        )
    with c2:
        outbound = st.number_input(
            "Outbound €/pallet",
            value=float(rates.get("outbound", 0.0)),
            key=f"{prefix}_out",
            min_value=0.0,
            step=0.1,
        )
        order_fee = st.number_input(
            "Order fee €",
            value=float(rates.get("order_fee", 0.0)),
            key=f"{prefix}_ord",
            min_value=0.0,
            step=0.1,
        )
    return {
        "inbound": float(inbound),
        "outbound": float(outbound),
        "storage": float(storage),
        "order_fee": float(order_fee),
    }


def features_block(
    prefix: str,
    features: Dict[str, Any],
    warehouse_ids: List[str],
    wid: str | None = None,
) -> Dict[str, Any]:
    """Render the features UI block and return the updated features payload."""
    try:
        import pandas as pd  # noqa: F401  # optional for Excel uploads
        _has_pandas = True
    except Exception:  # noqa: BLE001
        _has_pandas = False

    feats = normalize_features(features)

    with st.expander("Features", expanded=False):
        # Labeling
        labeling_enabled = st.checkbox(
            "Labeling service available",
            value=bool(feats.get("labeling", {}).get("enabled", False)),
            key=f"{prefix}_labeling_en",
        )
        label_per_piece = float(
            feats["labeling"].get("label_per_piece", 0.0) or 0.0
        )
        labelling_per_piece = float(
            feats["labeling"].get("labelling_per_piece", 0.0) or 0.0
        )
        if labeling_enabled:
            c1, c2 = st.columns(2)
            with c1:
                label_per_piece = st.number_input(
                    "Label cost (€/piece)",
                    min_value=0.0,
                    value=label_per_piece,
                    step=0.001,
                    format="%.3f",
                    key=f"{prefix}_label_cost",
                )
            with c2:
                labelling_per_piece = st.number_input(
                    "Labelling cost (€/piece)",
                    min_value=0.0,
                    value=labelling_per_piece,
                    step=0.001,
                    format="%.3f",
                    key=f"{prefix}_labelling_cost",
                )

        # Transfer
        transfer_required = st.checkbox(
            "Labelling transfer required (external site)",
            value=(feats.get("transfer", {}).get("mode", "none") != "none"),
            key=f"{prefix}_transfer_req",
        )

        transfer_mode_out = "none"
        transfer_lookup_file = feats.get("transfer", {}).get("lookup_file") or (
            f"data/transfer_rates_{wid}.json" if wid else "data/transfer_rates.json"
        )
        transfer_manual_cost = float(
            feats.get("transfer", {}).get("manual_cost", 0.0) or 0.0
        )
        double_stack = bool(feats.get("double_stack", False))

        if transfer_required:
            mode_choice = st.radio(
                "How do you want to provide the transfer cost?",
                ["lookup (JSON table)", "manual (fixed per leg)"],
                horizontal=True,
                index=0
                if feats.get("transfer", {}).get("mode") in ("json_lookup", "lookup")
                else 1,
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
                    placeholder=(
                        f"data/transfer_rates_{wid}.json"
                        if wid
                        else "data/transfer_rates.json"
                    ),
                    key=f"{prefix}_transfer_json",
                )

                if up is not None:
                    try:
                        app_root = Path(__file__).resolve().parents[2]  # .../cost-app
                        data_dir = app_root / "data"
                        data_dir.mkdir(parents=True, exist_ok=True)
                        target_rel = Path(
                            f"data/transfer_rates_{wid}.json"
                            if wid
                            else "data/transfer_rates.json"
                        )
                        target_abs = app_root / target_rel

                        if up.name.lower().endswith(".json"):
                            content = _json.loads(up.getvalue().decode("utf-8"))
                            with open(target_abs, "w", encoding="utf-8") as f:
                                _json.dump(content, f, ensure_ascii=False, indent=2)
                        else:
                            if not _has_pandas:
                                st.error(
                                    "Excel upload requires pandas. "
                                    "Upload JSON or install pandas."
                                )
                                st.stop()

                            import pandas as pd  # type: ignore  # noqa: WPS433

                            df = pd.read_excel(up)
                            cols_lower = {c: c.lower() for c in df.columns}
                            df = df.rename(columns=cols_lower)
                            if not {"pallets", "truck_cost"}.issubset(df.columns):
                                st.error(
                                    "Excel must contain columns: pallets, truck_cost"
                                )
                                st.stop()
                            data = [
                                {
                                    "pallets": int(r.pallets),
                                    "truck_cost": float(r.truck_cost),
                                }
                                for r in df[["pallets", "truck_cost"]].itertuples(
                                    index=False
                                )
                            ]
                            with open(target_abs, "w", encoding="utf-8") as f:
                                _json.dump(data, f, ensure_ascii=False, indent=2)

                        transfer_lookup_file = str(target_rel).replace("\\", "/")
                        st.success(f"Lookup table saved to: {transfer_lookup_file}")
                    except Exception as ex:  # noqa: BLE001
                        st.error(f"Failed to save uploaded file: {ex}")

            else:
                transfer_mode_out = "manual"
                transfer_manual_cost = st.number_input(
                    "Transfer fixed cost per leg (€)",
                    min_value=0.0,
                    value=float(transfer_manual_cost),
                    step=1.0,
                    key=f"{prefix}_transfer_fixed",
                )

        # Second leg: admin toggles availability; target is chosen in the user app.
        second_leg_enabled = st.checkbox(
            "Allow second leg",
            value=bool(feats.get("second_leg", {}).get("enabled", False)),
            key=f"{prefix}_secondleg",
        )

    return {
        "labeling": {
            "enabled": bool(labeling_enabled),
            "label_per_piece": float(label_per_piece or 0.0),
            "labelling_per_piece": float(labelling_per_piece or 0.0),
            "cost_per_unit": float(
                feats.get("labeling", {}).get("cost_per_unit", 0.0) or 0.0
            ),
        },
        "transfer": {
            "mode": transfer_mode_out,
            "manual_cost": float(transfer_manual_cost or 0.0),
            "lookup_file": transfer_lookup_file,
        },
        "double_stack": bool(double_stack),
        "second_leg": {"enabled": bool(second_leg_enabled)},
    }
