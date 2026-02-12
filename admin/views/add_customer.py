"""
Customer Management Page
========================

Admin interface for creating, editing, and deleting customers.

Features:
- Create new customers with multiple addresses
- Edit existing customer information
- Link customers to warehouses
- Delete customers with inline confirmation
- Dynamic address management (add/remove)
- State isolation between operations
- Success messages with persistence

Customer Data Structure:
- name: Customer display name
- addresses: List of address strings
- warehouses: List of warehouse IDs (optional linking)

State Management:
- Separate tabs for Create and Edit operations
- Form state reset after successful operations
- Fresh catalog load before each operation
- Detection of catalog changes to reset selections

Usage:
- Called by admin router
- Manages customer entries in catalog.json
- Provides warehouse linking functionality
- Clears cache after modifications

Related Files:
- services/config_manager.py: Catalog persistence and customer operations
"""

from __future__ import annotations

from typing import List, Dict, Any, Tuple, Optional
import streamlit as st
import sys
import importlib.util
from pathlib import Path

# ============================================================================
# MODULE IMPORTS
# ============================================================================

# Load config_manager without altering sys.path
_root = Path(__file__).resolve().parents[2]
_cm_path = _root / "services" / "config_manager.py"
_spec = importlib.util.spec_from_file_location("services.config_manager", _cm_path)
_cm = importlib.util.module_from_spec(_spec)
sys.modules["services.config_manager"] = _cm
_spec.loader.exec_module(_cm)

load_catalog = _cm.load_catalog
save_catalog = _cm.save_catalog
add_customer = _cm.add_customer
list_warehouse_ids = _cm.list_warehouse_ids
get_last_warning = getattr(_cm, "get_last_warning", lambda: None)


# ============================================================================
# CUSTOMER DATA UTILITIES
# ============================================================================

def get_customers(catalog: Dict[str, Any]):
    """Extract customers list/dict from catalog."""
    return catalog.get("customers")


def set_customers(catalog: Dict[str, Any], customers):
    """Update customers in catalog."""
    catalog["customers"] = customers
    return catalog


def customers_to_choices(customers) -> List[Tuple[str, str]]:
    """
    Convert customers to selectbox choices.
    
    Handles both dict and list storage formats.
    
    Args:
        customers: Customers data (dict or list)
        
    Returns:
        List of (customer_id, display_label) tuples
    """
    choices: List[Tuple[str, str]] = []
    
    if isinstance(customers, dict):
        for cid, obj in customers.items():
            name = (obj or {}).get("name", str(cid))
            choices.append((str(cid), f"{cid} — {name}"))
    
    elif isinstance(customers, list):
        for obj in customers:
            if isinstance(obj, dict):
                cid = str(
                    obj.get("id")
                    or obj.get("cid")
                    or obj.get("code")
                    or obj.get("name")
                    or ""
                )
                if cid:
                    name = obj.get("name", cid)
                    choices.append((cid, f"{cid} — {name}"))
    
    return sorted(choices, key=lambda x: x[1].lower())


