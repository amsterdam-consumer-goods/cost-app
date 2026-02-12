"""
GitHub Gist Storage Implementation
===================================

Handles GitHub Gist API interactions for catalog cloud persistence.

This module provides:
- Read catalog from GitHub Gist
- Write catalog to GitHub Gist
- Automatic authentication via secrets
- Error handling and fallback signaling
- Session-level disabling after auth failures

Configuration:
- GITHUB_GIST_ID: Gist ID (required)
- GITHUB_TOKEN: Personal access token (required)
- GITHUB_GIST_FILENAME: Filename in Gist (default: catalog.json)
- DISABLE_GIST: Set to "1" or "true" to disable

Related Files:
- services/storage/storage_manager.py: Orchestrates Gist + Local
- services/storage/local_storage.py: Local file backup
"""

from __future__ import annotations
import json
import os
from typing import Any, Dict, Optional


# ============================================================================
# EXCEPTIONS
# ============================================================================

class GistError(Exception):
    """
    Raised when Gist operations fail.
    
    Used to signal issues like:
    - Authentication failures (401, 403)
    - Network errors
    - Missing configuration
    - Rate limiting
    """
    pass


# ============================================================================
# GIST STORAGE
# ============================================================================

class GistStorage:
    """
    Handles GitHub Gist API operations for catalog persistence.
    
    Authentication:
    - Loads credentials from environment variables or Streamlit secrets
    - Requires GITHUB_GIST_ID and GITHUB_TOKEN
    
    Behavior:
    - Automatically disables itself after authentication failures
    - Returns empty catalog structure on missing/invalid Gist content
    - Uses GitHub API v3 with 15-second timeout
    """
    
    def __init__(
        self,
        gist_id: Optional[str] = None,
        token: Optional[str] = None,
        filename: str = "catalog.json"
    ):
        """
        Initialize Gist storage.
        
        Args:
            gist_id: GitHub Gist ID (loads from secrets if None)
            token: GitHub personal access token (loads from secrets if None)
            filename: Filename within Gist (default: catalog.json)
        """
        self.gist_id = gist_id or self._get_secret("GITHUB_GIST_ID")
        self.token = token or self._get_secret("GITHUB_TOKEN")
        self.filename = filename or self._get_secret("GITHUB_GIST_FILENAME") or "catalog.json"
        self._disabled = False
    
    @staticmethod
    def _get_secret(name: str) -> Optional[str]:
        """
        Get secret from environment or Streamlit secrets.
        
        Priority:
        1. Environment variable
        2. Streamlit secrets
        3. None
        
        Args:
            name: Secret name
            
        Returns:
            Secret value or None
        """
        # Try environment first
        value = os.environ.get(name)
        if value:
            return value
        
        # Try Streamlit secrets
        try:
            import streamlit as st
            return st.secrets.get(name)
        except Exception:
            return None
    
    def is_available(self) -> bool:
        """
        Check if Gist storage is configured and enabled.
        
        Conditions:
        - GITHUB_GIST_ID must be set
        - GITHUB_TOKEN must be set
        - DISABLE_GIST must not be "1" or "true"
        - Not disabled by previous auth failure
        
        Returns:
            True if Gist can be used, False otherwise
        """
        # Check disable flag
        disable_flag = self._get_secret("DISABLE_GIST") or ""
        if disable_flag.strip() in ("1", "true", "True"):
            return False
        
        # Check configuration and disabled state
        return bool(self.gist_id and self.token) and not self._disabled
    
    def disable(self) -> None:
        """
        Permanently disable Gist for this session.
        
        Called after authentication failures to prevent repeated
        failing requests.
        """
        self._disabled = True
    
    def _headers(self) -> Dict[str, str]:
        """
        Build HTTP headers for Gist API requests.
        
        Returns:
            Dict of HTTP headers
        """
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
        Load catalog from GitHub Gist.
        
        Process:
        1. Fetch Gist via GitHub API
        2. Extract file content
        3. Parse JSON
        4. Return catalog structure
        
        Returns:
            Dict with 'warehouses' and 'customers' keys
            Returns empty structure if Gist is empty or invalid
            
        Raises:
            GistError: If fetch fails or authentication fails
        """
        import requests
        
        if not self.gist_id:
            raise GistError("Missing GIST_ID")
        
        url = f"https://api.github.com/gists/{self.gist_id}"
        
        # Fetch Gist
        try:
            response = requests.get(url, headers=self._headers(), timeout=15)
            
            # Check for auth errors
            if response.status_code in (401, 403, 404):
                raise GistError(
                    f"Gist fetch unauthorized/unavailable (HTTP {response.status_code})"
                )
            
            response.raise_for_status()
            
        except requests.RequestException as e:
            raise GistError(f"Gist fetch error: {e}")
        
        # Parse response
        data = response.json()
        files = data.get("files", {})
        
        # Check if file exists in Gist
        if self.filename not in files or "content" not in files[self.filename]:
            return {"warehouses": [], "customers": []}
        
        # Extract content
        content = files[self.filename].get("content", "")
        if not content.strip():
            return {"warehouses": [], "customers": []}
        
        # Parse JSON
        try:
            obj = json.loads(content)
        except json.JSONDecodeError:
            return {"warehouses": [], "customers": []}
        
        # Ensure required keys exist
        obj.setdefault("warehouses", [])
        obj.setdefault("customers", [])
        
        return obj
    
    def save(self, data: Dict[str, Any]) -> None:
        """
        Save catalog to GitHub Gist.
        
        Process:
        1. Serialize catalog to JSON
        2. PATCH Gist via GitHub API
        3. Handle errors
        
        Args:
            data: Catalog dict with 'warehouses' and 'customers'
            
        Raises:
            GistError: If save fails or authentication fails
        """
        import requests
        
        if not self.gist_id:
            raise GistError("Missing GIST_ID")
        
        url = f"https://api.github.com/gists/{self.gist_id}"
        
        # Build request body
        body = {
            "files": {
                self.filename: {
                    "content": json.dumps(data, ensure_ascii=False, indent=2)
                }
            }
        }
        
        # PATCH Gist
        try:
            response = requests.patch(
                url,
                headers=self._headers(),
                data=json.dumps(body),
                timeout=15
            )
            
            # Check for auth errors
            if response.status_code in (401, 403):
                raise GistError(
                    f"Gist save unauthorized (HTTP {response.status_code})"
                )
            
            response.raise_for_status()
            
        except requests.RequestException as e:
            raise GistError(f"Gist save error: {e}")