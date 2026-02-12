"""
SVZ Truck Rates Excel to JSON Converter
========================================

Converts SVZ truck rate table from Excel to JSON format.

Input:
- data/svz_truck_rates.xlsx
  - Columns: "pallets" and "truck_cost" (case-insensitive)
  - Or: First two columns as (pallets, cost)
  - Range: 1-66 pallets

Output:
- data/svz_truck_rates.json
  - Format: [{"pallets": 1, "truck_cost": 120.0}, ...]

Usage:
    python tools/svz_rates_excel_to_json.py

Requirements:
    pip install pandas openpyxl

Related Files:
- data/svz_truck_rates.xlsx: Source Excel file
- data/svz_truck_rates.json: Output JSON file
- warehouses/calculators/vvp_calculator.py: Uses this data
"""

from __future__ import annotations
import json
from pathlib import Path
import pandas as pd


# ============================================================================
# CONFIGURATION
# ============================================================================

INPUT_XLSX = Path("data/svz_truck_rates.xlsx")
OUTPUT_JSON = Path("data/svz_truck_rates.json")


# ============================================================================
# COLUMN DETECTION
# ============================================================================

def detect_columns(df: pd.DataFrame) -> tuple[str, str]:
    """
    Detect pallet and cost columns.
    
    Strategy:
    1. Look for columns named "pallets" and "truck_cost" (case-insensitive)
    2. Fallback: Use first two columns
    
    Args:
        df: DataFrame
        
    Returns:
        Tuple of (pallets_column, cost_column)
    """
    # Build lowercase column map
    cols_lower = {c.lower(): c for c in df.columns if isinstance(c, str)}
    
    # Check for named columns
    if "pallets" in cols_lower and "truck_cost" in cols_lower:
        return cols_lower["pallets"], cols_lower["truck_cost"]
    
    # Fallback: First two columns
    return df.columns[0], df.columns[1]


# ============================================================================
# CONVERTER
# ============================================================================

def convert_rates() -> None:
    """
    Convert SVZ truck rates Excel to JSON.
    
    Process:
    1. Read Excel file
    2. Detect pallets and cost columns
    3. Filter valid rows (1-66 pallets, cost >= 0)
    4. Deduplicate (keep latest value per pallet count)
    5. Write sorted JSON
    
    Raises:
        FileNotFoundError: If Excel file doesn't exist
    """
    # Validate input
    if not INPUT_XLSX.exists():
        raise FileNotFoundError(f"Missing: {INPUT_XLSX}")
    
    # Read Excel
    df = pd.read_excel(INPUT_XLSX, engine="openpyxl")
    
    # Detect columns
    pallets_col, cost_col = detect_columns(df)
    
    # Extract relevant columns and drop NaN
    slim = df[[pallets_col, cost_col]].dropna()
    slim.columns = ["pallets", "truck_cost"]
    
    # Parse and validate rows
    items = []
    
    for _, row in slim.iterrows():
        try:
            pallet_count = int(row["pallets"])
            truck_cost = float(row["truck_cost"])
        except (ValueError, TypeError):
            continue
        
        # Validate range
        if 1 <= pallet_count <= 66 and truck_cost >= 0:
            items.append((pallet_count, truck_cost))
    
    # Deduplicate (keep latest)
    latest = {}
    for pallet_count, truck_cost in items:
        latest[pallet_count] = truck_cost
    
    # Build output (sorted by pallet count)
    output = [
        {"pallets": p, "truck_cost": float(latest[p])}
        for p in sorted(latest.keys())
    ]
    
    # Write JSON
    OUTPUT_JSON.write_text(
        json.dumps(output, indent=2),
        encoding="utf-8"
    )
    
    print(f"✅ Converted {len(output)} rates")
    print(f"   Range: {output[0]['pallets']}-{output[-1]['pallets']} pallets")
    print(f"   Output: {OUTPUT_JSON}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run converter."""
    try:
        convert_rates()
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()