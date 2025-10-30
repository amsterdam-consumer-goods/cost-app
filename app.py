"""
Streamlit entrypoint for the VVP Calculator.
- Main screen asks for USER password -> Calculator UI
- Sidebar has an Admin Login -> if correct, jump to Admin Panel
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

# Add project root to Python path FIRST
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Force reload of our local modules to avoid Cloud caching issues
import importlib
for module_name in ['services', 'services.catalog', 'services.catalog_adapter', 
                     'warehouses', 'warehouses.final_calc', 'warehouses.second_leg', 'warehouses.generic']:
    if module_name in sys.modules:
        del sys.modules[module_name]

import streamlit as st

# Now import our modules
from services.catalog import load as load_catalog
from services.catalog_adapter import normalize_catalog
from warehouses.generic import compute_generic

# -----------------------------------------------------------------------------
# Page setup
# -----------------------------------------------------------------------------
st.set_page_config(page_title="VVP Calculator", layout="wide")
st.markdown("<style>.stImage img { border-radius: 0 !important; }</style>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Passwords
# -----------------------------------------------------------------------------
APP_PASSWORD = st.secrets.get("APP_PASSWORD", os.environ.get("APP_PASSWORD"))
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", os.environ.get("ADMIN_PASSWORD"))

# -----------------------------------------------------------------------------
# Admin login (sidebar) -> if ok, we render admin panel immediately
# -----------------------------------------------------------------------------
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# =============================
# Admin Login + Admin Panel
# =============================
st.sidebar.markdown("### Admin Login")
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# Login / Logout
if not st.session_state.is_admin:
    admin_pw = st.sidebar.text_input("Password", type="password", placeholder="••••••••", key="admin_pw")
    if st.sidebar.button("Login", use_container_width=True, key="admin_login_btn"):
        if ADMIN_PASSWORD and admin_pw == str(ADMIN_PASSWORD):
            st.session_state.is_admin = True
            st.sidebar.success("✅ Admin access granted")
            st.rerun()
        else:
            st.sidebar.error("❌ Wrong password")
else:
    st.sidebar.success("🟢 Logged in as Admin")
    if st.sidebar.button("Logout Admin", use_container_width=True, key="admin_logout_btn"):
        st.session_state.is_admin = False
        st.rerun()

# Admin panel (tek seçimli menü: RADIO)
if st.session_state.is_admin:
    st.image("assets/logo2.png", width=190)
    st.title("🛠️ Admin Panel")

    # admin/app.py ile birebir aynı etiketler
    choice = st.sidebar.radio(
        "Admin Pages",
        options=["Update warehouse", "Add warehouse", "Add customer"],
        index=0,
        key="admin_page_choice",
    )

    try:
        from admin.views import admin_router
        admin_router(choice)
    except Exception as e:
        st.error("Admin views are not available.")
        st.exception(e)  # Tam traceback'i gösterir

    st.stop()  # admin modunda calculator render edilmez

# -----------------------------------------------------------------------------
# USER password gate (main screen)
# -----------------------------------------------------------------------------
def check_password() -> bool:
    # If no user password set, let users in directly
    if not APP_PASSWORD:
        return True
    if st.session_state.get("auth_ok"):
        return True

    st.image("assets/logo2.png", width=190)
    st.title("🔐 Enter Password")
    pw = st.text_input("Password", type="password", placeholder="Enter password…", key="user_pw_box")
    if st.button("Sign in", key="user_signin_btn"):
        st.session_state.auth_ok = pw == str(APP_PASSWORD)
        if not st.session_state.auth_ok:
            st.error("Incorrect password.")
        else:
            st.rerun()
    return False

if not check_password():
    st.stop()

# -----------------------------------------------------------------------------
# Calculator UI (for normal users)
# -----------------------------------------------------------------------------
st.image("assets/logo2.png", width=190)
hdr_c, hdr_r = st.columns([6, 1])
with hdr_c:
    st.title("📦 VVP and Final Calculator")
with hdr_r:
    if st.button("Logout User"):
        st.session_state.pop("auth_ok", None)
        st.rerun()
st.markdown("---")

if "step" not in st.session_state:
    st.session_state.step = "inputs"

for key, default in {
    "warehouse": "-- Select a warehouse --",
    "buying_transport_cost": 0.0,
    "pieces": 1,
    "pallets": 1,
    "weeks": 4,
    "pallet_unit_cost": 0.0,
}.items():
    st.session_state.setdefault(key, default)

def _dispatch(
    warehouse_label: str,
    pieces: int,
    pallets: int,
    weeks: int,
    buying_transport_cost: float,
    pallet_unit_cost: float,
) -> None:
    catalog = normalize_catalog(load_catalog())
    whs = catalog.get("warehouses", []) or []
    label_map = {}
    for w in whs:
        country = (w.get("country") or "").strip()
        name = (w.get("name") or w.get("id") or "Warehouse").strip()
        lbl = f"{country} / {name}" if country else name
        label_map[lbl] = w

    selected_wh = label_map.get(warehouse_label)
    if not selected_wh:
        rhs = warehouse_label.split("/", 1)[-1].strip().lower()
        for lbl, w in label_map.items():
            name = str(w.get("name", "")).strip().lower()
            lbl_rhs = lbl.split("/", 1)[-1].strip().lower()
            if (
                name == rhs
                or lbl_rhs == rhs
                or name.startswith(rhs)
                or rhs.startswith(name)
                or rhs in name
                or name in rhs
            ):
                selected_wh = w
                break

    if not selected_wh:
        st.error(
            "Selected warehouse not found in catalog.json.\n\n"
            "• Check if it's defined as 'Country / Name' in Admin.\n"
            "• Or select a valid warehouse from the list."
        )
        return

    id_map = {w.get("id"): w for w in whs if w.get("id")}
    compute_generic(
        wh=selected_wh,
        all_whs_map=id_map,
        pieces=pieces,
        pallets=pallets,
        weeks=weeks,
        buying_transport_cost=buying_transport_cost,
        pallet_unit_cost=pallet_unit_cost,
    )

if st.button("🔄 Refresh warehouses list"):
    st.rerun()

if st.session_state.step == "inputs":
    catalog = normalize_catalog(load_catalog())
    whs = catalog.get("warehouses", []) or []
    WAREHOUSE_OPTIONS = []
    for w in whs:
        country = (w.get("country") or "").strip()
        name = (w.get("name") or w.get("id") or "Warehouse").strip()
        label = f"{country} / {name}" if country else name
        WAREHOUSE_OPTIONS.append(label)

    warehouse = st.selectbox(
        "Select Warehouse",
        ["-- Select a warehouse --"] + WAREHOUSE_OPTIONS,
        index=(["-- Select a warehouse --"] + WAREHOUSE_OPTIONS).index(st.session_state.warehouse)
        if st.session_state.warehouse in ["-- Select a warehouse --"] + WAREHOUSE_OPTIONS
        else 0,
    )

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

    if next_clicked:
        if warehouse == "-- Select a warehouse --":
            st.warning("Please select a warehouse to continue.")
            st.stop()
        if pallets > 66:
            st.error("Pallets cannot exceed 66.")
            st.stop()
        if weeks < 4:
            st.error("You need to order at least 4 weeks of storage.")
            st.stop()
        if any(v is None or v <= 0 for v in [pieces, pallets, weeks]):
            st.warning("Fields marked with * are required and must be > 0.")
            st.stop()

        st.session_state.warehouse = warehouse
        st.session_state.buying_transport_cost = float(buying_transport_cost)
        st.session_state.pieces = int(pieces)
        st.session_state.pallets = int(pallets)
        st.session_state.weeks = int(weeks)
        st.session_state.pallet_unit_cost = float(pallet_unit_cost)
        st.session_state.step = "details"
        st.rerun()
else:
    catalog = normalize_catalog(load_catalog())
    whs = catalog.get("warehouses", []) or []
    WAREHOUSE_OPTIONS = []
    for w in whs:
        country = (w.get("country") or "").strip()
        name = (w.get("name") or w.get("id") or "Warehouse").strip()
        label = f"{country} / {name}" if country else name
        WAREHOUSE_OPTIONS.append(label)

    st.selectbox(
        "Warehouse (locked, change via Back)",
        ["-- Select a warehouse --"] + WAREHOUSE_OPTIONS,
        index=(["-- Select a warehouse --"] + WAREHOUSE_OPTIONS).index(st.session_state.warehouse)
        if st.session_state.warehouse in ["-- Select a warehouse --"] + WAREHOUSE_OPTIONS
        else 0,
        disabled=True,
    )

    if st.button("← Back", use_container_width=False):
        st.session_state.step = "inputs"
        st.rerun()

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

    _dispatch(
        st.session_state.warehouse,
        st.session_state.pieces,
        st.session_state.pallets,
        st.session_state.weeks,
        st.session_state.buying_transport_cost,
        st.session_state.pallet_unit_cost,
    )