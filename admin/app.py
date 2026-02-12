"""
Admin Panel Application Entry Point
====================================

This is the main Streamlit application for the Cost Calculator Admin Panel.

PURPOSE:
--------
The admin panel allows authorized users to:
- Create and update warehouse configurations (rates, features, labels)
- Manage customers and their addresses
- Link customers to specific warehouses
- Configure advanced features like transfer costs and labeling options

AUTHENTICATION:
---------------
Uses password-based authentication with two possible sources:
1. .streamlit/secrets.toml → ADMIN_PASSWORD = "your_password"
2. Environment variable → ADMIN_PASSWORD=your_password

If no password is configured, authentication is bypassed (NOT recommended for production).

LAUNCHING:
----------
From project root directory:

    streamlit run admin/app.py --server.port 8502 --server.address 127.0.0.1

Alternative ports:
- Default user app: 8501
- Admin app: 8502 (recommended)

ARCHITECTURE:
-------------
admin/
├── app.py                  ← This file (entry point)
├── views/
│   ├── __init__.py
│   ├── admin_router.py     ← Routes to appropriate page based on user selection
│   ├── helpers.py          ← Shared utilities for warehouse configuration
│   ├── add_warehouse.py    ← Warehouse creation interface
│   └── update_warehouse.py ← Warehouse editing interface
└── pages/
    ├── __init__.py
    └── add_customer.py     ← Customer management interface

DATA FLOW:
----------
1. User selects action via radio buttons (Update/Add warehouse, Add customer)
2. admin_router() routes to appropriate view
3. View loads data from catalog.json via services/config_manager.py
4. View saves changes back to catalog.json
5. Cache is cleared to ensure fresh data

CONFIGURATION FILES:
--------------------
- data/catalog.json         → Warehouse and customer data
- .streamlit/secrets.toml   → Admin password and secrets
- .env                      → Alternative secrets location

SECURITY NOTES:
---------------
- Always use strong passwords in production
- Never commit secrets.toml or .env to version control
- Consider IP whitelisting for production admin panel
- Session state used to maintain authentication across reruns

RELATED FILES:
--------------
- services/config_manager.py → Catalog data persistence
- admin/views/helpers.py     → Warehouse configuration utilities
- requirements.txt           → Dependencies (streamlit, etc.)

TROUBLESHOOTING:
----------------
Import errors:
    - Ensure __init__.py exists in admin/ and admin/views/
    - Clear Python cache: find . -name "__pycache__" -exec rm -rf {} +
    - Check sys.path includes project root

Authentication issues:
    - Verify ADMIN_PASSWORD is set in secrets.toml or environment
    - Check secrets.toml format: ADMIN_PASSWORD = "password123"
    - Restart Streamlit after changing secrets

Module not found:
    - Run from project root, not from admin/ directory
    - Check ROOT_DIR path resolution in this file
"""

import os
import sys

# ============================================================================
# PATH SETUP
# ============================================================================

# Add project root to sys.path so "admin" and "services" imports resolve
# This allows running `streamlit run admin/app.py` from project root
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../cost-app

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import streamlit as st


# ============================================================================
# AUTHENTICATION
# ============================================================================

def check_admin_password() -> bool:
    """
    Verify admin authentication.
    
    Flow:
    1. Check if already authenticated (session_state.admin_auth_ok)
    2. If not, show login form
    3. Compare entered password with secret
    4. Set session flag on success
    
    Password sources (in order of precedence):
    1. st.secrets["ADMIN_PASSWORD"] (from .streamlit/secrets.toml)
    2. os.environ["ADMIN_PASSWORD"] (from environment or .env)
    3. None → bypass authentication (development only)
    
    Returns:
        bool: True if authenticated, False if login form is shown
    """
    # Get password from secrets or environment
    secret_pw = st.secrets.get("ADMIN_PASSWORD", os.environ.get("ADMIN_PASSWORD"))
    
    # No password configured → allow access (not recommended for production)
    if not secret_pw:
        st.warning("⚠️ No admin password configured. Access granted by default.")
        return True
    
    # Already authenticated in this session
    if st.session_state.get("admin_auth_ok"):
        return True
    
    # Show login form
    st.image("assets/logo2.png", width=190)
    st.title("🛠️ Admin Login")
    st.caption("Enter admin password to access the control panel")
    
    pw = st.text_input(
        "Admin Password",
        type="password",
        placeholder="Enter admin password…"
    )
    
    if st.button("Sign in", type="primary"):
        if pw == str(secret_pw):
            st.session_state.admin_auth_ok = True
            st.success("✅ Authentication successful")
            st.rerun()
        else:
            st.error("❌ Incorrect password. Please try again.")
    
    # Authentication required, form shown
    return False


# ============================================================================
# STREAMLIT CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Cost-App Admin",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="collapsed"  # No sidebar needed for admin
)

# Custom CSS to disable rounded corners on images
st.markdown(
    """
    <style>
    /* Disable rounded corners on images */
    .stImage img {
        border-radius: 0 !important;
    }
    
    /* Optional: Improve admin panel aesthetics */
    .stRadio > label {
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================================
# AUTHENTICATION GATE
# ============================================================================

# Check authentication - stop execution if not authenticated
if not check_admin_password():
    st.stop()


# ============================================================================
# ROUTER IMPORT
# ============================================================================

# Import the admin router
# Kept in try/except to provide helpful error messages if imports fail
try:
    from admin.views import admin_router
except Exception as e:
    st.error("❌ Failed to import admin router")
    st.exception(e)
    st.error(
        "**Troubleshooting:**\n\n"
        "1. Ensure these files exist:\n"
        "   - `admin/__init__.py`\n"
        "   - `admin/views/__init__.py`\n"
        "   - `admin/views/admin_router.py`\n\n"
        "2. Clear Python cache:\n"
        "   ```bash\n"
        "   find . -name '__pycache__' -exec rm -rf {} +\n"
        "   ```\n\n"
        "3. Launch Streamlit from the project root:\n"
        "   ```bash\n"
        "   streamlit run admin/app.py\n"
        "   ```"
    )
    st.stop()


# ============================================================================
# MAIN ADMIN UI
# ============================================================================

# Header with logo
st.image("assets/logo2.png", width=190)

# Title and logout button
header_col, logout_col = st.columns([6, 1])

with header_col:
    st.title("🛠️ Admin Panel")
    st.caption("Manage warehouses and customers")

with logout_col:
    if st.button("Log out"):
        st.session_state.pop("admin_auth_ok", None)
        st.success("Logged out")
        st.rerun()

st.markdown("---")

# Action selection
choice = st.radio(
    "Choose an action",
    [
        "Update warehouse",  # Edit existing warehouse configurations
        "Add warehouse",     # Create new warehouse
        "Add customer"       # Manage customers
    ],
    horizontal=True,
    help="Select the admin task you want to perform"
)

# Route to appropriate view
try:
    admin_router(choice)
except Exception as e:
    st.error("❌ An error occurred while loading the admin view")
    st.exception(e)
    st.error(
        "**This may be caused by:**\n\n"
        "- Missing or outdated view files in `admin/views/`\n"
        "- Syntax errors in view files\n"
        "- Incorrect imports in view files\n\n"
        "**Check the error details above for more information.**"
    )