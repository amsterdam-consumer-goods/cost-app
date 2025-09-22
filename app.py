"""
Streamlit app entry for the VVP Calculator.

This module:
- Enforces a simple password gate (via Streamlit secrets or local env var).
- Collects core order inputs with a two-step flow (Inputs → Details).
- Dispatches to per-warehouse calculators to render costs and results.

Business logic for each warehouse lives in `warehouses/*.py`.
"""

from __future__ import annotations

import os
import streamlit as st

from warehouses.de_offergeld import compute_de_offergeld
from warehouses.fr_coquelle import compute_fr_coquelle
from warehouses.nl_mentrex import compute_nl_mentrex
from warehouses.nl_svz import compute_nl_svz
from warehouses.ro_giurgiu import compute_ro_giurgiu
from warehouses.sk_arufel import compute_sk_arufel


# =============================================================================
# Password gate
# =============================================================================
def check_password() -> bool:
    """Return True if the user is authenticated.

    Reads the password from:
      1) `st.secrets["APP_PASSWORD"]` on Streamlit Cloud, or
      2) `os.environ["APP_PASSWORD"]` locally (fallback).

    If no password is configured, the app does not block (useful for local dev).
    """
    secret_pw = st.secrets.get("APP_PASSWORD", os.environ.get("APP_PASSWORD"))

    # No password configured → allow access
    if not secret_pw:
        return True

    # Session already authenticated
    if st.session_state.get("auth_ok"):
        return True

    # Prompt for password
    st.title("🔐 Enter Password")
    pw = st.text_input("Password", type="password", placeholder="Enter password…")

    col_btn, _ = st.columns([1, 3])
    with col_btn:
        if st.button("Sign in"):
            st.session_state.auth_ok = pw == str(secret_pw)
            if not st.session_state.auth_ok:
                st.error("Incorrect password.")
            else:
                st.rerun()

    return False


# =============================================================================
# Page config & auth
# =============================================================================
st.set_page_config(page_title="VVP Calculator", layout="wide")

# Block the app until authenticated
if not check_password():
    st.stop()

# Quick logout (top-right area)
right_col = st.columns([6, 1])[1]
with right_col:
    if st.button("Logout"):
        st.session_state.pop("auth_ok", None)
        st.rerun()

st.title("VVP Calculator")

# =============================================================================
# Session defaults
# =============================================================================
if "step" not in st.session_state:
    # Two-step flow: "inputs" → "details"
    st.session_state.step = "inputs"

# Persisted form fields (with sensible defaults)
# Session defaults
for key, default in {
    "warehouse": "-- Select a warehouse --",
    "buying_transport_cost": 0.0,
    "pieces": 1,
    "pallets": 1,
    "weeks": 2,
    "pallet_unit_cost": 0.0,   # ← NEW: € per pallet (optional)
}.items():
    st.session_state.setdefault(key, default)


WAREHOUSES: list[str] = [
    "Netherlands / SVZ",
    "Germany / Offergeld",
    "Slovakia / Arufel",
    "France / Coquelle",
    "Romania / Giurgiu",
    "Netherlands / Mentrex",
]


def _dispatch(warehouse: str, pieces: int, pallets: int, weeks: int,
              buying_transport_cost: float, pallet_unit_cost: float):
    if warehouse == "Netherlands / SVZ":
        compute_nl_svz(pieces, pallets, weeks, buying_transport_cost, pallet_unit_cost)
    elif warehouse == "Germany / Offergeld":
        compute_de_offergeld(pieces, pallets, weeks, buying_transport_cost, pallet_unit_cost)
    elif warehouse == "Slovakia / Arufel":
        compute_sk_arufel(pieces, pallets, weeks, buying_transport_cost, pallet_unit_cost)
    elif warehouse == "France / Coquelle":
        compute_fr_coquelle(pieces, pallets, weeks, buying_transport_cost, pallet_unit_cost)
    elif warehouse == "Romania / Giurgiu":
        compute_ro_giurgiu(pieces, pallets, weeks, buying_transport_cost, pallet_unit_cost)
    elif warehouse == "Netherlands / Mentrex":
        compute_nl_mentrex(pieces, pallets, weeks, buying_transport_cost, pallet_unit_cost)
    else:
        st.info("This warehouse’s specific rules are not implemented yet.")


