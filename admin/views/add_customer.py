# admin/pages/add_customer.py
from __future__ import annotations
from typing import List, Dict, Any, Tuple, Optional
import streamlit as st
import sys, importlib.util
from pathlib import Path

# ------------------------------------------------------------
# Load services/config_manager without altering sys.path
# ------------------------------------------------------------
_root = Path(__file__).resolve().parents[2]
_cm_path = _root / "services" / "config_manager.py"
_spec = importlib.util.spec_from_file_location("services.config_manager", _cm_path)
_cm = importlib.util.module_from_spec(_spec)
sys.modules["services.config_manager"] = _cm
_spec.loader.exec_module(_cm)

load_catalog = _cm.load_catalog
save_catalog = _cm.save_catalog
cm_add_customer = _cm.add_customer
list_warehouse_ids = _cm.list_warehouse_ids  # for WH linking

# ----------------------------- helpers -----------------------------
def _get_customers(catalog: Dict[str, Any]):
    return catalog.get("customers")

def _set_customers(catalog: Dict[str, Any], customers):
    catalog["customers"] = customers
    return catalog

def _customers_to_choices(customers) -> List[Tuple[str, str]]:
    choices: List[Tuple[str, str]] = []
    if isinstance(customers, dict):
        for cid, obj in customers.items():
            name = (obj or {}).get("name", str(cid))
            choices.append((str(cid), f"{cid} — {name}"))
    elif isinstance(customers, list):
        for obj in customers:
            if isinstance(obj, dict):
                cid = str(obj.get("id") or obj.get("cid") or obj.get("code") or obj.get("name") or "")
                if cid:
                    name = obj.get("name", cid)
                    choices.append((cid, f"{cid} — {name}"))
    return sorted(choices, key=lambda x: x[1].lower())

def _get_customer_by_id(catalog: Dict[str, Any], cid: str) -> Optional[Dict[str, Any]]:
    customers = _get_customers(catalog)
    if isinstance(customers, dict):
        obj = customers.get(cid)
        if isinstance(obj, dict):
            # normalize return with id
            return {"id": cid, **obj}
    elif isinstance(customers, list):
        for obj in customers:
            if isinstance(obj, dict):
                oid = str(obj.get("id") or obj.get("cid") or obj.get("code") or obj.get("name") or "")
                if oid == cid:
                    return obj
    return None

def _save_customer_obj(catalog: Dict[str, Any], obj: Dict[str, Any]) -> Dict[str, Any]:
    """Upsert customer obj by id. Supports dict or list storage."""
    cid = str(obj.get("id"))
    customers = _get_customers(catalog)

    if customers is None:
        customers = {cid: {k: v for k, v in obj.items() if k != "id"}}
        return _set_customers(catalog, customers)

    if isinstance(customers, dict):
        customers[cid] = {k: v for k, v in obj.items() if k != "id"}
        return catalog

    if isinstance(customers, list):
        replaced = False
        for i, it in enumerate(customers):
            if isinstance(it, dict):
                oid = str(it.get("id") or it.get("cid") or it.get("code") or it.get("name") or "")
                if oid == cid:
                    customers[i] = obj
                    replaced = True
                    break
        if not replaced:
            customers.append(obj)
        return catalog

    # unexpected -> reset to dict
    return _set_customers(catalog, {cid: {k: v for k, v in obj.items() if k != "id"}})

def _delete_customer_by_id(catalog: Dict[str, Any], cid: str) -> Dict[str, Any]:
    customers = _get_customers(catalog)
    if isinstance(customers, dict):
        customers.pop(cid, None)
        return catalog
    if isinstance(customers, list):
        customers[:] = [
            it for it in customers
            if not (isinstance(it, dict) and str(it.get("id") or it.get("cid") or it.get("code") or it.get("name") or "") == cid)
        ]
        return catalog
    return catalog

