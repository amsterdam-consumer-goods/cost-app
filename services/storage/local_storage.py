"""
Local file storage implementation.
Handles catalog persistence to local JSON files.
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict


class LocalStorage:
    """Handles local file operations for catalog."""
    
    def __init__(self, file_path: Path):
        """
        Initialize local storage.
        
        Args:
            file_path: Path to the catalog JSON file
        """
        self.file_path = file_path
    
    def exists(self) -> bool:
        """Check if catalog file exists."""
        return self.file_path.exists()
    
    def load(self) -> Dict[str, Any]:
        """
        Load catalog from local file.
        
        Returns:
            Dict with 'warehouses' and 'customers' keys
        """
        if not self.file_path.exists():
            return {"warehouses": [], "customers": []}
        
        try:
            with self.file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            return {"warehouses": [], "customers": []}
        except Exception:
            return {"warehouses": [], "customers": []}
        
        data.setdefault("warehouses", [])
        data.setdefault("customers", [])
        
        return data
    
    def save(self, data: Dict[str, Any]) -> Path:
        """
        Save catalog to local file with atomic write.
        
        Args:
            data: Catalog dict with 'warehouses' and 'customers'
            
        Returns:
            Path to saved file
            
        Raises:
            IOError: If write fails
        """
        # Ensure parent directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Atomic write: write to temp file first
        tmp_path = self.file_path.with_suffix(".json.tmp")
        
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        
        # Replace original file atomically
        os.replace(tmp_path, self.file_path)
        
        # Verify file was written
        if not self.file_path.exists():
            raise IOError(f"Failed to write catalog to {self.file_path}")
        
        return self.file_path
    
    def get_mtime(self) -> str:
        """
        Get last modification time as formatted string.
        
        Returns:
            Formatted timestamp or '(not created yet)'
        """
        if not self.file_path.exists():
            return "(not created yet)"
        
        from datetime import datetime
        timestamp = datetime.fromtimestamp(self.file_path.stat().st_mtime)
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")