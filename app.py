"""
VVP Calculator Main Application
================================

Streamlit application entry point for warehouse cost calculation.

This application provides:
- User authentication (password-protected access)
- Admin panel access (separate admin login)
- Warehouse cost calculator (VVP calculation)
- P&L calculator (Final calculator)
- Export functionality

Authentication:
- User password: Main calculator access
- Admin password: Admin panel access (sidebar)
- Passwords from .streamlit/secrets.toml or environment variables

Workflow:
1. User login (if password configured)
2. Select warehouse
3. Enter order details (pieces, pallets, weeks, transport)
4. Calculate VVP costs (warehousing, labeling, transfer)
5. Calculate P&L (purchase price, sales price, delivery)
6. Export results

Admin Panel:
- Accessible via sidebar login
- Manage warehouses (add, update, delete)
- Manage customers (add, edit, delete)
- Configure features (labeling, transfer, second leg)

Related Files:
- ui/generic.py: Main calculator orchestration
- ui/final_calc.py: P&L calculator
- ui/warehouse_inputs.py: Labeling and transfer UI
- admin/app.py: Standalone admin panel
- services/config_manager.py: Catalog management
- data/catalog.json: Warehouse and customer database
"""

from __future__ import annotations
import sys
import os
from pathlib import Path

# ============================================================================
# PATH SETUP
# ============================================================================

# Add project root to Python path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Force reload of local modules (prevents Cloud caching issues)
import importlib
for module_name in [
    'services',
    'services.catalog',
    'services.catalog_adapter',
    'services.config_manager',
    'ui',
    'ui.generic',
    'ui.final_calc',
    'ui.second_leg',
    'ui.warehouse_inputs',
    'ui.warehouse_detector',
]:
    if module_name in sys.modules:
        del sys.modules[module_name]

import streamlit as st

# ============================================================================
# MODE SWITCHING CACHE MANAGEMENT
# ============================================================================

# Clear cache when switching between admin and user modes
if "last_mode" not in st.session_state:
    st.session_state.last_mode = None

current_mode = "admin" if st.session_state.get("is_admin") else "user"

if st.session_state.last_mode != current_mode:
    st.session_state.last_mode = current_mode
    st.cache_data.clear()

# ============================================================================
# IMPORTS
# ============================================================================

