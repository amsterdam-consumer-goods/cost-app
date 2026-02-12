"""
Final Calculator UI Component
==============================

Customer selection, France auto-delivery detection, and P&L calculation interface.

This module provides:
- Customer and address selection
- Automatic France delivery cost calculation (SVZ warehouse only)
- P&L calculation and display
- Breakdown export for reports

France Auto-Delivery:
- Detects French addresses by postal code
- Only active for SVZ warehouse
- Calculates cost based on department + pallet count
- Reads from data/fr_delivery_rates.json

Related Files:
- warehouses/calculators.py: ProfitCalculator, FranceDeliveryCalculator
- warehouses/customers/: Customer data management
- ui/warehouse_detector.py: Warehouse type detection
- data/catalog.json: Customer database
- data/fr_delivery_rates.json: France delivery rates
"""

from __future__ import annotations
from typing import Dict, Tuple, Optional
import streamlit as st

from warehouses.calculators import ProfitCalculator, FranceDeliveryCalculator
from warehouses.customers import (
    load_customers,
    get_customer_names,
    get_customer_addresses,
    is_france_address,
    extract_postal_code,
)
from .warehouse_detector import WarehouseDetector


# ============================================================================
# MAIN CALCULATOR
# ============================================================================

def final_calculator(pieces: int, vvp_cost_per_piece_rounded: float) -> Dict:
    """
    Render final calculator UI and compute P&L results.
    
    Workflow:
    1. Load customers from catalog
    2. Customer + address selection
    3. France auto-delivery detection (if applicable)
    4. Price inputs (purchase, sales, delivery)
    5. P&L calculation
    6. Display summary and breakdown
    
    Args:
        pieces: Number of pieces in order
        vvp_cost_per_piece_rounded: VVP cost per piece from warehouse calculator
        
    Returns:
        Dictionary with P&L metrics and customer info:
        - unit_vvp_cpp: VVP cost per piece
        - unit_purchase_cpp: Purchase price per piece
        - unit_delivery_cpp: Delivery cost per piece
        - unit_gross_cpp: Total unit cost (VVP + purchase)
        - sales_price_cpp: Sales price per piece
        - total_cost: Total cost
        - total_revenue: Total revenue
        - gross_profit: Revenue - cost
        - gross_margin_pct: Gross margin %
        - net_profit: Revenue - cost - delivery
        - net_margin_pct: Net margin %
        - customer: Selected customer name
        - customer_warehouse: Selected address
        - data_source: Catalog path
    """
    st.subheader("Final Calculator")
    
    # Load customers (always fresh, no cache)
    customers_data, catalog_path = load_customers()
    customer_names = get_customer_names(customers_data)
    
    # Display data source
    source_display = catalog_path or "No customers"
    st.caption(f"🔍 Loaded {len(customer_names)} customers from: {source_display}")
    
    # Customer selection
    customer = _render_customer_selection(customer_names)
    
    # Address selection
    customer_address = _render_address_selection(customers_data, customer)
    
    # France auto-delivery detection
    france_auto_cost = _handle_france_auto_delivery(customer_address)
    
    # Price inputs
    purchase_price, sales_price, delivery_cost = _render_input_fields(france_auto_cost)
    
    # Calculate P&L
    results = ProfitCalculator.calculate(
        pieces=pieces,
        vvp_cost_per_piece=vvp_cost_per_piece_rounded,
        purchase_price_per_piece=purchase_price,
        sales_price_per_piece=sales_price,
        delivery_transport_total=delivery_cost,
    )
    
    # Display results
    _render_summary(results)
    _render_breakdown(customer, customer_address, results)
    
    # Add metadata for export
    results["customer"] = customer
    results["customer_warehouse"] = customer_address
    results["data_source"] = source_display
    
    return results


# ============================================================================
# CUSTOMER & ADDRESS SELECTION
# ============================================================================

def _render_customer_selection(customer_names: list) -> Optional[str]:
    """
    Render customer selection dropdown.
    
    Args:
        customer_names: List of customer names
        
    Returns:
        Selected customer name or None
    """
    if not customer_names:
        st.info("ℹ️ No customers found. Add customers in the Admin Panel.")
        return None
    
    customer = st.selectbox(
        "Customer",
        ["-- Select --"] + customer_names,
        index=0,
        key="final_calc_selected_customer"
    )
    
    if customer == "-- Select --":
        return None
    
    return customer


def _render_address_selection(
    customers_data: Dict,
    customer: Optional[str]
) -> Optional[str]:
    """
    Render address selection dropdown for selected customer.
    
    Args:
        customers_data: Customer database
        customer: Selected customer name
        
    Returns:
        Selected address or None
    """
    if not customer:
        return None
    
    addresses = get_customer_addresses(customers_data, customer)
    
    if not addresses:
        st.warning("No warehouse address found for the selected customer.")
        return None
    
    customer_address = st.selectbox(
        "Customer Warehouse",
        ["-- Select --"] + addresses,
        index=0,
        key="final_calc_selected_warehouse"
    )
    
    if customer_address == "-- Select --":
        return None
    
    return customer_address


# ============================================================================
# FRANCE AUTO-DELIVERY
# ============================================================================