# ----------------------------- UI -----------------------------
def page_add_customer():
    st.title("Admin • Customers")

    # Kalıcı başarı mesajı için session bayrakları (flicker engel)
    ss = st.session_state
    ss.setdefault("create_success_cid", "")
    ss.setdefault("edit_success", False)
    ss.setdefault("delete_success", False)

    tab_create, tab_edit = st.tabs(["➕ Create Customer", "📝 Edit / Delete Customer"])

    # ------------------------- CREATE -------------------------
    with tab_create:
        catalog = load_catalog()

        with st.form("create_customer_form", clear_on_submit=False):
            name = st.text_input("Customer name", key="new_name", placeholder="e.g., ACME BV")

            # address inputs (dinamik)
            ss.setdefault("new_addr_count", 1)
            col_a, col_b = st.columns([1, 1])
            add_addr = col_a.form_submit_button("Add another address")
            reset_addr = col_b.form_submit_button("Reset addresses")
            if add_addr:
                ss.new_addr_count += 1
            if reset_addr:
                ss.new_addr_count = 1
                # form alanlarını temizleyelim
                for k in list(ss.keys()):
                    if str(k).startswith("new_addr_"):
                        del ss[k]

            addresses: List[str] = []
            for i in range(ss.new_addr_count):
                addr = st.text_input(
                    f"Address #{i+1}",
                    key=f"new_addr_{i}",
                    placeholder="Main St 10, 1011AB Amsterdam, NL",
                )
                addresses.append((addr or "").strip())

            submitted = st.form_submit_button("Create customer", type="primary")

        if submitted:
            if not (name and name.strip()):
                st.error("Name required.")
            else:
                addresses_clean = [a for a in addresses if a]
                if not addresses_clean:
                    st.error("Please enter at least one address line.")
                else:
                    catalog, cid = cm_add_customer(catalog, {"name": name.strip(), "addresses": addresses_clean})
                    save_catalog(catalog)
                    ss.create_success_cid = cid
                    st.toast("Customer created", icon="✅")

        # kalıcı success alanı (form dışı, flicker yapmaz)
        if ss.create_success_cid:
            st.success(f"✅ Customer saved (ID: {ss.create_success_cid})")

    # ------------------------- EDIT / DELETE -------------------------
    with tab_edit:
        catalog = load_catalog()
        customers = _get_customers(catalog)
        choices = _customers_to_choices(customers)

        if not choices:
            st.info("No customers yet. Create one in the first tab.")
            return

        cid = st.selectbox(
            "Select customer",
            options=[c[0] for c in choices],
            format_func=lambda v: dict(choices).get(v, v),
            key="selected_customer_cid"
        )

        cust = _get_customer_by_id(catalog, cid)
        if not cust:
            st.error("Customer not found (maybe deleted).")
            return

        with st.form("edit_customer_form", clear_on_submit=False):
            st.subheader("Customer Information")

            # name
            name = st.text_input("Name", value=cust.get("name", cid), key="edit_name")

            # addresses (edit + delete)
            st.markdown("**Addresses**")
            addrs: List[str] = list(map(str, cust.get("addresses", [])))

            # silme checkbox state’leri
            # (form içinde de stabil kalsın diye uzun anahtarlar kullanıyoruz)
            key_prefix = f"ed_{cid}_"
            ss.setdefault(key_prefix + "addr_del_flags", [False] * len(addrs))
            if len(ss[key_prefix + "addr_del_flags"]) != len(addrs):
                ss[key_prefix + "addr_del_flags"] = [False] * len(addrs)

            for i, a in enumerate(addrs):
                cols = st.columns([8, 2])
                cols[0].text_input(f"Address #{i+1}", value=a, key=f"{key_prefix}addr_{i}")
                ss[key_prefix + "addr_del_flags"][i] = cols[1].checkbox(
                    "Delete", key=f"{key_prefix}del_{i}", value=ss[key_prefix + "addr_del_flags"][i]
                )

            # new address lines
            ss.setdefault(key_prefix + "new_addr_count", 0)
            if st.form_submit_button("Add another address line"):
                ss[key_prefix + "new_addr_count"] += 1

            new_lines: List[str] = []
            for i in range(ss[key_prefix + "new_addr_count"]):
                v = st.text_input(
                    f"New address #{i+1}",
                    key=f"{key_prefix}new_addr_line_{i}",
                    placeholder="e.g., Warehouselaan 5, 3542XX Utrecht, NL",
                )
                if v:
                    new_lines.append(v.strip())

            # ---------- warehouses (WH) linking ----------
            st.markdown("**Linked Warehouses**")
            all_wids = list_warehouse_ids(catalog)  # ["netherlands_svz", ...]
            current_whs: List[str] = list(map(str, cust.get("warehouses", [])))
            selected_whs = st.multiselect(
                "Select warehouses for this customer",
                options=all_wids,
                default=current_whs,
                help="These warehouses will be associated with the selected customer."
            )

            col_save, col_delete = st.columns([1, 1])
            save_clicked = col_save.form_submit_button("Save changes", type="primary")
            delete_clicked = col_delete.form_submit_button("Delete customer")

        # --------- edit result handling (form dışı kalıcı mesajlar) ---------
        if save_clicked:
            edited_addrs: List[str] = []
            for i in range(len(addrs)):
                if not ss[key_prefix + "addr_del_flags"][i]:
                    edited_val = st.session_state.get(f"{key_prefix}addr_{i}", addrs[i]).strip()
                    if edited_val:
                        edited_addrs.append(edited_val)
            for nl in new_lines:
                if nl:
                    edited_addrs.append(nl)

            updated = {
                "id": cid,
                "name": (st.session_state.get("edit_name") or "").strip() or cid,
                "addresses": edited_addrs,
                "warehouses": selected_whs,  # NEW: link warehouses
            }
            catalog = _save_customer_obj(catalog, updated)
            save_catalog(catalog)
            ss.edit_success = True
            st.toast("Customer saved", icon="✅")

            # yeni adres satırı sayaçlarını sıfırla
            ss[key_prefix + "new_addr_count"] = 0
            # geçici yeni adres alanlarını temizle
            for k in list(ss.keys()):
                if str(k).startswith(key_prefix + "new_addr_line_"):
                    del ss[k]

        if ss.edit_success:
            st.success("✅ Customer saved")

        if delete_clicked:
            with st.popover("Confirm deletion"):
                st.warning(f"Delete **{cid}** permanently?")
                confirm = st.checkbox("I understand, delete this customer.")
                really = st.button("Confirm delete", type="primary", disabled=not confirm)
                if really:
                    catalog = load_catalog()
                    catalog = _delete_customer_by_id(catalog, cid)
                    save_catalog(catalog)
                    ss.delete_success = True
                    st.toast("Customer deleted", icon="🗑️")
                    st.success("🗑️ Customer deleted")
                    st.experimental_rerun()
