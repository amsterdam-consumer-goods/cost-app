"""
GitHub Gist storage implementation.
Handles all Gist API interactions for catalog persistence.
"""

from __future__ import annotations
import json
import os
from typing import Any, Dict, Optional


class GistError(Exception):
    """Raised when Gist operations fail."""
    pass


class GistStorage:
    """Handles GitHub Gist API operations."""
    
    def __init__(
        self,
        gist_id: Optional[str] = None,
        token: Optional[str] = None,
        filename: str = "catalog.json"
    ):
        self.gist_id = gist_id or self._get_secret("GITHUB_GIST_ID")
        self.token = token or self._get_secret("GITHUB_TOKEN")
        self.filename = filename or self._get_secret("GITHUB_GIST_FILENAME") or "catalog.json"
        self._disabled = False
    
    @staticmethod
    def _get_secret(name: str) -> Optional[str]:
        """Get secret from environment or Streamlit secrets."""
        value = os.environ.get(name)
        if value:
            return value
        try:
            import streamlit as st
            return st.secrets.get(name)
        except Exception:
            return None
    
    def is_available(self) -> bool:
        """Check if Gist storage is configured and not disabled."""
        disable_flag = self._get_secret("DISABLE_GIST") or ""
        if disable_flag.strip() in ("1", "true", "True"):
            return False
        return bool(self.gist_id and self.token) and not self._disabled
    
    def disable(self) -> None:
        """Permanently disable Gist for this session (after auth error)."""
        self._disabled = True
    
    def _headers(self) -> Dict[str, str]:
        """Build headers for Gist API requests."""
        headers = {
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers
    
    def load(self) -> Dict[str, Any]:
        """
        Load catalog from Gist.
        
        Returns:
            Dict with 'warehouses' and 'customers' keys
            
        Raises:
            GistError: If fetch fails
        """
        import requests
        
        if not self.gist_id:
            raise GistError("Missing GIST_ID")
        
        url = f"https://api.github.com/gists/{self.gist_id}"
        
        try:
            response = requests.get(url, headers=self._headers(), timeout=15)
            
            if response.status_code in (401, 403, 404):
                raise GistError(
                    f"Gist fetch unauthorized/unavailable (HTTP {response.status_code})"
                )
            
            response.raise_for_status()
            
        except requests.RequestException as e:
            raise GistError(f"Gist fetch error: {e}")
        
        data = response.json()
        files = data.get("files", {})
        
        if self.filename not in files or "content" not in files[self.filename]:
            return {"warehouses": [], "customers": []}
        
        content = files[self.filename].get("content", "")
        if not content.strip():
            return {"warehouses": [], "customers": []}
        
        try:
            obj = json.loads(content)
        except json.JSONDecodeError:
            return {"warehouses": [], "customers": []}
        
        obj.setdefault("warehouses", [])
        obj.setdefault("customers", [])
        
        return obj
    
    def save(self, data: Dict[str, Any]) -> None:
        """
        Save catalog to Gist.
        
        Args:
            data: Catalog dict with 'warehouses' and 'customers'
            
        Raises:
            GistError: If save fails
        """
        import requests
        
        if not self.gist_id:
            raise GistError("Missing GIST_ID")
        
        url = f"https://api.github.com/gists/{self.gist_id}"
        
        body = {
            "files": {
                self.filename: {
                    "content": json.dumps(data, ensure_ascii=False, indent=2)
                }
            }
        }
        
        try:
            response = requests.patch(
                url,
                headers=self._headers(),
                data=json.dumps(body),
                timeout=15
            )
            
            if response.status_code in (401, 403):
                raise GistError(
                    f"Gist save unauthorized (HTTP {response.status_code})"
                )
            
            response.raise_for_status()
            
        except requests.RequestException as e:
            raise GistError(f"Gist save error: {e}")