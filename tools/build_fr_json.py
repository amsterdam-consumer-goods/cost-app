"""
France Delivery Rates Excel to JSON Converter
==============================================

Converts French delivery rate table from Excel to normalized JSON format.

Input:
- data/fr_delivery_rates.xlsx
  - Sheet: "rates" (or first sheet)
  - Row 2: Department codes (01-95)
  - Column A (from row 5): Pallet counts
  - Matrix: Delivery costs (€)

Output:
- data/fr_delivery_rates.json
  - Format: [{"dept": "01", "pallets": 1, "total": 120.50}, ...]

Usage:
    python tools/build_fr_json.py

Requirements:
    pip install pandas openpyxl

Related Files:
- data/fr_delivery_rates.xlsx: Source Excel file
- data/fr_delivery_rates.json: Output JSON file
- warehouses/calculators/france_delivery.py: Uses this data
"""

from __future__ import annotations
import json
from pathlib import Path
import pandas as pd


# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
EXCEL_PATH = DATA_DIR / "fr_delivery_rates.xlsx"
JSON_PATH = DATA_DIR / "fr_delivery_rates.json"


# ============================================================================
# PARSER HELPERS
# ============================================================================

def _parse_pallet_label(value) -> int | None:
    """
    Parse pallet count from label.
    
    Handles:
    - Numeric values: "1", "10", "33"
    - Text labels: "complete truck", "full truck" → 33
    
    Args:
        value: Cell value
        
    Returns:
        Pallet count or None if invalid
    """
    text = str(value).strip().lower()
    
    # Try direct integer conversion
    try:
        return int(text)
    except ValueError:
        pass
    
    # Check for full truck labels
    if "comp" in text or "full" in text:
        return 33
    
    return None


# ============================================================================
# CONVERTER
# ============================================================================

def build_json() -> None:
    """
    Convert France delivery rates Excel to JSON.
    
    Process:
    1. Read Excel file
    2. Parse department codes from row 2
    3. Parse pallet counts from column A (starting row 5)
    4. Extract costs from matrix
    5. Write normalized JSON
    
    Raises:
        FileNotFoundError: If Excel file doesn't exist
        ValueError: If no valid data found
    """
    # Validate input
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"Excel not found: {EXCEL_PATH}")
    
    # Read Excel (no header)
    df = pd.read_excel(EXCEL_PATH, header=None)
    
    # Parse department codes from row 2 (index 1)
    dept_row = df.iloc[1, 1:]  # Skip first column
    departments: list[str | None] = []
    
    for value in dept_row:
        try:
            dept_num = int(str(value).strip())
            departments.append(f"{dept_num:02d}")  # Zero-pad (1 → "01")
        except ValueError:
            departments.append(None)
    
    # Parse pallet counts from column A (starting row 5, index 4)
    data_start_row = 4
    pallet_col = df.iloc[data_start_row:, 0]
    pallets: list[int | None] = []
    
    for value in pallet_col:
        pallets.append(_parse_pallet_label(value))
    
    # Extract cost matrix
    values = df.iloc[data_start_row:, 1:]  # Skip first column
    
    # Build normalized rows
    rows: list[dict] = []
    
    for i, pallet_count in enumerate(pallets):
        if pallet_count is None:
            continue
        
        for j, dept in enumerate(departments):
            if dept is None:
                continue
            
            # Get cost value
            cell_value = values.iat[i, j]
            
            if pd.isna(cell_value):
                continue
            
            # Parse cost (handle various formats)
            try:
                # Try cleaning text format: "€ 1.234,56" → 1234.56
                cost_str = str(cell_value)
                cost_str = cost_str.replace("€", "").replace("EUR", "").replace(" ", "")
                cost_str = cost_str.replace(".", "").replace(",", ".")
                total = float(cost_str)
            except ValueError:
                try:
                    # Try direct float conversion
                    total = float(cell_value)
                except ValueError:
                    continue
            
            # Add row
            rows.append({
                "dept": dept,
                "pallets": int(pallet_count),
                "total": float(total)
            })
    
    # Validate output
    if not rows:
        raise ValueError("No rows parsed from department × pallet matrix.")
    
    # Write JSON
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    
    # Print summary
    unique_depts = sorted({r["dept"] for r in rows})
    
    print(f"✅ Wrote {len(rows)} rows to: {JSON_PATH}")
    print(f"   Departments: {len(unique_depts)} ({unique_depts[0]}–{unique_depts[-1]})")
    
    # Print sample
    sample = next((r for r in rows if r["dept"] == "30" and r["pallets"] == 33), None)
    if sample:
        print(f"   Sample: dept 30, 33 pallets → €{sample['total']:.2f}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run converter."""
    try:
        build_json()
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()