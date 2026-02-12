"""
Storage Manager
===============

Orchestrates GitHub Gist and local file storage with fallback strategy.

This module provides:
- Load catalog (Gist → Local fallback)
- Save catalog (Gist + Local)
- Warning message tracking
- Path and modification time access

Strategy:
- PRIMARY: GitHub Gist (cloud sync)
- FALLBACK: Local file (cache)

Load Priority:
1. Try Gist first (if configured)
2. On success: cache to local, return
3. On failure: fall back to local cache

Save Priority:
1. Save to Gist (if configured)
2. Always save to local (as cache)
3. Continue even if Gist fails

Related Files:
- services/storage/gist_storage.py: GitHub Gist API
- services/storage/local_storage.py: Local file operations
- services/config_manager.py: Public API facade
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, Optional

from .gist_storage import GistStorage, GistError
from .local_storage import LocalStorage


class StorageManager:
    """
    Coordinates GitHub Gist and local storage with fallback logic.
    
    Architecture:
    - Gist: Primary cloud storage (optional)
    - Local: Cache and fallback (always available)
    
    Features:
    - Automatic fallback on Gist failures
    - Warning message tracking for UI
    - Configurable local path
    - Session-level Gist disabling
    """
    
    def __init__(self, local_path: Optional[Path] = None):
        """
        Initialize storage manager.
        
        Args:
            local_path: Path to local catalog file
                       If None, uses CATALOG_PATH env or default
        """
        self.local_path = local_path or self._get_default_path()
        self.gist = GistStorage()
        self.local = LocalStorage(self.local_path)
        self._last_warning: Optional[str] = None
    
    @staticmethod
    def _get_default_path() -> Path:
        """
        Get default catalog path.
        
        Priority:
        1. CATALOG_PATH environment variable
        2. Default: project_root/data/catalog.json
        
        Returns:
            Resolved Path to catalog file
        """
        # Check environment variable
        env_path = os.environ.get("CATALOG_PATH")
        if env_path:
            return Path(env_path).expanduser().resolve()
        
        # Default path: project_root/data/catalog.json
        project_root = Path(__file__).resolve().parents[2]
        return (project_root / "data" / "catalog.json").resolve()
    
    def get_last_warning(self) -> Optional[str]:
        """
        Get last warning message.
        
        Used by UI to display Gist sync issues to users.
        
        Returns:
            Warning message or None
        """
        return self._last_warning
    
    def _set_warning(self, message: str) -> None:
        """
        Set warning message for UI display.
        
        Args:
            message: Warning message
        """
        self._last_warning = message
    
    def load(self) -> Dict[str, Any]:
        """
        Load catalog with Gist-first fallback strategy.
        
        Strategy:
        1. Try Gist (primary source)
           - On success: cache to local and return
           - On failure: set warning, disable Gist, continue to step 2
        2. Load from local cache
        3. If both empty and Gist available: initialize empty Gist
        
        Returns:
            Catalog dict with 'warehouses' and 'customers' keys
            
        Note:
            Never fails - always returns at least empty catalog structure
        """
        # STEP 1: Try Gist first (primary source)
        if self.gist.is_available():
            try:
                data = self.gist.load()
                
                # Cache to local for faster subsequent reads
                self.local.save(data)
                
                # Clear any previous warnings
                self._last_warning = None
                
                return data
                
            except GistError as e:
                # Gist failed - disable and fall back
                self.gist.disable()
                self._set_warning(f"Cloud storage unavailable: {e}. Using local cache.")
                
            except Exception as e:
                # Unexpected error - disable and fall back
                self.gist.disable()
                self._set_warning(f"Unexpected error loading from cloud: {e}. Using local cache.")
        
        # STEP 2: Fallback to local cache
        data = self.local.load()
        
        # STEP 3: Initialize Gist if both are empty
        if not data.get("warehouses") and not data.get("customers"):
            if self.gist.is_available():
                try:
                    empty_catalog = {"warehouses": [], "customers": []}
                    self.gist.save(empty_catalog)
                except Exception:
                    # Initialization failed - not critical
                    pass
        
        return data
    
    def save(self, data: Dict[str, Any]) -> Path:
        """
        Save catalog to both Gist and local storage.
        
        Strategy:
        1. Save to Gist first (primary)
           - On success: clear warnings
           - On failure: set warning, disable Gist, continue
        2. Always save to local (cache)
        3. Return local path
        
        Args:
            data: Catalog dict with 'warehouses' and 'customers'
            
        Returns:
            Path to local file
            
        Note:
            Always succeeds - local save never fails unless disk is full
        """
        # STEP 1: Save to Gist first (primary storage)
        if self.gist.is_available():
            try:
                self.gist.save(data)
                
                # Clear any previous warnings
                self._last_warning = None
                
            except GistError as e:
                # Gist failed - disable and warn
                self.gist.disable()
                self._set_warning(f"Cloud storage sync failed: {e}. Data saved locally only.")
                
            except Exception as e:
                # Unexpected error - disable and warn
                self.gist.disable()
                self._set_warning(f"Cloud storage error: {e}. Data saved locally only.")
        
        # STEP 2: Always save to local as cache
        local_path = self.local.save(data)
        
        return local_path
    
    def get_path(self) -> Path:
        """
        Get path to local catalog file.
        
        Returns:
            Path to catalog.json
        """
        return self.local_path
    
    def get_mtime(self) -> str:
        """
        Get last modification time of local catalog.
        
        Returns:
            Formatted timestamp string
        """
        return self.local.get_mtime()