import streamlit as st
from warehouses.nl_svz import compute_nl_svz
from warehouses.de_offergeld import compute_de_offergeld
from warehouses.fr_coquelle import compute_fr_coquelle
from warehouses.sk_arufel import compute_sk_arufel
from warehouses.nl_mentrex import compute_nl_mentrex
from warehouses.ro_giurgiu import compute_ro_giurgiu

st.set_page_config(page_title="VVP Calculator", layout="wide")
st.title("VVP Calculator")

# ---------------------------------
# Session defaults
# ---------------------------------
if "step" not in st.session_state:
    st.session_state.step = "inputs"  # "inputs" | "details"

for key, default in {
    "warehouse": "-- Select a warehouse --",
    "buying_transport_cost": 0.0,
    "pieces": 1,
    "pallets": 1,
    "weeks": 1,
}.items():
    st.session_state.setdefault(key, default)

WAREHOUSES = [
    "Netherlands / SVZ",
    "Germany / Offergeld",
    "Slovakia / Arufel",
    "France / Coquelle",
    "Romania / Giurgiu",
    "Netherlands / Mentrex",
]

def _dispatch(warehouse: str, pieces: int, pallets: int, weeks: int, buying_transport_cost: float):
    if warehouse == "Netherlands / SVZ":
        compute_nl_svz(pieces, pallets, weeks, buying_transport_cost)
    elif warehouse == "Germany / Offergeld":
        compute_de_offergeld(pieces, pallets, weeks, buying_transport_cost)
    elif warehouse == "Slovakia / Arufel":
        compute_sk_arufel(pieces, pallets, weeks, buying_transport_cost)
    elif warehouse == "France / Coquelle":
        compute_fr_coquelle(pieces, pallets, weeks, buying_transport_cost)
    elif warehouse == "Romania / Giurgiu":
        compute_ro_giurgiu(pieces, pallets, weeks, buying_transport_cost)
    elif warehouse == "Netherlands / Mentrex":
        compute_nl_mentrex(pieces, pallets, weeks, buying_transport_cost)
    else:
        st.info("This warehouse’s specific rules are not implemented yet.")

# =========================
# STEP 1: INPUTS (form)
# =========================
if st.session_state.step == "inputs":
    warehouse = st.selectbox(
        "Select Warehouse",
        ["-- Select a warehouse --"] + WAREHOUSES,
        index=(["-- Select a warehouse --"] + WAREHOUSES).index(st.session_state.warehouse)
        if st.session_state.warehouse in ["-- Select a warehouse --"] + WAREHOUSES else 0
    )

    st.subheader("Order Inputs")
    st.markdown("<span style='color:red'>* Required fields</span>", unsafe_allow_html=True)

    with st.form("order_form", clear_on_submit=False):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown("Buying Transport Cost (€ total)", unsafe_allow_html=True)
            buying_transport_cost = st.number_input(
                label="Buying Transport Cost (€ total)",
                min_value=0.0, step=1.0, value=float(st.session_state.buying_transport_cost),
                format="%.2f", label_visibility="collapsed",
            )
        with c2:
            st.markdown("Pieces (#) <span style='color:red'>*</span>", unsafe_allow_html=True)
            pieces = st.number_input(
                label="Pieces (#)", min_value=1, step=1, value=int(st.session_state.pieces),
                format="%d", label_visibility="collapsed",
            )
        with c3:
            st.markdown("Pallets (#) <span style='color:red'>*</span>", unsafe_allow_html=True)
            pallets = st.number_input(
                label="Pallets (#)", min_value=1, step=1, value=int(st.session_state.pallets),
                format="%d", label_visibility="collapsed",
            )
        with c4:
            st.markdown("Weeks in Storage <span style='color:red'>*</span>", unsafe_allow_html=True)
            weeks = st.number_input(
                label="Weeks in Storage", min_value=1, step=1, value=int(st.session_state.weeks),
                format="%d", label_visibility="collapsed",
            )

        next_clicked = st.form_submit_button("Next →", type="primary")

    if next_clicked:
        if warehouse == "-- Select a warehouse --":
            st.warning("Please select a warehouse to continue.")
            st.stop()
        if pallets > 66:
            st.error("❌ Invalid input: Pallets cannot exceed 66. Please enter a valid pallet number.")
            st.stop()
        if any(v is None or v <= 0 for v in [pieces, pallets, weeks]):
            st.warning("Fields marked with a red * are mandatory and must be greater than 0.")
            st.stop()

        st.session_state.warehouse = warehouse
        st.session_state.buying_transport_cost = float(buying_transport_cost)
        st.session_state.pieces = int(pieces)
        st.session_state.pallets = int(pallets)
        st.session_state.weeks = int(weeks)
        st.session_state.step = "details"
        st.rerun()

# =========================
# STEP 2: DETAILS
# =========================
else:
    # Warehouse name
    st.selectbox(
        "Warehouse (locked, to change it go Back)",
        ["-- Select a warehouse --"] + WAREHOUSES,
        index=(["-- Select a warehouse --"] + WAREHOUSES).index(st.session_state.warehouse),
        disabled=True,
    )

    # Back button right under warehouse selection
    if st.button("← Back", use_container_width=False):
        st.session_state.step = "inputs"
        st.rerun()

    # Show locked inputs as read-only summary
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

    # Dispatch to warehouse logic
    _dispatch(
        st.session_state.warehouse,
        st.session_state.pieces,
        st.session_state.pallets,
        st.session_state.weeks,
        st.session_state.buying_transport_cost,
    )
