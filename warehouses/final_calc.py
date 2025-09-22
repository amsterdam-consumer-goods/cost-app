# warehouses/final_calc.py
import os
import json
import streamlit as st

JSON_PATH = "data/customers.json"

# ---------------------------
# JSON helpers (cached read)
# ---------------------------
@st.cache_data(show_spinner=False, ttl=300)
def _load_json_with_mtime(path: str, mtime: float):
    """Cache JSON by file mtime; any change invalidates the cache."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _safe_read_json(path: str):
    """Read customers JSON, with basic error reporting."""
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
    """Return sorted unique customer names from JSON rows."""
    names = [str(x.get("name", "")).strip() for x in data]
    names = [n for n in names if n and n.lower() != "nan"]
    names.sort()
    return names

def _get_addresses_for(data: list[dict], customer: str) -> list[str]:
    """Return de-duplicated, ordered list of addresses for a customer."""
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

# ---------------------------
# Final calculator
# ---------------------------
def final_calculator(pieces: int, vvp_cost_per_piece_rounded: float):
    """
    Final step (P&L):
      • Reads customers & addresses from data/customers.json
      • Gets purchase/sales prices and delivery transport TOTAL
      • Computes:
          - unit_gross_cost  = VVP/pc + Purchase/pc
          - total_gross_cost = unit_gross_cost × qty      (this is shown as 'Total Cost (€)')
          - gross_profit     = Revenue − total_gross_cost
          - net_profit       = Revenue − total_gross_cost − DeliveryTransportTOTAL
      • Shows a compact summary and a detailed breakdown.
    """
    st.subheader("Final Calculator")

    # Load customer data
    data = _safe_read_json(JSON_PATH)
    if data is None:
        st.stop()

    # Customer and address pickers
    customers = _get_customers(data)
    customer = st.selectbox("Customer", ["-- Select --"] + customers, index=0) if customers else None

    customer_wh = None
    if customer and customer != "-- Select --":
        addrs = _get_addresses_for(data, customer)
        if addrs:
            customer_wh = st.selectbox("Customer Warehouse", ["-- Select --"] + addrs, index=0)
        else:
            st.warning("No warehouse address found for the selected customer.")

    # Commercial inputs
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
            min_value=0.0, step=1.0, format="%.2f",
            help="Total delivery transport cost for this order (not per piece).",
        )

    # Derived helpers
    unit_vvp        = float(vvp_cost_per_piece_rounded)
    unit_purchase   = float(purchase_price_per_piece)
    unit_delivery   = (delivery_transport_total / pieces) if pieces else 0.0  # for info display only

    unit_gross_cost   = unit_vvp + unit_purchase                 # delivery NOT included
    total_gross_cost  = unit_gross_cost * pieces                 # shown as 'Total Cost (€)'
    total_revenue     = sales_price_per_piece * pieces
    gross_profit      = total_revenue - total_gross_cost
    net_profit        = total_revenue - total_gross_cost - delivery_transport_total

    gross_margin_pct  = (gross_profit / total_revenue * 100.0) if total_revenue > 0 else 0.0
    net_margin_pct    = (net_profit   / total_revenue * 100.0) if total_revenue > 0 else 0.0
    total_cost = (unit_gross_cost * pieces) + delivery_transport_total
    # Context line
    st.caption(
        f"Rounded VVP Cost / pc: **€{unit_vvp:.2f}**  |  "
        f"Purchase / pc: **€{unit_purchase:.3f}**  |  "
        f"Delivery Transport / pc: **€{unit_delivery:.4f}**  |  "
        f"Pieces: **{pieces}**"
    )

    # ---------------------------
    # Summary
    # ---------------------------
    st.markdown("---")
    st.subheader("Summary")

    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        st.metric("Total Cost (€)", f"{total_gross_cost:.2f}")       # per your preference
    with r1c2:
        st.metric("Unit Cost (€ / pc)", f"{unit_gross_cost:.3f}")     # VVP + Purchase (no delivery)
    with r1c3:
        st.metric("Total Revenue (€)", f"{total_revenue:.2f}")

    g_col, n_col = st.columns(2)
    with g_col:
        st.metric("Gross Profit (€)", f"{gross_profit:.2f}")
        st.metric("Gross Margin (%)", f"{gross_margin_pct:.2f}",
                  delta=f"{gross_margin_pct:.2f}%", delta_color="normal")
    with n_col:
        st.metric("Net Profit (€)", f"{net_profit:.2f}")
        st.metric("Net Margin (%)", f"{net_margin_pct:.2f}",
                  delta=f"{net_margin_pct:.2f}%", delta_color="normal")

    # ---------------------------
    # Breakdown
    # ---------------------------
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

    st.caption(f"Data source: `{os.path.abspath(JSON_PATH)}`")