# =============================================================================
# Step 1 — Inputs
# =============================================================================
if st.session_state.step == "inputs":
    warehouse = st.selectbox(
        "Select Warehouse",
        ["-- Select a warehouse --"] + WAREHOUSES,
        index=(
            (["-- Select a warehouse --"] + WAREHOUSES).index(st.session_state.warehouse)
            if st.session_state.warehouse in ["-- Select a warehouse --"] + WAREHOUSES
            else 0
        ),
    )

    st.subheader("Order Inputs")
    st.markdown("<span style='color:red'>* Required fields</span>", unsafe_allow_html=True)

    # Use a form so Enter/Submit doesn’t jump to the next step prematurely
    with st.form("order_form", clear_on_submit=False):
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.markdown("Buying Transport Cost (€ total)", unsafe_allow_html=True)
            buying_transport_cost = st.number_input(
                "Buying Transport Cost (€ total)",
                min_value=0.0,
                step=1.0,
                value=float(st.session_state.buying_transport_cost),
                format="%.2f",
                label_visibility="collapsed",
            )

        with c2:
            st.markdown("Pieces (#) <span style='color:red'>*</span>", unsafe_allow_html=True)
            pieces = st.number_input(
                "Pieces (#)",
                min_value=1,
                step=1,
                value=int(st.session_state.pieces),
                format="%d",
                label_visibility="collapsed",
            )

        with c3:
            st.markdown("Pallets (#) <span style='color:red'>*</span>", unsafe_allow_html=True)
            pallets = st.number_input(
                "Pallets (#)",
                min_value=1, step=1,
                value=int(st.session_state.pallets),
                format="%d", label_visibility="collapsed",
            )
            pallet_unit_cost = st.number_input(
                "Pallet Cost (€ per pallet) — optional",
                min_value=0.0, step=0.01,
                value=float(st.session_state.pallet_unit_cost),
                format="%.2f",
            )

        with c4:
            st.markdown("Weeks in Storage (min 2) <span style='color:red'>*</span>", unsafe_allow_html=True)
            weeks = st.number_input(
                "Weeks in Storage",
                min_value=2,                        # ← enforce at least 2
                step=1,
                value=int(max(2, st.session_state.weeks)),  # ← keep UI safe if session had 1
                format="%d",
                label_visibility="collapsed",
            )

        next_clicked = st.form_submit_button("Next →", type="primary")

    if next_clicked:
        if warehouse == "-- Select a warehouse --":
            st.warning("Please select a warehouse to continue.")
            st.stop()

        if pallets > 66:
            st.error("❌ Invalid input: Pallets cannot exceed 66. Please enter a valid pallet number.")
            st.stop()

        if weeks < 2:   # ← new rule
            st.error("You need to order at least 2 weeks of storage.")
            st.stop()

        if any(v is None or v <= 0 for v in [pieces, pallets, weeks]):
            st.warning("Fields marked with a red * are mandatory and must be greater than 0.")
            st.stop()

        # ... proceed to save into session_state and go to details


        # Persist to session and go to Step 2
        st.session_state.warehouse = warehouse
        st.session_state.buying_transport_cost = float(buying_transport_cost)
        st.session_state.pieces = int(pieces)
        st.session_state.pallets = int(pallets)
        st.session_state.weeks = int(weeks)
        st.session_state.pallet_unit_cost = float(pallet_unit_cost)  # ← NEW
        st.session_state.step = "details"
        st.rerun()

# =============================================================================
# Step 2 — Details / Results
# =============================================================================
else:
    # Locked warehouse display
    st.selectbox(
        "Warehouse (locked, to change it go Back)",
        ["-- Select a warehouse --"] + WAREHOUSES,
        index=(["-- Select a warehouse --"] + WAREHOUSES).index(st.session_state.warehouse),
        disabled=True,
    )

    # Back button directly under the warehouse selector
    if st.button("← Back", use_container_width=False):
        st.session_state.step = "inputs"
        st.rerun()

    # Read-only recap of inputs
    st.markdown("### Order Summary")
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.metric("Buying Transport Cost (€)", f"{st.session_state.buying_transport_cost:.2f}")
    with s2:
        st.metric("Pieces (#)", f"{st.session_state.pieces}")
    with s3:
        st.metric("Pallets (#)", f"{st.session_state.pallets}")
    with s4:
        st.metric("Weeks in Storage", f"{st.session_state.weeks}")

    st.markdown("---")

    # Run the warehouse-specific calculator
    _dispatch(
        st.session_state.warehouse,
        st.session_state.pieces,
        st.session_state.pallets,
        st.session_state.weeks,
        st.session_state.buying_transport_cost,
        st.session_state.pallet_unit_cost,   # ← NEW
    )

