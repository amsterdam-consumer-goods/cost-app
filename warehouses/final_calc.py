"""
Final calculator - Customer selection, France auto-delivery, and P&L.
Refactored to use modular components.
"""

from __future__ import annotations
import streamlit as st

from warehouses.calculators import ProfitCalculator, FranceDeliveryCalculator
from warehouses.customers import (
    load_customers,
    get_customer_names,
    get_customer_addresses,
    is_france_address,
    extract_postal_code,
)
from warehouses.warehouse_detector import WarehouseDetector


def final_calculator(pieces: int, vvp_cost_per_piece_rounded: float):
    """
    Render final calculator UI and return P&L results.
    
    Args:
        pieces: Number of pieces
        vvp_cost_per_piece_rounded: Rounded VVP cost per piece
        
    Returns:
        Dict with P&L metrics and customer info
    """
    st.subheader("Final Calculator")
    
    # Load customers (always fresh, no cache)
    customers_data, catalog_path = load_customers()
    customer_names = get_customer_names(customers_data)
    
    # Display source info
    source_display = catalog_path or "No customers"
    st.caption(f"🔍 Loaded {len(customer_names)} customers from: {source_display}")
    
    # Customer selection
    customer = None
    if customer_names:
        customer = st.selectbox(
            "Customer",
            ["-- Select --"] + customer_names,
            index=0,
            key="final_calc_selected_customer"
        )
        if customer == "-- Select --":
            customer = None
    else:
        st.info("ℹ️ No customers found. Add customers in the Admin Panel.")
    
    # Address selection
    customer_address = None
    if customer:
        addresses = get_customer_addresses(customers_data, customer)
        if addresses:
            customer_address = st.selectbox(
                "Customer Warehouse",
                ["-- Select --"] + addresses,
                index=0,
                key="final_calc_selected_warehouse"
            )
            if customer_address == "-- Select --":
                customer_address = None
        else:
            st.warning("No warehouse address found for the selected customer.")
    
    # France auto-delivery detection
    france_auto_cost = _handle_france_auto_delivery(customer_address)
    
    # Input fields
    purchase_price, sales_price, delivery_cost = _render_input_fields(france_auto_cost)
    
    # Calculate P&L
    results = ProfitCalculator.calculate(
        pieces=pieces,
        vvp_cost_per_piece=vvp_cost_per_piece_rounded,
        purchase_price_per_piece=purchase_price,
        sales_price_per_piece=sales_price,
        delivery_transport_total=delivery_cost,
    )
    
    # Display summary
    _render_summary(results)
    
    # Display breakdown
    _render_breakdown(customer, customer_address, results)
    
    # Add customer info to results for export
    results["customer"] = customer
    results["customer_warehouse"] = customer_address
    results["data_source"] = source_display
    
    return results


def _handle_france_auto_delivery(customer_address: str | None) -> float:
    """
    Handle France auto-delivery cost calculation.
    
    Returns:
        Auto-calculated delivery cost (0 if not applicable)
    """
    # Clear any previous auto-delivery cost
    st.session_state.pop("__fr_auto_delivery_total", None)
    
    if not customer_address:
        return 0.0
    
    # Check if address is in France
    if not is_france_address(customer_address):
        return 0.0
    
    # Check if current warehouse allows France auto-delivery (SVZ only)
    if not WarehouseDetector.is_svz_warehouse():
        st.info("FR address detected, but auto-delivery is only enabled for SVZ.")
        return 0.0
    
    # Extract postal code
    postal_code = extract_postal_code(customer_address)
    if not postal_code:
        st.warning("France address detected but no 5-digit postal code was found.")
        return 0.0
    
    # Get pallet count from session
    pallets = int(st.session_state.get("pallets", 0))
    if pallets <= 0:
        st.info("Enter pallet count at the beginning to enable France auto-cost.")
        return 0.0
    
    # Calculate auto-delivery cost
    calculator = FranceDeliveryCalculator()
    auto_cost = calculator.lookup_cost(postal_code, pallets)
    
    if auto_cost > 0:
        st.session_state["__fr_auto_delivery_total"] = float(auto_cost)
        effective_pallets = calculator.get_effective_pallets(pallets)
        
        st.caption(
            f"🇫🇷 France delivery auto-cost: dept **{postal_code[:2]}**, "
            f"pallets **{effective_pallets}{' (full truck)' if effective_pallets == 33 else ''}** "
            f"→ **€{auto_cost:.2f}** (from FR rates)"
        )
        
        return auto_cost
    else:
        st.warning("France auto-cost lookup failed (check fr_delivery_rates.json).")
        return 0.0


