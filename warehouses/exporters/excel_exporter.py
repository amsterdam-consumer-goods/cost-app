"""Excel export functionality."""

from __future__ import annotations
from io import BytesIO
from datetime import datetime
from typing import List, Tuple, Any
import streamlit as st


def export_to_excel(
    export_rows: List[Tuple[str, Any]],
    warehouse_title: str
) -> None:
    """Render Excel download button."""
    try:
        import pandas as pd
    except ImportError:
        st.caption("Install pandas for Excel export.")
        return
    
    buf = BytesIO()
    now = datetime.now()
    calc_id = now.strftime("%Y%m%d-%H%M%S")
    primary_for_file = warehouse_title.replace(" / ", "_").replace(" ", "_").lower()
    
    bd_rows = [
        {"Item": k, "Value": ("" if v in (None, "") else v)}
        for k, v in export_rows
    ]
    
    with pd.ExcelWriter(buf, engine="xlsxwriter") as xw:
        df = pd.DataFrame(bd_rows)
        df.to_excel(xw, index=False, sheet_name="VVP")
        ws = xw.sheets["VVP"]
        ws.set_column(0, 0, 42)
        ws.set_column(1, 1, 22)
    
    st.download_button(
        "Download Excel",
        data=buf.getvalue(),
        file_name=f"vvp_{primary_for_file}_{calc_id}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )