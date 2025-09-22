import os
import math
import pandas as pd
import streamlit as st

EXCEL_PATH = "data/customers.xlsx"  # <-- CHANGE THIS

# ---------------------------
# Excel helpers
# ---------------------------
@st.cache_data(show_spinner=False, ttl=300)
def _load_excel_with_mtime(path: str, mtime: float) -> pd.DataFrame:
    """Cached by file mtime; cache busts when file changes."""
    return pd.read_excel(path, engine="openpyxl")

def _safe_read_excel(path: str) -> pd.DataFrame | None:
    if not os.path.exists(path):
        st.error(f"Customer Excel not found: {path}")
        return None
    try:
        mtime = os.path.getmtime(path)
        return _load_excel_with_mtime(path, mtime)
    except Exception as e:
        st.error(f"Customer Excel could not be read.\n\nError: {e}")
        return None

def _get_customers(df: pd.DataFrame) -> list[str]:
    # First column = CustomerName
    col0 = df.iloc[:, 0].astype(str).str.strip()
    custs = [c for c in col0.unique().tolist() if c and c.lower() != "nan"]
    custs.sort()
    return custs

def _get_addresses_for(df: pd.DataFrame, customer: str) -> list[str]:
    # Columns 2..N = addresses
    col0 = df.iloc[:, 0].astype(str).str.strip()
    mask = col0.str.casefold() == customer.strip().casefold()
    if not mask.any():
        return []
    row = df.loc[mask].iloc[0, 1:]
    raw = row.tolist()
    # Clean non-empty unique addresses
    out, seen = [], set()
    for x in raw:
        if pd.isna(x): continue
        s = str(x).strip()
        if not s: continue
        if s not in seen:
            out.append(s); seen.add(s)
    return out

# ---------------------------
# Final calculator
# ---------------------------
def final_calculator(pieces: int, vvp_cost_per_piece_rounded: float):
    """
    Final step:
      - Reads customers & addresses from EXCEL_PATH (fixed).
      - Asks purchase/sales price per piece.
      - Asks Delivery Transportation Cost (TOTAL €).
      - Computes delivery transport per piece and adds it into unit total cost.
      - Shows 4-metric summary, plus stacked Gross/Net blocks (color-coded margins).
    """
    st.subheader("Final Calculator")

    # --- Load fixed Excel (Customer / Address) ---
    df = _safe_read_excel(EXCEL_PATH)
    if df is None:
        st.stop()

    customers = _get_customers(df)
    customer = st.selectbox("Customer", ["-- Select --"] + customers, index=0) if customers else None

    customer_wh = None
    if customer and customer != "-- Select --":
        addrs = _get_addresses_for(df, customer)
        if addrs:
            customer_wh = st.selectbox("Customer Warehouse", ["-- Select --"] + addrs, index=0)
        else:
            st.warning("No warehouse address found for the selected customer.")

    # --- Inputs: prices + delivery transport total ---
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

    # --- Derived: delivery transport per piece ---
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
        + delivery_transport_per_piece  # delivery €/pc included
    )

    # Totals
    total_cost    = unit_total_cost * pieces
    total_revenue = sales_price_per_piece * pieces

    # GROSS (ALL costs included: vvp + purchase + delivery)
    gross_profit = total_revenue - total_cost
    gross_margin = (gross_profit / total_revenue * 100.0) if total_revenue > 0 else 0.0

    # NET (purchase-only deducted; ops & delivery excluded)
    net_cost   = purchase_price_per_piece * pieces
    net_profit = total_revenue - (total_cost + delivery_transport_total)
    net_margin = (net_profit / total_revenue * 100.0) if total_revenue > 0 else 0.0

    # --- Summary (aligned, margins as metrics with color via delta) ---
    st.markdown("---")
    st.subheader("Summary")

    # Row 1: totals
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Cost (€)", f"{total_cost:.2f}")
    with c2:
        st.metric("Unit Cost (€ / pc)", f"{unit_total_cost:.3f}")
    with c3:
        st.metric("Total Revenue (€)", f"{total_revenue:.2f}")

    # Row 2: left = Gross (stacked), right = Net (stacked)
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


    # --- Breakdown (full audit trail) ---
    with st.expander("Breakdown"):
        st.write({
            # Selection
            "Customer": customer if customer and customer != "-- Select --" else None,
            "Customer warehouse": customer_wh if customer_wh and customer_wh != "-- Select --" else None,

            # Unit-level inputs
            "Unit VVP operational cost (€ / pc)": round(unit_operational_cost, 2),
            "Unit purchase cost (€ / pc)": round(purchase_price_per_piece, 3),
            "Delivery transport (TOTAL €)": round(delivery_transport_total, 2),
            "Delivery transport (€ / pc)": round(delivery_transport_per_piece, 4),

            # Unit-level total
            "Unit TOTAL cost (€ / pc) [VVP + Purchase + Delivery]": round(unit_total_cost, 3),

            # Sales input
            "Sales price (€ / pc)": round(sales_price_per_piece, 3),

            # Totals & profits
            "Quantity (pcs)": pieces,

            # Gross block
            "Gross profit (€) [Revenue − All costs]": round(gross_profit, 2),
            "Gross margin (%)": round(gross_margin, 2),

            # Net block
            "Net profit (€) [Revenue − Purchase only]": round(net_profit, 2),
            "Net margin (%)": round(net_margin, 2),
    })


    st.caption(f"Data source: {os.path.abspath(EXCEL_PATH)}")