def get_customer_by_id(catalog: Dict[str, Any], customer_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve customer by ID.
    
    Handles both dict and list storage formats.
    
    Args:
        catalog: Complete catalog dictionary
        customer_id: Customer ID to find
        
    Returns:
        Customer dictionary if found, None otherwise
    """
    customers = get_customers(catalog)
    
    if isinstance(customers, dict):
        obj = customers.get(customer_id)
        if isinstance(obj, dict):
            return {"id": customer_id, **obj}
    
    elif isinstance(customers, list):
        for obj in customers:
            if isinstance(obj, dict):
                oid = str(
                    obj.get("id")
                    or obj.get("cid")
                    or obj.get("code")
                    or obj.get("name")
                    or ""
                )
                if oid == customer_id:
                    return obj
    
    return None


def save_customer(catalog: Dict[str, Any], customer_obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Upsert customer in catalog.
    
    Supports both dict and list storage formats.
    
    Args:
        catalog: Complete catalog dictionary
        customer_obj: Customer data to save
        
    Returns:
        Updated catalog
    """
    customer_id = str(customer_obj.get("id"))
    customers = get_customers(catalog)
    
    if customers is None:
        customers = {customer_id: {k: v for k, v in customer_obj.items() if k != "id"}}
        return set_customers(catalog, customers)
    
    if isinstance(customers, dict):
        customers[customer_id] = {k: v for k, v in customer_obj.items() if k != "id"}
        return catalog
    
    if isinstance(customers, list):
        replaced = False
        for i, item in enumerate(customers):
            if isinstance(item, dict):
                oid = str(
                    item.get("id")
                    or item.get("cid")
                    or item.get("code")
                    or item.get("name")
                    or ""
                )
                if oid == customer_id:
                    customers[i] = customer_obj
                    replaced = True
                    break
        
        if not replaced:
            customers.append(customer_obj)
        
        return catalog
    
    # Unexpected format - reset to dict
    return set_customers(
        catalog,
        {customer_id: {k: v for k, v in customer_obj.items() if k != "id"}}
    )


def delete_customer(catalog: Dict[str, Any], customer_id: str) -> Dict[str, Any]:
    """
    Delete customer from catalog.
    
    Args:
        catalog: Complete catalog dictionary
        customer_id: Customer ID to delete
        
    Returns:
        Updated catalog
    """
    customers = get_customers(catalog)
    
    if isinstance(customers, dict):
        customers.pop(customer_id, None)
        return catalog
    
    if isinstance(customers, list):
        customers[:] = [
            item for item in customers
            if not (
                isinstance(item, dict)
                and str(
                    item.get("id")
                    or item.get("cid")
                    or item.get("code")
                    or item.get("name")
                    or ""
                ) == customer_id
            )
        ]
        return catalog
    
    return catalog


# ============================================================================
# MAIN PAGE
# ============================================================================

def page_add_customer():
    """Render the Customer Management page."""
    
    st.title("Admin • Customers")
    st.caption("Create, edit, and manage customer information")
    
    # Show backend warning if any (e.g., Gist fallback)
    warning = get_last_warning()
    if warning and not st.session_state.get("warn_shown_add_customer"):
        st.info(warning)
        st.session_state["warn_shown_add_customer"] = True
    
    # Initialize persistent flags
    st.session_state.setdefault("create_success_cid", "")
    st.session_state.setdefault("edit_success", False)
    st.session_state.setdefault("delete_success", False)
    
    # Tabs for different operations
    tab_create, tab_edit = st.tabs(["➕ Create Customer", "📝 Edit / Delete Customer"])
    
    # -------------------------------------------------------------------------
    # CREATE TAB
    # -------------------------------------------------------------------------
    with tab_create:
        catalog = load_catalog()
        
        # Show warning again if present
        warning = get_last_warning()
        if warning:
            st.info(warning)
        
        with st.form("create_customer_form", clear_on_submit=False):
            st.subheader("Customer Information")
            
            name = st.text_input(
                "Customer name",
                key="new_customer_name",
                placeholder="e.g., ACME Corporation BV"
            )
            
            # Dynamic address inputs
            st.markdown("**Addresses**")
            st.session_state.setdefault("new_addr_count", 1)
            
            col_a, col_b = st.columns([1, 1])
            add_addr = col_a.form_submit_button("Add another address")
            reset_addr = col_b.form_submit_button("Reset addresses")
            
            if add_addr:
                st.session_state.new_addr_count += 1
                st.rerun()
            
            if reset_addr:
                st.session_state.new_addr_count = 1
                for k in list(st.session_state.keys()):
                    if str(k).startswith("new_addr_"):
                        del st.session_state[k]
                st.rerun()
            
            addresses: List[str] = []
            for i in range(st.session_state.new_addr_count):
                addr = st.text_input(
                    f"Address #{i+1}",
                    key=f"new_addr_{i}",
                    placeholder="e.g., Main Street 10, 1011AB Amsterdam, Netherlands",
                )
                addresses.append((addr or "").strip())
            
            submitted = st.form_submit_button("Create customer", type="primary")
        
        if submitted:
            if not (name and name.strip()):
                st.error("❌ Customer name is required")
            else:
                addresses_clean = [a for a in addresses if a]
                
                if not addresses_clean:
                    st.error("❌ Please enter at least one address")
                else:
                    # Fresh catalog load before saving
                    catalog = load_catalog()
                    
                    catalog, customer_id = add_customer(
                        catalog,
                        {"name": name.strip(), "addresses": addresses_clean}
                    )
                    
                    save_catalog(catalog)
                    
                    # Clear form inputs
                    st.session_state.create_success_cid = customer_id
                    st.session_state.new_addr_count = 1
                    for k in list(st.session_state.keys()):
                        if str(k).startswith("new_addr_") or k == "new_customer_name":
                            del st.session_state[k]
                    
                    st.toast("Customer created", icon="✅")
                    st.rerun()
        
        # Show success message
        if st.session_state.create_success_cid:
            st.success(f"✅ Customer created (ID: {st.session_state.create_success_cid})")
            
            warning = get_last_warning()
            if warning:
                st.info(warning)
            
            if st.button("Clear message"):
                st.session_state.create_success_cid = ""
                st.rerun()
    
    # -------------------------------------------------------------------------
    # EDIT / DELETE TAB
    # -------------------------------------------------------------------------
    with tab_edit:
        catalog = load_catalog()
        
        warning = get_last_warning()
        if warning:
            st.info(warning)
        
        customers = get_customers(catalog)
        choices = customers_to_choices(customers)
        
        if not choices:
            st.info("No customers yet. Create one in the 'Create Customer' tab.")
            return
        
        # Reset selection on catalog change
        if "edit_customer_choices_hash" not in st.session_state:
            st.session_state.edit_customer_choices_hash = str(choices)
        elif st.session_state.edit_customer_choices_hash != str(choices):
            st.session_state.edit_customer_choices_hash = str(choices)
            if "selected_customer_cid" in st.session_state:
                del st.session_state.selected_customer_cid
        
        customer_id = st.selectbox(
            "Select customer",
            options=[c[0] for c in choices],
            format_func=lambda v: dict(choices).get(v, v),
            key="selected_customer_cid"
        )
        
        # Clear form state when customer changes
        if "last_edited_cid" not in st.session_state or st.session_state.last_edited_cid != customer_id:
            st.session_state.last_edited_cid = customer_id
            # Clear all edit-related keys for old customer
            for k in list(st.session_state.keys()):
                if k.startswith("ed_") and not k.startswith(f"ed_{customer_id}_"):
                    del st.session_state[k]
        
        customer = get_customer_by_id(catalog, customer_id)
        if not customer:
            st.error("Customer not found (possibly deleted)")
            return
        
        # Unique form key per customer (forces widget reset on selection change)
        with st.form(f"edit_customer_form_{customer_id}", clear_on_submit=False):
            st.subheader("Customer Information")
            
            name = st.text_input(
                "Name",
                value=customer.get("name", customer_id),
                key=f"edit_name_{customer_id}"
            )
            
            # Address management
            st.markdown("**Addresses**")
            addresses: List[str] = list(map(str, customer.get("addresses", [])))
            
            key_prefix = f"ed_{customer_id}_"
            
            # Reset delete flags when customer changes
            if f"{key_prefix}last_cid" not in st.session_state or st.session_state[f"{key_prefix}last_cid"] != customer_id:
                st.session_state[f"{key_prefix}last_cid"] = customer_id
                st.session_state[key_prefix + "addr_del_flags"] = [False] * len(addresses)
                st.session_state[key_prefix + "new_addr_count"] = 0
            
            # Ensure flags list matches current addresses
            if len(st.session_state.get(key_prefix + "addr_del_flags", [])) != len(addresses):
                st.session_state[key_prefix + "addr_del_flags"] = [False] * len(addresses)
            
            # Existing addresses
            for i, addr in enumerate(addresses):
                cols = st.columns([8, 2])
                cols[0].text_input(
                    f"Address #{i+1}",
                    value=addr,
                    key=f"{key_prefix}addr_{i}"
                )
                st.session_state[key_prefix + "addr_del_flags"][i] = cols[1].checkbox(
                    "Delete",
                    key=f"{key_prefix}del_{i}",
                    value=st.session_state[key_prefix + "addr_del_flags"][i]
                )
            
            # New address lines
            st.session_state.setdefault(key_prefix + "new_addr_count", 0)
            
            if st.form_submit_button("Add another address"):
                st.session_state[key_prefix + "new_addr_count"] += 1
                st.rerun()
            
            new_lines: List[str] = []
            for i in range(st.session_state[key_prefix + "new_addr_count"]):
                v = st.text_input(
                    f"New address #{i+1}",
                    key=f"{key_prefix}new_addr_line_{i}",
                    placeholder="e.g., Warehouse Lane 5, 3542XX Utrecht, Netherlands",
                )
                if v:
                    new_lines.append(v.strip())
            
            # Warehouse linking
            st.markdown("**Linked Warehouses**")
            all_warehouse_ids = list_warehouse_ids(catalog)
            current_warehouses: List[str] = list(map(str, customer.get("warehouses", [])))
            
            selected_warehouses = st.multiselect(
                "Select warehouses for this customer",
                options=all_warehouse_ids,
                default=current_warehouses,
                key=f"edit_whs_{customer_id}",
                help="These warehouses will be associated with this customer"
            )
            
            # Action buttons
            col_save, col_delete = st.columns([1, 1])
            save_clicked = col_save.form_submit_button("💾 Save changes", type="primary")
            delete_clicked = col_delete.form_submit_button("🗑️ Delete customer", type="secondary")
        
        # Handle save
        if save_clicked:
            edited_addresses: List[str] = []
            
            # Collect non-deleted existing addresses
            for i in range(len(addresses)):
                if not st.session_state[key_prefix + "addr_del_flags"][i]:
                    edited_val = st.session_state.get(f"{key_prefix}addr_{i}", addresses[i]).strip()
                    if edited_val:
                        edited_addresses.append(edited_val)
            
            # Add new address lines
            for new_line in new_lines:
                if new_line:
                    edited_addresses.append(new_line)
            
            edited_name = st.session_state.get(f"edit_name_{customer_id}", customer.get("name", customer_id)).strip()
            
            updated_customer = {
                "id": customer_id,
                "name": edited_name or customer_id,
                "addresses": edited_addresses,
                "warehouses": selected_warehouses,
            }
            
            # Fresh catalog load before saving
            catalog = load_catalog()
            catalog = save_customer(catalog, updated_customer)
            save_catalog(catalog)
            
            # Clear temp flags
            st.session_state[key_prefix + "new_addr_count"] = 0
            for k in list(st.session_state.keys()):
                if str(k).startswith(key_prefix + "new_addr_line_"):
                    del st.session_state[k]
            
            st.session_state.edit_success = True
            st.toast("Customer saved", icon="✅")
            st.rerun()
        
        if st.session_state.edit_success:
            st.success("✅ Customer saved successfully")
            warning = get_last_warning()
            if warning:
                st.info(warning)
            st.session_state.edit_success = False
        
        # Handle delete (direct, no confirmation popup)
        if delete_clicked:
            catalog = load_catalog()
            catalog = delete_customer(catalog, customer_id)
            save_catalog(catalog)
            
            # Clear all customer-related session state
            for k in list(st.session_state.keys()):
                if (
                    str(k).startswith(f"ed_{customer_id}_")
                    or k == "selected_customer_cid"
                    or k == "edit_customer_choices_hash"
                    or k == "last_edited_cid"
                ):
                    del st.session_state[k]
            
            st.toast("Customer deleted", icon="🗑️")
            st.success(f"🗑️ Customer **{customer_id}** deleted successfully")
            st.rerun()