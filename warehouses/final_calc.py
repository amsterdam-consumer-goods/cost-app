# warehouses/final_calc.py
import os
import json
import streamlit as st

JSON_PATH = "data/customers.json"   # <-- Excel yerine JSON

# ---------------------------
# JSON helpers
# ---------------------------
@st.cache_data(show_spinner=False, ttl=300)
def _load_json_with_mtime(path: str, mtime: float):
    """Dosya mtime’a göre cache; dosya değişince cache bozulur."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _safe_read_json(path: str):
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
    # tools/xlsx_to_json.py çıktısı: [{"name": "...", "addresses": [...]}, ...]
    names = [str(x.get("name", "")).strip() for x in data]
    names = [n for n in names if n and n.lower() != "nan"]
    names.sort()
    return names

def _get_addresses_for(data: list[dict], customer: str) -> list[str]:
    for row in data:
        if str(row.get("name", "")).strip().casefold() == customer.strip().casefold():
            raw = row.get("addresses", []) or []
            out, seen = [], set()
            for x in raw:
                s = str(x).strip()
                if s and s not in seen:
                    out.append(s); seen.add(s)
            return out
    return []

# ---------------------------
# Final calculator
# ---------------------------
def final_calculator(pieces: int, vvp_cost_per_piece_rounded: float):
    """
    Final step:
      - Müşteri & adresleri data/customers.json’dan okur.
      - Satın alma / satış fiyatı ile teslimat taşıma toplamını alır.
      - Teslimat €/pc hesaplayıp unit total costa ekler.
      - Özet + Gross/Net metriklerini gösterir (margin renkli).
    """
    st.subheader("Final Calculator")

    # JSON yükle
    data = _safe_read_json(JSON_PATH)
    if data is None:
        st.stop()

    # Customer dropdown
    customers = _get_customers(data)
    customer = st.selectbox("Customer", ["-- Select --"] + customers, index=0) if customers else None

    # Address dropdown
    customer_wh = None
    if customer and customer != "-- Select --":
        addrs = _get_addresses_for(data, customer)
        if addrs:
            customer_wh = st.selectbox("Customer Warehouse", ["-- Select --"] + addrs, index=0)
        else:
            st.warning("No warehouse address found for the selected customer.")

    # Prices & delivery total
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
            "Delivery Transportation Cost (TOTAL €)", min_value=0.0, step=1.0, format="%.2f",
            help="Total delivery transport cost for this order (not per piece)."
        )

    # Derived
    delivery_transport_per_piece = (delivery_transport_total / pieces) if pieces else 0.0

    st.caption(
        f"Rounded VVP Cost / pc: **€{vvp_cost_per_piece_rounded:.2f}**  |  "
        f"Purchase / pc: **€{purchase_price_per_piece:.3f}**  |  "
        f"Delivery Transport / pc: **€{delivery_transport_per_piece:.4f}**  |  "
        f"Pieces: **{pieces}**"
    )

    # --- P&L calculations ---
    unit_operational_cost = vvp_cost_per_piece_rounded
    unit_total_cost = (
        unit_operational_cost
        + purchase_price_per_piece
        + delivery_transport_per_piece
    )

    # Totals
    total_cost    = unit_total_cost * pieces
    total_revenue = sales_price_per_piece * pieces

    # PROFIT/MARGINS (naming corrected earlier requests)
    # Gross = Revenue − Purchase (ops & delivery excluded)
    gross_cost   = purchase_price_per_piece * pieces
    gross_profit = total_revenue - total_cost
    gross_margin = (gross_profit / total_revenue * 100.0) if total_revenue > 0 else 0.0

    # Net = Revenue − ALL costs (unit_total_cost already includes ops + purchase + delivery)
    net_profit = total_revenue - total_cost
    net_margin = (net_profit / total_revenue * 100.0) if total_revenue > 0 else 0.0

    # --- Summary (aligned) ---
    st.markdown("---")
    st.subheader("Summary")

    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1: st.metric("Total Cost (€)", f"{total_cost:.2f}")
    with r1c2: st.metric("Unit Cost (€ / pc)", f"{unit_total_cost:.3f}")
    with r1c3: st.metric("Total Revenue (€)", f"{total_revenue:.2f}")

    g_col, n_col = st.columns(2)
    with g_col:
        st.metric("Gross Profit (€)", f"{gross_profit:.2f}")
        st.metric(
            "Gross Margin (%)",
            f"{gross_margin:.2f}",
            delta=f"{gross_margin:.2f}%",
            delta_color="normal",  # + yeşil / - kırmızı
        )
    with n_col:
        st.metric("Net Profit (€)", f"{net_profit:.2f}")
        st.metric(
            "Net Margin (%)",
            f"{net_margin:.2f}",
            delta=f"{net_margin:.2f}%",
            delta_color="normal",
        )

    # --- Breakdown ---
    with st.expander("Breakdown"):
        st.write({
            "Customer": customer if customer and customer != "-- Select --" else None,
            "Customer warehouse": customer_wh if customer_wh and customer_wh != "-- Select --" else None,

            "Unit VVP operational cost (€ / pc)": round(unit_operational_cost, 2),
            "Unit purchase cost (€ / pc)": round(purchase_price_per_piece, 3),
            "Delivery transport (TOTAL €)": round(delivery_transport_total, 2),
            "Delivery transport (€ / pc)": round(delivery_transport_per_piece, 4),

            "Unit TOTAL cost (€ / pc) [VVP + Purchase + Delivery]": round(unit_total_cost, 3),
            "Sales price (€ / pc)": round(sales_price_per_piece, 3),

            "Quantity (pcs)": pieces,

            "Gross cost (€) [Purchase × qty]": round(gross_cost, 2),
            "Gross profit (€) [Revenue − Purchase]": round(gross_profit, 2),
            "Gross margin (%)": round(gross_margin, 2),

            "Total cost (€) [Unit total × qty]": round(total_cost, 2),
            "Total revenue (€)": round(total_revenue, 2),
            "Net profit (€) [Revenue − All costs]": round(net_profit, 2),
            "Net margin (%)": round(net_margin, 2),
        })

    # Kaynak bilgisi
    st.caption(f"Data source: `{os.path.abspath(JSON_PATH)}`")