from services.catalog import load_catalog, normalize_catalog
from warehouses.ui.generic import compute_generic

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="VVP Calculator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - disable rounded corners on images
st.markdown(
    """
    <style>
    .stImage img {
        border-radius: 0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================================
# PASSWORD CONFIGURATION
# ============================================================================

# Load passwords from secrets or environment variables
try:
    APP_PASSWORD = st.secrets.get("APP_PASSWORD", os.environ.get("APP_PASSWORD"))
    ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", os.environ.get("ADMIN_PASSWORD"))
except Exception:
    APP_PASSWORD = os.environ.get("APP_PASSWORD")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

# ============================================================================
# ADMIN LOGIN (SIDEBAR)
# ============================================================================

st.sidebar.markdown("### Admin Login")

# Initialize admin state
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# Admin login/logout
if not st.session_state.is_admin:
    # Show login form
    admin_pw = st.sidebar.text_input(
        "Password",
        type="password",
        placeholder="••••••••",
        key="admin_pw"
    )
    
    if st.sidebar.button("Login", use_container_width=True, key="admin_login_btn"):
        if ADMIN_PASSWORD and admin_pw == str(ADMIN_PASSWORD):
            st.session_state.is_admin = True
            st.sidebar.success("✅ Admin access granted")
            st.cache_data.clear()
            st.rerun()
        else:
            st.sidebar.error("❌ Wrong password")
else:
    # Show logout button
    st.sidebar.success("🟢 Logged in as Admin")
    
    if st.sidebar.button("Logout Admin", use_container_width=True, key="admin_logout_btn"):
        st.session_state.is_admin = False
        st.cache_data.clear()
        st.rerun()

# ============================================================================
# ADMIN PANEL ROUTING
# ============================================================================

if st.session_state.is_admin:
    # Render admin panel
    st.image("assets/logo2.png", width=190)
    st.title("🛠️ Admin Panel")
    
    # Admin page selection (radio menu)
    choice = st.sidebar.radio(
        "Admin Pages",
        options=["Update warehouse", "Add warehouse", "Add customer"],
        index=0,
        key="admin_page_choice",
    )
    
    # Route to admin views
    try:
        from admin.views import admin_router
        admin_router(choice)
    except Exception as e:
        st.error("❌ Admin views are not available.")
        st.exception(e)
    
    # Stop execution (don't render calculator in admin mode)
    st.stop()

# ============================================================================
# USER AUTHENTICATION
# ============================================================================

def check_password() -> bool:
    """
    Check user password.
    
    If no password is configured, allows access directly.
    Otherwise, shows login form.
    
    Returns:
        True if authenticated, False otherwise
    """
    # No password configured - allow access
    if not APP_PASSWORD:
        return True
    
    # Already authenticated
    if st.session_state.get("auth_ok"):
        return True
    
    # Show login form
    st.image("assets/logo2.png", width=190)
    st.title("🔐 Enter Password")
    
    pw = st.text_input(
        "Password",
        type="password",
        placeholder="Enter password…",
        key="user_pw_box"
    )
    
    if st.button("Sign in", key="user_signin_btn"):
        st.session_state.auth_ok = pw == str(APP_PASSWORD)
        
        if not st.session_state.auth_ok:
            st.error("Incorrect password.")
        else:
            st.rerun()
    
    return False


# Check authentication
if not check_password():
    st.stop()

# ============================================================================
# CALCULATOR UI (USER MODE)
# ============================================================================

# Header
st.image("assets/logo2.png", width=190)

hdr_col, logout_col = st.columns([6, 1])

with hdr_col:
    st.title("📦 VVP and Final Calculator")

with logout_col:
    if st.button("Logout User"):
        st.session_state.pop("auth_ok", None)
        st.rerun()

st.markdown("---")

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

# Initialize step tracker
if "step" not in st.session_state:
    st.session_state.step = "inputs"

# Initialize form values
for key, default in {
    "warehouse": "-- Select a warehouse --",
    "buying_transport_cost": 0.0,
    "pieces": 1,
    "pallets": 1,
    "weeks": 4,
    "pallet_unit_cost": 0.0,
}.items():
    st.session_state.setdefault(key, default)

# ============================================================================
# WAREHOUSE DISPATCH
# ============================================================================

def _dispatch(
    warehouse_label: str,
    pieces: int,
    pallets: int,
    weeks: int,
    buying_transport_cost: float,
    pallet_unit_cost: float,
) -> None:
    """
    Dispatch to warehouse calculator.
    
    Loads catalog, finds selected warehouse, and runs calculation.
    
    Args:
        warehouse_label: Warehouse display label
        pieces: Number of pieces
        pallets: Number of pallets
        weeks: Storage duration in weeks
        buying_transport_cost: Inbound transport cost
        pallet_unit_cost: Cost per pallet unit
    """
    # Load catalog
    catalog = normalize_catalog(load_catalog())
    warehouses = catalog.get("warehouses", []) or []
    
    # Build label -> warehouse map
    label_map = {}
    for w in warehouses:
        country = (w.get("country") or "").strip()
        name = (w.get("name") or w.get("id") or "Warehouse").strip()
        label = f"{country} / {name}" if country else name
        label_map[label] = w
    
    # Find selected warehouse
    selected_wh = label_map.get(warehouse_label)
    
    # Fuzzy match fallback (if exact match fails)
    if not selected_wh:
        search_term = warehouse_label.split("/", 1)[-1].strip().lower()
        
        for label, wh in label_map.items():
            name = str(wh.get("name", "")).strip().lower()
            label_rhs = label.split("/", 1)[-1].strip().lower()
            
            if (
                name == search_term
                or label_rhs == search_term
                or name.startswith(search_term)
                or search_term.startswith(name)
                or search_term in name
                or name in search_term
            ):
                selected_wh = wh
                break
    
    # Error if warehouse not found
    if not selected_wh:
        st.error(
            "⚠️ Selected warehouse not found in catalog.\n\n"
            "• Check if it's defined as 'Country / Name' in Admin Panel\n"
            "• Or select a valid warehouse from the dropdown"
        )
        return
    
    # Build ID map for second leg
    id_map = {w.get("id"): w for w in warehouses if w.get("id")}
    
    # Run calculation
    compute_generic(
        wh=selected_wh,
        all_whs_map=id_map,
        pieces=pieces,
        pallets=pallets,
        weeks=weeks,
        buying_transport_cost=buying_transport_cost,
        pallet_unit_cost=pallet_unit_cost,
    )


# ============================================================================
# REFRESH BUTTON
# ============================================================================

# Allow manual cache refresh (useful for customer data updates)
if st.button("🔄 Refresh data", help="Reload warehouse and customer data"):
    st.cache_data.clear()
    st.rerun()

# ============================================================================
# STEP 1: INPUT FORM
# ============================================================================

if st.session_state.step == "inputs":
    # Load warehouses
    catalog = normalize_catalog(load_catalog())
    warehouses = catalog.get("warehouses", []) or []
    
    # Build warehouse options
    warehouse_options = []
    for w in warehouses:
        country = (w.get("country") or "").strip()
        name = (w.get("name") or w.get("id") or "Warehouse").strip()
        label = f"{country} / {name}" if country else name
        warehouse_options.append(label)
    
    # Warehouse selection
    warehouse = st.selectbox(
        "Select Warehouse",
        ["-- Select a warehouse --"] + warehouse_options,
        index=(["-- Select a warehouse --"] + warehouse_options).index(st.session_state.warehouse)
        if st.session_state.warehouse in ["-- Select a warehouse --"] + warehouse_options
        else 0,
    )
    
    # Order inputs form
    st.subheader("Order Inputs")
    
    with st.form("order_form", clear_on_submit=False):
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            st.markdown("Incoming Transport Cost (€ total)")
            buying_transport_cost = st.number_input(
                "Incoming Transport Cost (€ total)",
                min_value=0.0,
                step=1.0,
                value=float(st.session_state.buying_transport_cost),
                format="%.2f",
                label_visibility="collapsed",
            )
        
        with c2:
            st.markdown("Pieces (#) *")
            pieces = st.number_input(
                "Pieces (#)",
                min_value=1,
                step=1,
                value=int(st.session_state.pieces),
                format="%d",
                label_visibility="collapsed",
            )
        
        with c3:
            st.markdown("Pallets (#) *")
            pallets = st.number_input(
                "Pallets (#)",
                min_value=1,
                step=1,
                value=int(st.session_state.pallets),
                format="%d",
                label_visibility="collapsed",
            )
            
            pallet_unit_cost = st.number_input(
                "Pallet Cost (€ per pallet) — optional",
                min_value=0.0,
                step=0.01,
                value=float(st.session_state.pallet_unit_cost),
                format="%.2f",
            )
        
        with c4:
            st.markdown("Weeks in Storage (min 4) *")
            weeks = st.number_input(
                "Weeks in Storage",
                min_value=4,
                step=1,
                value=int(max(4, st.session_state.weeks)),
                format="%d",
                label_visibility="collapsed",
            )
        
        next_clicked = st.form_submit_button("Next →", type="primary")
    
    # Form validation
    if next_clicked:
        if warehouse == "-- Select a warehouse --":
            st.warning("⚠️ Please select a warehouse to continue.")
            st.stop()
        
        if pallets > 66:
            st.error("❌ Pallets cannot exceed 66.")
            st.stop()
        
        if weeks < 4:
            st.error("❌ You need to order at least 4 weeks of storage.")
            st.stop()
        
        if any(v is None or v <= 0 for v in [pieces, pallets, weeks]):
            st.warning("⚠️ Fields marked with * are required and must be > 0.")
            st.stop()
        
        # Save to session and proceed
        st.session_state.warehouse = warehouse
        st.session_state.buying_transport_cost = float(buying_transport_cost)
        st.session_state.pieces = int(pieces)
        st.session_state.pallets = int(pallets)
        st.session_state.weeks = int(weeks)
        st.session_state.pallet_unit_cost = float(pallet_unit_cost)
        st.session_state.step = "details"
        st.rerun()

# ============================================================================
# STEP 2: DETAILS & CALCULATION
# ============================================================================

else:
    # Load warehouses for display
    catalog = normalize_catalog(load_catalog())
    warehouses = catalog.get("warehouses", []) or []
    
    warehouse_options = []
    for w in warehouses:
        country = (w.get("country") or "").strip()
        name = (w.get("name") or w.get("id") or "Warehouse").strip()
        label = f"{country} / {name}" if country else name
        warehouse_options.append(label)
    
    # Show locked warehouse selection
    st.selectbox(
        "Warehouse (locked, change via Back)",
        ["-- Select a warehouse --"] + warehouse_options,
        index=(["-- Select a warehouse --"] + warehouse_options).index(st.session_state.warehouse)
        if st.session_state.warehouse in ["-- Select a warehouse --"] + warehouse_options
        else 0,
        disabled=True,
    )
    
    # Back button
    if st.button("← Back", use_container_width=False):
        st.session_state.step = "inputs"
        st.rerun()
    
    # Order summary
    st.markdown("### Order Summary")
    
    s1, s2, s3, s4 = st.columns(4)
    
    with s1:
        st.metric("Incoming Transport Cost (€)", f"{st.session_state.buying_transport_cost:.2f}")
    
    with s2:
        st.metric("Pieces (#)", f"{st.session_state.pieces}")
    
    with s3:
        st.metric("Pallets (#)", f"{st.session_state.pallets}")
        if st.session_state.pallet_unit_cost and st.session_state.pallet_unit_cost > 0:
            st.caption(f"€/pallet: {st.session_state.pallet_unit_cost:.2f}")
    
    with s4:
        st.metric("Weeks in Storage", f"{st.session_state.weeks}")
    
    st.markdown("---")
    
    # Run calculator
    _dispatch(
        st.session_state.warehouse,
        st.session_state.pieces,
        st.session_state.pallets,
        st.session_state.weeks,
        st.session_state.buying_transport_cost,
        st.session_state.pallet_unit_cost,
    )