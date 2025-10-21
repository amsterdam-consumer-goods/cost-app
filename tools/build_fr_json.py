# tools/build_fr_json.py
"""
Converts the French delivery rate Excel file (fr_delivery_rates.xlsx)
into a normalized JSON table (fr_delivery_rates.json).

Each row in the output represents a combination of:
- Department code (01–95)
- Number of pallets
- Total transport cost (€)
"""

from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
EXCEL_PATH = DATA_DIR / "fr_delivery_rates.xlsx"
JSON_PATH = DATA_DIR / "fr_delivery_rates.json"

def _parse_pallet_label(v):
    s = str(v).strip().lower()
    try:
        return int(s)
    except Exception:
        pass
    if s.startswith("comp") or "full" in s:
        return 33
    return None

def build_json():
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"Excel not found: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH, header=None)
    dept_row = df.iloc[1, 1:]
    depts: list[str | None] = []
    for v in dept_row:
        try:
            d = int(str(v).strip())
            depts.append(f"{d:02d}")
        except Exception:
            depts.append(None)
    data_start_row = 4
    pallets_col = df.iloc[data_start_row:, 0]
    pallets: list[int | None] = []
    for v in pallets_col:
        pallets.append(_parse_pallet_label(v))
    values = df.iloc[data_start_row:, 1:]
    rows: list[dict] = []
    for i, p in enumerate(pallets):
        if p is None:
            continue
        for j, d in enumerate(depts):
            if d is None:
                continue
            val = values.iat[i, j]
            if pd.isna(val):
                continue
            try:
                total = float(
                    str(val)
                    .replace("€", "")
                    .replace("EUR", "")
                    .replace(" ", "")
                    .replace(".", "")
                    .replace(",", ".")
                )
            except Exception:
                try:
                    total = float(val)
                except Exception:
                    continue
            rows.append({"dept": d, "pallets": int(p), "total": float(total)})
    if not rows:
        raise ValueError("No rows parsed from Zipcode × Pallets matrix.")
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    uniq_depts = sorted({r["dept"] for r in rows})
    print(f"✅ Wrote {len(rows)} rows to: {JSON_PATH}")
    print(f"   Depts found: {len(uniq_depts)} ({uniq_depts[0]}–{uniq_depts[-1]})")
    sample = next((r for r in rows if r["dept"] == "30" and r["pallets"] == 33), None)
    if sample:
        print(f"   Sample dept 30 / pallets 33 → €{sample['total']:.2f}")
    else:
        print("   Sample dept 30 / pallets 33 not found.")

if __name__ == "__main__":
    build_json()
