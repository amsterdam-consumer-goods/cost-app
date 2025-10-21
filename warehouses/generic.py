from __future__ import annotations

import json
import math
from io import BytesIO
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import streamlit as st
from warehouses.final_calc import final_calculator
from warehouses.second_leg import second_leg_ui

# optional Excel support
try:
    import pandas as pd  # type: ignore
except Exception:
    pd = None


@st.cache_data(show_spinner=False)
def _load_truck_rates_any(path_str: str) -> Dict[int, float]:
    """Load {pallets -> truck_cost} from .json/.xlsx/.xls/.csv. Returns {} on failure."""
    if not path_str:
        return {}
    p = Path(path_str)
    if not p.exists():
        return {}

    rates: Dict[int, float] = {}
    suffix = p.suffix.lower()

    if suffix == ".json":
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if isinstance(data, dict):
            for k, v in data.items():
                try:
                    rates[int(k)] = float(v)
                except Exception:
                    pass
        elif isinstance(data, list):
            for row in data:
                try:
                    rates[int(row["pallets"])] = float(row["truck_cost"])
                except Exception:
                    pass
        return rates

    if suffix in (".xlsx", ".xls", ".csv") and pd is not None:
        try:
            df = pd.read_csv(p) if suffix == ".csv" else pd.read_excel(p, sheet_name=0)
            for _, row in df.iterrows():
                try:
                    rates[int(row["pallets"])] = float(row["truck_cost"])
                except Exception:
                    continue
        except Exception:
            return {}
        return rates

    return {}


def _lookup_truck_cost(rates: Dict[int, float], pallets_for_lookup: int) -> float:
    """Return rate for n pallets, falling back to nearest lower key."""
    if not rates:
        return 0.0
    n = max(1, min(66, int(pallets_for_lookup)))
    if n in rates:
        return rates[n]
    lower = [k for k in rates if k <= n]
    return rates[max(lower)] if lower else 0.0


def compute_generic(
    *,
    wh: Dict[str, Any],
    all_whs_map: Dict[str, Dict[str, Any]],
    pieces: int,
    pallets: int,
    weeks: int,
    buying_transport_cost: float,
    pallet_unit_cost: float,
) -> None:
    name = (wh.get("name") or wh.get("id") or "Warehouse")
    country = wh.get("country", "")
    title = f"{country} / {name}" if country else f"{name}"
    st.subheader(title)

    rates = wh.get("rates", {}) or {}
    features = wh.get("features", {}) or {}

    inbound_per = float(rates.get("inbound", 0.0))
    outbound_per = float(rates.get("outbound", 0.0))
    storage_per = float(rates.get("storage", 0.0))
    order_fee = float(rates.get("order_fee", 0.0))

    # keep a small on-screen note (not included in Excel/Print)
    st.caption(
        f"Rates used — inbound: €{inbound_per:.2f}/pallet • "
        f"outbound: €{outbound_per:.2f}/pallet • "
        f"storage: €{storage_per:.2f}/pallet/week • "
        f"order fee: €{order_fee:.2f}"
    )

    inbound_cost = float(pallets) * inbound_per
    outbound_cost = float(pallets) * outbound_per
    storage_cost = float(pallets) * float(weeks) * storage_per
    warehousing_one_round = inbound_cost + outbound_cost + storage_cost + order_fee

    # labelling
    label_total = 0.0
    labelling_required = False
    lab = features.get("label_costs")
    if isinstance(lab, dict) and ("label" in lab or "labelling" in lab):
        st.markdown("### Labelling")
        labelling_required = st.checkbox("This order will be labelled.", key=f"lab_required_{name}")
        if labelling_required:
            label_per_piece = float(lab.get("label", 0.0))
            labelling_per_piece = float(lab.get("labelling", 0.0))
            label_total = (label_per_piece + labelling_per_piece) * float(pieces)
        st.caption(f"Per piece — label: {lab.get('label',0)} / labelling: {lab.get('labelling',0)}")

    # transfer (labelling legs)
    transfer_total = 0.0
    extra_warehousing_on_return = 0.0
    if bool(features.get("transfer", False)):
        if isinstance(features.get("label_costs"), dict) and not labelling_required:
            pass
        else:
            st.subheader("Labelling Transfer")
            mode_raw = str(features.get("transfer_mode", "")).strip().lower()
            if mode_raw in ("json_lookup", "lookup", "excel_lookup"):
                mode = "excel"
            elif mode_raw in ("manual_fixed", "fixed"):
                mode = "fixed"
            else:
                mode = mode_raw

            if mode == "excel":
                wid = str(wh.get("id") or name).lower().replace(" ", "_")
                double_stack_flag = bool(features.get("double_stack", False))
                double_stack = st.checkbox("Double Stackable", value=False, key=f"ds_{wid}") if double_stack_flag else False

                wh_to_lab = st.checkbox("Warehouse → Labelling", value=False, key=f"wh2lab_{wid}")
                lab_to_wh = st.checkbox("Labelling → Warehouse", value=False, key=f"lab2wh_{wid}")
                if not (wh_to_lab or lab_to_wh):
                    st.info("Select at least one transfer leg (WH→Lab and/or Lab→WH).")

                lookup_path = str(features.get("transfer_excel") or "")
                rates_excel = _load_truck_rates_any(lookup_path)

                pallets_for_lookup = math.ceil(pallets / 2) if (double_stack and pallets > 0) else pallets
                truck_cost = _lookup_truck_cost(rates_excel, pallets_for_lookup) if (wh_to_lab or lab_to_wh) else 0.0

                wh_to_lab_cost = truck_cost if wh_to_lab else 0.0
                lab_to_wh_cost = truck_cost if lab_to_wh else 0.0
                transfer_total = wh_to_lab_cost + lab_to_wh_cost

                if wh_to_lab and lab_to_wh:
                    extra_warehousing_on_return = float(pallets) * (inbound_per + outbound_per)

            elif mode == "fixed":
                fixed = float(features.get("transfer_fixed", 0.0))
                st.info(f"Fixed transfer (catalog): €{fixed:,.2f}")
                transfer_total = fixed
            else:
                st.caption("Transfer disabled or unsupported mode.")

    pallet_cost_total = (float(pallet_unit_cost) or 0.0) * float(pallets) if (pallet_unit_cost or 0) > 0 else 0.0

    st.subheader("Second Warehouse Transfer")
    second_leg_added, second_leg_breakdown = second_leg_ui(
        primary_warehouse=title,
        pallets=pallets,
    )

    warehousing_total = warehousing_one_round + extra_warehousing_on_return
    base_total = warehousing_total + float(buying_transport_cost) + pallet_cost_total + label_total + transfer_total
    total_cost = base_total + second_leg_added

    cpp = (total_cost / float(pieces)) if pieces else 0.0
    cpp_rounded = math.ceil(cpp * 100) / 100.0

    st.caption(f"You are entering inputs for **{title}**")

    st.markdown("---")
    st.subheader("VVP Results")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Cost (€)", f"{total_cost:.2f}")
    with c2:
        st.metric("Cost per piece (€)", f"{cpp:.4f}")
    with c3:
        st.metric("Rounded Cost per piece (€)", f"{cpp_rounded:.2f}")

    # final step (returns dict for export)
    fc = final_calculator(pieces=pieces, vvp_cost_per_piece_rounded=cpp_rounded)

    # on-screen breakdown
    with st.expander("Breakdown"):
        rows = {
            "Inbound Cost (€)": round(inbound_cost, 2),
            "Outbound Cost (€)": round(outbound_cost, 2),
            "Storage Cost (€)": round(storage_cost, 2),
            "Order fee (€)": round(order_fee, 2),
            "Warehousing Total (1st leg) (€)": round(warehousing_one_round, 2),
            "Extra Warehousing on Return (€)": round(extra_warehousing_on_return, 2),
            "Labelling required?": bool(labelling_required),
            "Labelling total (€)": round(label_total, 2),
            "Transfer total (€)": round(transfer_total, 2),
            "Pallet unit (€/pallet)": round(float(pallet_unit_cost) or 0.0, 2),
            "Pallets (#)": pallets,
            "Pallet cost total (€)": round(pallet_cost_total, 2),
            "Buying transport (€ total)": round(float(buying_transport_cost), 2),
        }
        if second_leg_breakdown:
            rows.update(second_leg_breakdown)
        rows.update(
            {
                "Warehousing Total (incl. return) (€)": round(warehousing_total, 2),
                "TOTAL (€)": round(total_cost, 2),
                "Cost per piece (€)": round(cpp, 4),
                "Rounded VPP (€)": round(cpp_rounded, 2),
            }
        )
        if isinstance(fc, dict):
            rows.update(
                {
                    "Sales price (€ / pc)": fc.get("sales_price_cpp"),
                    "Unit purchase (€ / pc)": fc.get("unit_purchase_cpp"),
                    "Unit delivery (€ / pc)": fc.get("unit_delivery_cpp"),
                    "Unit gross cost (€ / pc)": fc.get("unit_gross_cpp"),
                    "Total revenue (€)": fc.get("total_revenue"),
                    "Gross profit (€)": fc.get("gross_profit"),
                    "Gross margin (%)": fc.get("gross_margin_pct"),
                    "Net profit (€)": fc.get("net_profit"),
                    "Net margin (%)": fc.get("net_margin_pct"),
                    "Delivery transport (TOTAL €)": fc.get("delivery_transport_total"),
                }
            )
        st.write(rows)

    # -------- Export / Print (no Rates section) --------
    st.markdown("---")
    st.subheader("Save / Export")

    def _blank(x):
        return "" if (x is None or x == "" or x == 0 or x == 0.0) else x

    export_rows: list[tuple[str, object]] = []

    # Warehousing
    export_rows.append(("— Warehousing —", ""))
    export_rows += [
        ("Inbound Cost (€)", round(inbound_cost, 2)),
        ("Outbound Cost (€)", round(outbound_cost, 2)),
        ("Storage Cost (€)", round(storage_cost, 2)),
    ]
    if extra_warehousing_on_return > 0:
        export_rows.append(("Warehousing extra (return) (€)", round(extra_warehousing_on_return, 2)))
    export_rows.append(("Warehousing Total (incl. return) (€)", round(warehousing_total, 2)))

    # Commercials
    sales = fc.get("sales_price_cpp") if isinstance(fc, dict) else None
    purch = fc.get("unit_purchase_cpp") if isinstance(fc, dict) else None
    unit_del = fc.get("unit_delivery_cpp") if isinstance(fc, dict) else None
    del_total = fc.get("delivery_transport_total") if isinstance(fc, dict) else None

    export_rows.append(("", ""))
    export_rows.append(("— Commercials —", ""))
    export_rows += [
        ("Sales price (€ / pc)", _blank(sales)),
        ("Unit purchase (€ / pc)", _blank(purch)),
        ("Unit delivery (€ / pc)", _blank(unit_del)),
        ("Delivery transport (TOTAL €)", _blank(del_total)),
    ]

    # Results
    grosp = fc.get("gross_profit") if isinstance(fc, dict) else None
    grosm = fc.get("gross_margin_pct") if isinstance(fc, dict) else None
    netp = fc.get("net_profit") if isinstance(fc, dict) else None
    netm = fc.get("net_margin_pct") if isinstance(fc, dict) else None

    export_rows.append(("", ""))
    export_rows.append(("— Results —", ""))
    export_rows += [
        ("TOTAL (€)", round(total_cost, 2)),
        ("Cost per piece (€)", round(cpp, 4)),
        ("Rounded CPP (€)", round(cpp_rounded, 2)),
        ("Gross profit (€)", _blank(grosp)),
        ("Gross margin (%)", _blank(grosm)),
        ("Net profit (€)", _blank(netp)),
        ("Net margin (%)", _blank(netm)),
    ]

    # Excel (single sheet: VVP)
    col_a, col_b = st.columns([1.6, 1])
    with col_a:
        if pd is not None:
            buf = BytesIO()
            now = datetime.now()
            calc_id = now.strftime("%Y%m%d-%H%M%S")
            primary_for_file = title.replace(" / ", "_").replace(" ", "_").lower()

            bd_rows = [{"Item": k, "Value": ("" if v in (None, "") else v)} for k, v in export_rows]
            with pd.ExcelWriter(buf, engine="xlsxwriter") as xw:
                df = pd.DataFrame(bd_rows)
                df.to_excel(xw, index=False, sheet_name="VVP")
                ws = xw.sheets["VVP"]
                ws.set_column(0, 0, 42)
                ws.set_column(1, 1, 22)

            st.download_button(
                "Download Excel",
                data=buf.getvalue(),
                file_name=f"vvp_{primary_for_file}_{calc_id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        else:
            st.caption("Install pandas for Excel export.")

    # Print
    with col_b:
        if st.button("Print", use_container_width=True):
            def rows_html(rows: list[tuple[str, object]]) -> str:
                return "".join(
                    f"<tr><td>{k}</td><td style='text-align:right'>{'' if v in (None, '') else v}</td></tr>"
                    for k, v in rows
                )

            html = f"""
            <html>
              <head>
                <meta charset="utf-8" />
                <title>VVP — {title}</title>
                <style>
                  body {{ font-family: Arial, sans-serif; padding: 18px; }}
                  h1 {{ font-size: 18px; margin: 0 0 6px; }}
                  .meta {{ color:#666; font-size: 12px; margin-bottom: 10px; }}
                  table {{ width:100%; border-collapse:collapse; }}
                  th, td {{ border:1px solid #ddd; padding:6px 8px; font-size:12px; }}
                  th {{ background:#f5f5f5; text-align:left; }}
                  @media print {{ @page {{ size: A4 portrait; margin: 12mm; }} }}
                </style>
              </head>
              <body>
                <h1>VVP Calculator</h1>
                <div class="meta">{title} • {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
                <table>
                  <thead><tr><th>Item</th><th>Value</th></tr></thead>
                  <tbody>{rows_html(export_rows)}</tbody>
                </table>
                <script>window.onload = () => window.print();</script>
              </body>
            </html>
            """
            st.components.v1.html(html, height=0)
            st.toast("Opening print dialog…", icon="🖨️")