def _handle_france_auto_delivery(customer_address: Optional[str]) -> float:
    """
    Handle automatic France delivery cost calculation.
    
    Conditions:
    1. Customer address must be in France (detected by postal code)
    2. Current warehouse must be SVZ (only SVZ supports auto-delivery)
    3. Pallet count must be > 0 (from session state)
    4. Postal code must be valid 5-digit format
    
    Process:
    1. Clear any previous auto-delivery cost from session
    2. Check all conditions
    3. Lookup cost in fr_delivery_rates.json
    4. Store in session state for input field default
    5. Display info caption
    
    Args:
        customer_address: Selected customer address
        
    Returns:
        Auto-calculated delivery cost (0 if not applicable)
    """
    # Clear previous auto-delivery cost
    st.session_state.pop("__fr_auto_delivery_total", None)
    
    if not customer_address:
        return 0.0
    
    # Check if address is in France
    if not is_france_address(customer_address):
        return 0.0
    
    # Check if current warehouse allows France auto-delivery (SVZ only)
    if not WarehouseDetector.is_svz_warehouse():
        st.info("🇫🇷 French address detected, but auto-delivery is only enabled for SVZ.")
        return 0.0
    
    # Extract postal code
    postal_code = extract_postal_code(customer_address)
    if not postal_code:
        st.warning("France address detected but no 5-digit postal code found.")
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
        # Store in session for input default
        st.session_state["__fr_auto_delivery_total"] = float(auto_cost)
        
        # Get effective pallets (capped at 33 for full truck)
        effective_pallets = calculator.get_effective_pallets(pallets)
        
        # Display info
        full_truck_note = " (full truck)" if effective_pallets == 33 else ""
        st.caption(
            f"🇫🇷 France delivery auto-cost: dept **{postal_code[:2]}**, "
            f"pallets **{effective_pallets}{full_truck_note}** "
            f"→ **€{auto_cost:.2f}** (from FR rates)"
        )
        
        return auto_cost
    else:
        st.warning("France auto-cost lookup failed. Check data/fr_delivery_rates.json")
        return 0.0


# ============================================================================
# INPUT FIELDS
# ============================================================================

def _render_input_fields(default_delivery: float) -> Tuple[float, float, float]:
    """
    Render price input fields.
    
    Args:
        default_delivery: Default delivery cost (from France auto-calc or 0)
        
    Returns:
        Tuple of (purchase_price, sales_price, delivery_cost)
    """
    c1, c2, c3 = st.columns(3)
    
    with c1:
        purchase_price = st.number_input(
            "Purchase Price per Piece (€)",
            min_value=0.0,
            step=0.001,
            format="%.3f",
            help="Cost to acquire each piece"
        )
    
    with c2:
        sales_price = st.number_input(
            "Sales Price per Piece (€)",
            min_value=0.0,
            step=0.001,
            format="%.3f",
            help="Selling price per piece"
        )
    
    with c3:
        delivery_cost = st.number_input(
            "Delivery Transportation Cost (TOTAL €)",
            min_value=0.0,
            step=1.0,
            value=default_delivery,
            format="%.2f",
            help="Total delivery transport cost (not per piece)"
        )
    
    return purchase_price, sales_price, delivery_cost


# ============================================================================
# RESULTS DISPLAY
# ============================================================================

def _render_summary(results: Dict) -> None:
    """
    Render summary metrics display.
    
    Shows:
    - Top caption: Unit costs and piece count
    - First row: Total cost, unit cost, revenue
    - Second row: Gross/net profit and margins
    
    Args:
        results: P&L calculation results from ProfitCalculator
    """
    # Cost breakdown caption
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


def _render_breakdown(
    customer: Optional[str],
    address: Optional[str],
    results: Dict
) -> None:
    """
    Render detailed calculation breakdown in expander.
    
    Shows complete breakdown of:
    - Customer info
    - All cost components
    - Revenue and profit calculations
    - Margin percentages
    
    Args:
        customer: Selected customer name
        address: Selected customer address
        results: P&L calculation results
    """
    with st.expander("📊 Detailed Breakdown"):
        st.write({
            "Customer": customer or "Not selected",
            "Customer warehouse": address or "Not selected",
            "---": "---",
            "Unit VVP cost (€ / pc)": f"{results['unit_vvp_cpp']:.4f}",
            "Unit purchase cost (€ / pc)": f"{results['unit_purchase_cpp']:.4f}",
            "Delivery transport (TOTAL €)": f"{results['delivery_transport_total']:.2f}",
            "Delivery transport (€ / pc)": f"{results['unit_delivery_cpp']:.4f}",
            "Unit gross cost (€ / pc) [VVP + Purchase]": f"{results['unit_gross_cpp']:.4f}",
            "---2": "---",
            "Sales price (€ / pc)": f"{results['sales_price_cpp']:.4f}",
            "Quantity (pcs)": results['pieces'],
            "---3": "---",
            "Total cost (€) [Unit gross × qty]": f"{results['total_gross_cost']:.2f}",
            "Total revenue (€)": f"{results['total_revenue']:.2f}",
            "---4": "---",
            "Gross profit (€) [Revenue − Total cost]": f"{results['gross_profit']:.2f}",
            "Gross margin (%)": f"{results['gross_margin_pct']:.2f}",
            "Net profit (€) [Revenue − Total cost − Delivery]": f"{results['net_profit']:.2f}",
            "Net margin (%)": f"{results['net_margin_pct']:.2f}",
        })