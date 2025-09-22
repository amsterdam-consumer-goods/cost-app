# tools/xlsx_to_json.py
import json
import pandas as pd
from pathlib import Path

XLSX_PATH = Path("data/customers.xlsx")
JSON_PATH = Path("data/customers.json")

def excel_to_json(xlsx_path: Path, json_path: Path):
    # İlk sayfa: 1. sütun "Name", diğer sütunlar adres.
    df = pd.read_excel(xlsx_path, engine="openpyxl")

    out = []
    for _, row in df.iterrows():
        name = str(row.iloc[0]).strip()
        if not name or name.lower() == "nan":
            continue

        addrs = []
        seen = set()
        for x in row.iloc[1:].tolist():
            if pd.isna(x):
                continue
            s = str(x).strip()
            if not s or s in seen:
                continue
            seen.add(s)
            addrs.append(s)

        out.append({"name": name, "addresses": addrs})

    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    excel_to_json(XLSX_PATH, JSON_PATH)
    print(f"✅ Wrote {JSON_PATH} ({JSON_PATH.stat().st_size} bytes)")
