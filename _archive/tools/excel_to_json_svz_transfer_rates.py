# tools/svz_rates_excel_to_json.py
"""
Convert 'data/svz_truck_rates.xlsx' to 'data/svz_truck_rates.json'.

Expected: a simple table mapping pallets(1..66) -> truck_cost(€).
Column detection:
- If columns named 'pallets' and 'truck_cost' exist (case-insensitive), use them.
- Else use the first two columns as (pallets, truck_cost).

Output JSON format (list of dicts):
[
  {"pallets": 1, "truck_cost": 120.0},
  ...
]
"""

import json
from pathlib import Path
import pandas as pd

INPUT_XLSX = Path("data/svz_truck_rates.xlsx")
OUTPUT_JSON = Path("data/svz_truck_rates.json")

def detect_columns(df):
    cols_lower = {c.lower(): c for c in df.columns if isinstance(c, str)}
    if "pallets" in cols_lower and "truck_cost" in cols_lower:
        return cols_lower["pallets"], cols_lower["truck_cost"]
    # fallback: first two columns
    return df.columns[0], df.columns[1]

def main():
    if not INPUT_XLSX.exists():
        raise FileNotFoundError(f"Missing: {INPUT_XLSX}")

    # Read first sheet; requires openpyxl
    df = pd.read_excel(INPUT_XLSX, engine="openpyxl")
    pallets_col, cost_col = detect_columns(df)

    slim = df[[pallets_col, cost_col]].dropna()
    slim.columns = ["pallets", "truck_cost"]

    items = []
    for _, row in slim.iterrows():
        try:
            p = int(row["pallets"])
            c = float(row["truck_cost"])
        except Exception:
            continue
        if 1 <= p <= 66 and c >= 0:
            items.append((p, c))

    latest = {}
    for p, c in items:
        latest[p] = c

    out = [{"pallets": p, "truck_cost": float(latest[p])} for p in sorted(latest.keys())]

    OUTPUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {len(out)} rows -> {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
