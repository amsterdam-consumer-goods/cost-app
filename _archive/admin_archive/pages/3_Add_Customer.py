import streamlit as st
from services.config_manager import load_catalog, save_catalog, add_customer

st.title("Add Customer")
KEY = "cust_"

catalog = load_catalog()

cust_name = st.text_input("Customer name", key=f"{KEY}name").strip()

addr_count = st.number_input("How many addresses?", min_value=1, value=1, step=1, key=f"{KEY}count")
addresses = []
for i in range(int(addr_count)):
    a = st.text_input(f"Address {i+1}", key=f"{KEY}addr_{i}").strip()
    addresses.append(a)

if st.button("Create customer", type="primary", key=f"{KEY}create"):
    errs = []
    if not cust_name:
        errs.append("Customer name is required.")
    clean_addrs = [a for a in addresses if a]
    if not clean_addrs:
        errs.append("At least one address is required.")

    if errs:
        st.error(" • " + "\n • ".join(errs))
    else:
        cid, _ = add_customer(catalog, cust_name, clean_addrs)
        save_catalog(catalog)
        st.success(f"Customer '{cust_name}' created with id '{cid}'.")
