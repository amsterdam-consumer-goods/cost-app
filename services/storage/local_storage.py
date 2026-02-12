"""
Local File Storage Implementation
==================================

Handles catalog persistence to local JSON files.

This module provides:
- Read catalog from local JSON file
- Write catalog to local JSON file (atomic)
- File existence checks
- Modification time tracking
- UTF-8 encoding handling

Features:
- Atomic writes (temp file + rename)
- Directory creation if needed
- Graceful handling of missing/corrupt files
- fsync for data durability

Related Files:
- services/storage/storage_manager.py: Orchestrates Gist + Local
- services/storage/gist_storage.py: Cloud backup
- data/catalog.json: Default storage location
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict


class LocalStorage:
    """
    Handles local file operations for catalog.
    
    Features:
    - UTF-8 encoding (handles special characters)
    - Atomic writes (prevents data corruption)
    - Automatic directory creation
    - Graceful error handling
    """
    
    def __init__(self, file_path: Path):
        """
        Initialize local storage.
        
        Args:
            file_path: Path to catalog JSON file
        """
        self.file_path = file_path
    
    def exists(self) -> bool:
        """
        Check if catalog file exists.
        
        Returns:
            True if file exists, False otherwise
        """
        return self.file_path.exists()
    
    def load(self) -> Dict[str, Any]:
        """
        Load catalog from local file.
        
        Process:
        1. Check if file exists
        2. Read file with UTF-8 encoding
        3. Parse JSON
        4. Ensure required keys exist
        
        Returns:
            Dict with 'warehouses' and 'customers' keys
            Returns empty structure if file doesn't exist or is invalid
            
        Note:
            Does not raise exceptions - returns empty catalog on errors
        """
        # File doesn't exist
        if not self.file_path.exists():
            return {"warehouses": [], "customers": []}
        
        # Read and parse file
        try:
            with self.file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            # Invalid JSON - return empty
            return {"warehouses": [], "customers": []}
        except Exception:
            # Other errors (permissions, etc) - return empty
            return {"warehouses": [], "customers": []}
        
        # Ensure required keys exist
        data.setdefault("warehouses", [])
        data.setdefault("customers", [])
        
        return data
    
    def save(self, data: Dict[str, Any]) -> Path:
        """
        Save catalog to local file with atomic write.
        
        Atomic Write Process:
        1. Create parent directory if needed
        2. Write to temporary file (.json.tmp)
        3. Flush and fsync (ensure data on disk)
        4. Rename temp file to target (atomic operation)
        5. Verify file exists
        
        This ensures the file is never left in a corrupt state,
        even if power fails during write.
        
        Args:
            data: Catalog dict with 'warehouses' and 'customers'
            
        Returns:
            Path to saved file
            
        Raises:
            IOError: If write fails or verification fails
        """
        # Ensure parent directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to temporary file first (atomic write pattern)
        tmp_path = self.file_path.with_suffix(".json.tmp")
        
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk
        
        # Atomically replace original file
        # This is atomic on POSIX and Windows
        os.replace(tmp_path, self.file_path)
        
        # Verify file was written
        if not self.file_path.exists():
            raise IOError(f"Failed to write catalog to {self.file_path}")
        
        return self.file_path
    
    def get_mtime(self) -> str:
        """
        Get last modification time as formatted string.
        
        Returns:
            Formatted timestamp (YYYY-MM-DD HH:MM:SS)
            Returns '(not created yet)' if file doesn't exist
        """
        if not self.file_path.exists():
            return "(not created yet)"
        
        from datetime import datetime
        
        timestamp = datetime.fromtimestamp(self.file_path.stat().st_mtime)
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")