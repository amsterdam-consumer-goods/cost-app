# admin/app.py
"""
Streamlit entrypoint for the Admin Panel.

Run from project root:
    streamlit run admin/app.py --server.port 8502 --server.address 127.0.0.1

Authentication:
- Use ADMIN_PASSWORD in .streamlit/secrets.toml
  or an environment variable ADMIN_PASSWORD.
"""

# Add project root to sys.path so "admin" and "services" imports resolve
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../cost-app
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import streamlit as st
from admin.views import admin_router  # keep import (mirrors original behavior)


def check_admin_password() -> bool:
    """Return True if admin is authenticated; otherwise show a login form."""
    secret_pw = st.secrets.get("ADMIN_PASSWORD", os.environ.get("ADMIN_PASSWORD"))
    if not secret_pw:
        return True

    if st.session_state.get("admin_auth_ok"):
        return True

    st.image("assets/logo2.png", width=190)
    st.title("🛠️ Admin Login")
    pw = st.text_input("Admin Password", type="password", placeholder="Enter admin password…")
    if st.button("Sign in"):
        st.session_state.admin_auth_ok = pw == str(secret_pw)
        if not st.session_state.admin_auth_ok:
            st.error("Incorrect password.")
        else:
            st.rerun()
    return False


st.set_page_config(page_title="Cost-App Admin", page_icon="🛠️", layout="wide")

st.markdown(
    """
<style>
/* Disable rounded corners on images */
.stImage img { border-radius: 0 !important; }
</style>
""",
    unsafe_allow_html=True,
)

# Auth gate
if not check_admin_password():
    st.stop()

# Router import (kept in try/except as in the original flow)
try:
    from admin.views import admin_router as _router  # noqa: F401
except Exception as e:
    st.exception(e)
    st.error(
        "Failed to import admin.views.admin_router.\n"
        "Ensure files exist: admin/__init__.py, admin/views/__init__.py, admin/views/*.py "
        "and launch Streamlit from the project root."
    )
    st.stop()

# Main Admin UI
st.image("assets/logo2.png", width=190)

hdr_c, hdr_r = st.columns([6, 1])
with hdr_c:
    st.title("🛠️ Admin Panel")
with hdr_r:
    if st.button("Log out"):
        st.session_state.pop("admin_auth_ok", None)
        st.rerun()

st.markdown("---")

choice = st.radio(
    "Choose an action",
    ["Update warehouse", "Add warehouse", "Add customer"],
    horizontal=True,
)

# Route
try:
    admin_router(choice)
except Exception as e:
    st.exception(e)
    st.error("admin_router(choice) raised an error. Please check admin/views/*.py.")
