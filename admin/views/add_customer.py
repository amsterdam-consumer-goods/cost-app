# admin/pages/add_customer.py
from typing import List
import streamlit as st
import sys
import importlib.util
from pathlib import Path

# Manually load config_manager module
_root = Path(__file__).resolve().parents[2]
_cm_path = _root / "services" / "config_manager.py"
_spec = importlib.util.spec_from_file_location("services.config_manager", _cm_path)
_cm = importlib.util.module_from_spec(_spec)
sys.modules["services.config_manager"] = _cm
_spec.loader.exec_module(_cm)

load_catalog = _cm.load_catalog
save_catalog = _cm.save_catalog
cm_add_customer = _cm.add_customer

def page_add_customer():
    st.title("Admin • Add Customer")
    catalog = load_catalog()

    name = st.text_input("Customer name")

    if "addr_count" not in st.session_state:
        st.session_state.addr_count = 1

    if st.button("Add another address"):
        st.session_state.addr_count += 1

    addresses: List[str] = []
    for i in range(st.session_state.addr_count):
        addr = st.text_input(f"Address #{i+1} (single line)", key=f"addr_{i}", placeholder="e.g., Main St 10, 1011AB Amsterdam, NL")
        addresses.append(addr.strip())

    if st.button("Create customer", type="primary"):
        if not (name and name.strip()):
            st.error("Name required.")
            return
        addresses_clean = [a for a in addresses if a]
        if not addresses_clean:
            st.error("Please enter at least one address line.")
            return

        catalog, cid = cm_add_customer(catalog, {"name": name.strip(), "addresses": addresses_clean})
        save_catalog(catalog)
        st.success(f"Customer created with ID: {cid}")
        st.rerun()