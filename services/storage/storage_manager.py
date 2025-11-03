"""
Storage Manager - Orchestrates Gist and Local storage.
Implements fallback strategy: Gist (primary) → Local (cache).
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, Optional

from .gist_storage import GistStorage, GistError
from .local_storage import LocalStorage


class StorageManager:
    """Coordinates Gist and Local storage with fallback logic."""
    
    def __init__(self, local_path: Optional[Path] = None):
        """
        Initialize storage manager.
        
        Args:
            local_path: Path to local catalog file. If None, uses default.
        """
        self.local_path = local_path or self._get_default_path()
        self.gist = GistStorage()
        self.local = LocalStorage(self.local_path)
        self._last_warning: Optional[str] = None
    
    @staticmethod
    def _get_default_path() -> Path:
        """Get default catalog path from environment or fallback."""
        env_path = os.environ.get("CATALOG_PATH")
        if env_path:
            return Path(env_path).expanduser().resolve()
        
        # Default: project_root/data/catalog.json
        project_root = Path(__file__).resolve().parents[2]
        return (project_root / "data" / "catalog.json").resolve()
    
    def get_last_warning(self) -> Optional[str]:
        """Get last warning message (for UI display)."""
        return self._last_warning
    
    def _set_warning(self, message: str) -> None:
        """Set warning message."""
        self._last_warning = message
    
    def load(self) -> Dict[str, Any]:
        """
        Load catalog with Gist-first fallback strategy.
        
        Strategy:
        1. Try Gist (primary source)
        2. On success: cache to local and return
        3. On failure: fall back to local cache
        
        Returns:
            Catalog dict with 'warehouses' and 'customers'
        """
        # STEP 1: Try Gist first (primary source)
        if self.gist.is_available():
            try:
                data = self.gist.load()
                # Cache to local for faster subsequent reads
                self.local.save(data)
                self._last_warning = None
                return data
            except GistError as e:
                self.gist.disable()
                self._set_warning(f"Cloud storage unavailable: {e}. Using local cache.")
            except Exception as e:
                self.gist.disable()
                self._set_warning(f"Unexpected error loading from cloud: {e}. Using local cache.")
        
        # STEP 2: Fallback to local cache
        data = self.local.load()
        
        # STEP 3: If local is empty and Gist available, try to initialize Gist
        if not data.get("warehouses") and not data.get("customers"):
            if self.gist.is_available():
                try:
                    empty_catalog = {"warehouses": [], "customers": []}
                    self.gist.save(empty_catalog)
                except Exception:
                    pass
        
        return data
    
    def save(self, data: Dict[str, Any]) -> Path:
        """
        Save catalog to both Gist and Local.
        
        Strategy:
        1. Save to Gist first (primary)
        2. Always save to Local (cache)
        3. Warnings if Gist fails, but operation continues
        
        Args:
            data: Catalog dict with 'warehouses' and 'customers'
            
        Returns:
            Path to local file
        """
        # STEP 1: Save to Gist first (primary storage)
        if self.gist.is_available():
            try:
                self.gist.save(data)
                self._last_warning = None
            except GistError as e:
                self.gist.disable()
                self._set_warning(f"Cloud storage sync failed: {e}. Data saved locally only.")
            except Exception as e:
                self.gist.disable()
                self._set_warning(f"Cloud storage error: {e}. Data saved locally only.")
        
        # STEP 2: Always save to local as cache
        local_path = self.local.save(data)
        
        return local_path
    
    def get_path(self) -> Path:
        """Get path to local catalog file."""
        return self.local_path
    
    def get_mtime(self) -> str:
        """Get last modification time of local catalog."""
        return self.local.get_mtime()