"""Print/HTML export functionality."""

from __future__ import annotations
from datetime import datetime
from typing import List, Tuple, Any
import streamlit as st


def export_to_print(
    export_rows: List[Tuple[str, Any]],
    warehouse_title: str
) -> None:
    """Render print button with HTML popup."""
    if st.button("Print", use_container_width=True):
        html = _generate_print_html(export_rows, warehouse_title)
        st.components.v1.html(html, height=0)
        st.toast("Opening print dialog…", icon="🖨️")


def _generate_print_html(
    rows: List[Tuple[str, Any]],
    title: str
) -> str:
    """Generate HTML for printing."""
    rows_html = "".join(
        f"<tr><td>{k}</td><td style='text-align:right'>{'' if v in (None, '') else v}</td></tr>"
        for k, v in rows
    )
    
    return f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <title>VVP — {title}</title>
        <style>
          body {{ font-family: Arial, sans-serif; padding: 18px; }}
          h1 {{ font-size: 18px; margin: 0 0 6px; }}
          .meta {{ color:#666; font-size: 12px; margin-bottom: 10px; }}
          table {{ width:100%; border-collapse:collapse; }}
          th, td {{ border:1px solid #ddd; padding:6px 8px; font-size:12px; }}
          th {{ background:#f5f5f5; text-align:left; }}
          @media print {{ @page {{ size: A4 portrait; margin: 12mm; }} }}
        </style>
      </head>
      <body>
        <h1>VVP Calculator</h1>
        <div class="meta">{title} • {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
        <table>
          <thead><tr><th>Item</th><th>Value</th></tr></thead>
          <tbody>{rows_html}</tbody>
        </table>
        <script>window.onload = () => window.print();</script>
      </body>
    </html>
    """