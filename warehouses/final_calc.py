# warehouses/final_calc.py
import os
import json
import streamlit as st

JSON_PATH = "data/customers.json"


# ==============================================================
# JSON helpers
# ==============================================================

@st.cache_data(show_spinner=False, ttl=300)
def _load_json_with_mtime(path: str, mtime: float):
    """Cache JSON content keyed by file mtime so edits bust the cache."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _safe_read_json(path: str):
    """Read the customers JSON from disk; render an error if unavailable."""
    if not os.path.exists(path):
        st.error(f"Customer JSON not found: {path}")
        return None
    try:
        mtime = os.path.getmtime(path)
        return _load_json_with_mtime(path, mtime)
    except Exception as e:
        st.error(f"Customer JSON could not be read.\n\nError: {e}")
        return None


def _get_customers(data: list[dict]) -> list[str]:
    """
    Extract a sorted list of customer names from the JSON structure produced by tools/xlsx_to_json.py:
    [{"name": "...", "addresses": [...]}, ...]
    """
    names = [str(x.get("name", "")).strip() for x in data]
    names = [n for n in names if n and n.lower() != "nan"]
    names.sort()
    return names


def _get_addresses_for(data: list[dict], customer: str) -> list[str]:
    """Return unique, non-empty addresses for the selected customer."""
    for row in data:
        if str(row.get("name", "")).strip().casefold() == customer.strip().casefold():
            raw = row.get("addresses", []) or []
            seen, out = set(), []
            for x in raw:
                s = str(x).strip()
                if s and s not in seen:
                    out.append(s)
                    seen.add(s)
            return out
    return []


# ==============================================================
# Final calculator (P&L)
# ==============================================================

def final_calculator(pieces: int, vvp_cost_per_piece_rounded: float):
    """
    Final P&L step.

    Inputs:
      - pieces: order quantity
      - vvp_cost_per_piece_rounded: rounded unit VVP (operational) cost from the warehouse calculation

    What we compute (per your spec):
      * gross_cost                 = (rounded VVP + purchase price per piece) × pieces
      * total_revenue              = (sales price per piece) × pieces
      * gross_profit               = total_revenue − gross_cost
      * net_profit                 = total_revenue − gross_cost − delivery_transport_total
        (i.e., delivery is excluded from gross, included only in net)

    UI:
      - The “Total Cost (€)” metric displays GROSS COST (not including delivery).
      - “Unit Cost (€/pc)” displays VVP + Purchase (not including delivery).
      - Delivery is shown separately and used only in Net Profit/Margin.
    """
    st.subheader("Final Calculator")

    # ---- Load customers JSON ----
    data = _safe_read_json(JSON_PATH)
    if data is None:
        st.stop()

    # ---- Customer selection ----
    customers = _get_customers(data)
    customer = (
        st.selectbox("Customer", ["-- Select --"] + customers, index=0)
        if customers else None
    )

    # ---- Customer warehouse selection (optional) ----
    customer_wh = None
    if customer and customer != "-- Select --":
        addrs = _get_addresses_for(data, customer)
        if addrs:
            customer_wh = st.selectbox(
                "Customer Warehouse", ["-- Select --"] + addrs, index=0
            )
        else:
            st.warning("No warehouse address found for the selected customer.")

    # ---- Commercial inputs ----
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
        delivery_transport_total = st.number_input(
            "Delivery Transportation Cost (TOTAL €)",
            min_value=0.0,
            step=1.0,
            format="%.2f",
            help="Total delivery transport cost for this order (not per piece).",
        )

    # ---- Derived delivery (per piece) ----
    delivery_transport_per_piece = (delivery_transport_total / pieces) if pieces else 0.0

    # ---- Header context line ----
    st.caption(
        f"Rounded VVP / pc: **€{vvp_cost_per_piece_rounded:.2f}**  |  "
        f"Purchase / pc: **€{purchase_price_per_piece:.3f}**  |  "
        f"Delivery / pc: **€{delivery_transport_per_piece:.4f}**  |  "
        f"Qty: **{pieces} pcs**"
    )

    # ==============================================================
    # CORE CALCULATIONS (per your definitions)
    # ==============================================================

    # Unit costs
    unit_vvp = vvp_cost_per_piece_rounded
    unit_purchase = purchase_price_per_piece
    unit_delivery = delivery_transport_per_piece

    # Unit totals (explicit for clarity)
    unit_cost_excl_delivery = unit_vvp + unit_purchase              # used for GROSS
    unit_cost_incl_delivery = unit_cost_excl_delivery + unit_delivery  # used for NET if needed

    # Totals
    gross_cost = unit_cost_excl_delivery * pieces                   # what you want to show as “Total Cost (€)”
    total_revenue = sales_price_per_piece * pieces
    total_cost_incl_delivery = unit_cost_incl_delivery * pieces     # informational; not shown as the main "Total Cost"

    # Profits & margins
    gross_profit = total_revenue - gross_cost
    gross_margin = (gross_profit / total_revenue * 100.0) if total_revenue > 0 else 0.0

    net_profit = total_revenue - gross_cost - delivery_transport_total
    net_margin = (net_profit / total_revenue * 100.0) if total_revenue > 0 else 0.0

    # ==============================================================
    # Summary cards
    # ==============================================================

    st.markdown("---")
    st.subheader("Summary")

    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        # IMPORTANT: per your request, “Total Cost (€)” == GROSS COST (excludes delivery)
        st.metric("Total Cost (€)", f"{gross_cost:.2f}")
    with r1c2:
        st.metric("Unit Cost (€/pc)", f"{unit_cost_excl_delivery:.3f}")
    with r1c3:
        st.metric("Total Revenue (€)", f"{total_revenue:.2f}")

    g_col, n_col = st.columns(2)
    with g_col:
        st.metric("Gross Profit (€)", f"{gross_profit:.2f}")
        st.metric(
            "Gross Margin (%)",
            f"{gross_margin:.2f}",
            delta=f"{gross_margin:.2f}%",
            delta_color="normal",
        )
    with n_col:
        st.metric("Net Profit (€)", f"{net_profit:.2f}")
        st.metric(
            "Net Margin (%)",
            f"{net_margin:.2f}",
            delta=f"{net_margin:.2f}%",
            delta_color="normal",
        )

    # ==============================================================
    # Detailed breakdown (for auditability)
    # ==============================================================

    with st.expander("Breakdown"):
        st.write(
            {
                "Customer": customer if customer and customer != "-- Select --" else None,
                "Customer warehouse": (
                    customer_wh if customer_wh and customer_wh != "-- Select --" else None
                ),

                # Unit costs
                "Unit VVP operational cost (€/pc)": round(unit_vvp, 2),
                "Unit purchase cost (€/pc)": round(unit_purchase, 3),
                "Unit delivery cost (€/pc)": round(unit_delivery, 4),

                # Per-unit totals (both views)
                "Unit cost EXCL delivery (€/pc) [VVP + Purchase]": round(unit_cost_excl_delivery, 3),
                "Unit cost INCL delivery (€/pc) [VVP + Purchase + Delivery]": round(unit_cost_incl_delivery, 3),

                # Order-level costs
                "Delivery transport (TOTAL €)": round(delivery_transport_total, 2),

                # Totals used in cards
                "TOTAL COST shown (Gross cost, €) [Unit excl delivery × qty]": round(gross_cost, 2),
                "Total cost INCL delivery (informational, €)": round(total_cost_incl_delivery, 2),

                # Revenue & profits
                "Sales price (€/pc)": round(sales_price_per_piece, 3),
                "Quantity (pcs)": pieces,
                "Total revenue (€)": round(total_revenue, 2),

                "Gross profit (€) [Revenue − Gross cost]": round(gross_profit, 2),
                "Gross margin (%)": round(gross_margin, 2),

                "Net profit (€) [Revenue − Gross cost − Delivery]": round(net_profit, 2),
                "Net margin (%)": round(net_margin, 2),
            }
        )

    # Data source info (absolute path helps during local debugging)
    st.caption(f"Data source: `{os.path.abspath(JSON_PATH)}`")
