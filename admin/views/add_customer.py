# admin/pages/add_customer.py
from typing import List
import streamlit as st
from services.config_manager import load_catalog, save_catalog, add_customer as cm_add_customer

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

        cid, _cust = cm_add_customer(catalog, name.strip(), addresses_clean)
        save_catalog(catalog)
        st.success(f"Customer created with ID: {cid}")
        st.rerun()
