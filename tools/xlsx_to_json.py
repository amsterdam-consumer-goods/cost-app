"""
Customer Excel to JSON Converter
=================================

Converts customer data from Excel to JSON format for catalog.

Input:
- data/customers.xlsx
  - Column 1: Customer name
  - Columns 2+: Customer addresses

Output:
- data/customers.json
  - Format: [{"name": "...", "addresses": ["...", "..."]}, ...]

Usage:
    python tools/xlsx_to_json.py

Requirements:
    pip install pandas openpyxl

Related Files:
- data/customers.xlsx: Source Excel file
- data/customers.json: Output JSON file
- services/repositories/customer_repository.py: Uses this data
"""

from __future__ import annotations
import json
from pathlib import Path
import pandas as pd


# ============================================================================
# CONFIGURATION
# ============================================================================

XLSX_PATH = Path("data/customers.xlsx")
JSON_PATH = Path("data/customers.json")


# ============================================================================
# CONVERTER
# ============================================================================

def excel_to_json(xlsx_path: Path, json_path: Path) -> None:
    """
    Convert customer Excel to JSON format.
    
    Process:
    1. Read Excel file (first sheet)
    2. Extract customer names from column 1
    3. Extract addresses from remaining columns
    4. Deduplicate addresses per customer
    5. Write JSON output
    
    Args:
        xlsx_path: Path to input Excel file
        json_path: Path to output JSON file
        
    Raises:
        FileNotFoundError: If Excel file doesn't exist
        ValueError: If Excel format is invalid
    """
    # Read Excel
    df = pd.read_excel(xlsx_path, engine="openpyxl")
    
    customers = []
    
    # Process each row
    for _, row in df.iterrows():
        # Column 1: Customer name
        name = str(row.iloc[0]).strip()
        
        # Skip empty names
        if not name or name.lower() == "nan":
            continue
        
        # Columns 2+: Addresses
        addresses = []
        seen = set()
        
        for value in row.iloc[1:].tolist():
            # Skip empty values
            if pd.isna(value):
                continue
            
            address = str(value).strip()
            
            # Skip empty or duplicate addresses
            if not address or address in seen:
                continue
            
            seen.add(address)
            addresses.append(address)
        
        # Add customer
        customers.append({
            "name": name,
            "addresses": addresses
        })
    
    # Write JSON
    json_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(customers, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Converted {len(customers)} customers")
    print(f"   Output: {json_path} ({json_path.stat().st_size} bytes)")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run converter."""
    if not XLSX_PATH.exists():
        print(f"❌ Input file not found: {XLSX_PATH}")
        return
    
    excel_to_json(XLSX_PATH, JSON_PATH)


if __name__ == "__main__":
    main()