def _render_input_fields(default_delivery: float) -> tuple[float, float, float]:
    """
    Render price input fields.
    
    Returns:
        (purchase_price, sales_price, delivery_cost)
    """
    c1, c2, c3 = st.columns(3)
    
    with c1:
        purchase_price = st.number_input(
            "Purchase Price per Piece (€)",
            min_value=0.0,
            step=0.001,
            format="%.3f"
        )
    
    with c2:
        sales_price = st.number_input(
            "Sales Price per Piece (€)",
            min_value=0.0,
            step=0.001,
            format="%.3f"
        )
    
    with c3:
        delivery_cost = st.number_input(
            "Delivery Transportation Cost (TOTAL €)",
            min_value=0.0,
            step=1.0,
            value=default_delivery,
            format="%.2f",
            help="Total delivery transport cost for this order (not per piece).",
        )
    
    return purchase_price, sales_price, delivery_cost


def _render_summary(results: dict) -> None:
    """Render summary metrics."""
    st.caption(
        f"Rounded VVP Cost / pc: **€{results['unit_vvp_cpp']:.2f}**  |  "
        f"Purchase / pc: **€{results['unit_purchase_cpp']:.3f}**  |  "
        f"Delivery Transport / pc: **€{results['unit_delivery_cpp']:.4f}**  |  "
        f"Pieces: **{results['pieces']}**"
    )
    
    st.markdown("---")
    st.subheader("Summary")
    
    # Top row: costs and revenue
    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        st.metric("Total Cost (€)", f"{results['total_cost']:.2f}")
    with r1c2:
        st.metric("Unit Cost (€ / pc)", f"{results['unit_gross_cpp']:.3f}")
    with r1c3:
        st.metric("Total Revenue (€)", f"{results['total_revenue']:.2f}")
    
    # Bottom row: profits and margins
    g_col, n_col = st.columns(2)
    with g_col:
        st.metric("Gross Profit (€)", f"{results['gross_profit']:.2f}")
        st.metric(
            "Gross Margin (%)",
            f"{results['gross_margin_pct']:.2f}",
            delta=f"{results['gross_margin_pct']:.2f}%",
            delta_color="normal"
        )
    with n_col:
        st.metric("Net Profit (€)", f"{results['net_profit']:.2f}")
        st.metric(
            "Net Margin (%)",
            f"{results['net_margin_pct']:.2f}",
            delta=f"{results['net_margin_pct']:.2f}%",
            delta_color="normal"
        )


def _render_breakdown(customer: str | None, address: str | None, results: dict) -> None:
    """Render detailed breakdown."""
    with st.expander("Breakdown"):
        st.write({
            "Customer": customer,
            "Customer warehouse": address,
            "Unit VVP cost (€ / pc)": results['unit_vvp_cpp'],
            "Unit purchase cost (€ / pc)": results['unit_purchase_cpp'],
            "Delivery transport (TOTAL €)": results['delivery_transport_total'],
            "Delivery transport (€ / pc)": results['unit_delivery_cpp'],
            "Unit gross cost (€ / pc) [VVP + Purchase]": results['unit_gross_cpp'],
            "Sales price (€ / pc)": results['sales_price_cpp'],
            "Quantity (pcs)": results['pieces'],
            "Total cost (€) [Unit gross × qty]": results['total_gross_cost'],
            "Total revenue (€)": results['total_revenue'],
            "Gross profit (€) [Revenue − Total cost]": results['gross_profit'],
            "Gross margin (%)": results['gross_margin_pct'],
            "Net profit (€) [Revenue − Total cost − DeliveryTOTAL]": results['net_profit'],
            "Net margin (%)": results['net_margin_pct'],
        })