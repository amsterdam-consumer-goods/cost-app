# services/config_manager.py
"""
Single source of truth for loading/saving the catalog and helpers.
Cloud (GitHub Gist) as primary source + local cache fallback.

CRITICAL FIX: Now loads from Gist FIRST on startup, writes to BOTH Gist and local.
"""

from __future__ import annotations
import json, os, re
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Tuple, List, Optional

# ------------------------------------------------------------
# Core paths and defaults
# ------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_CATALOG_REL = Path("data/catalog.json")
_DEF: Dict[str, Any] = {"warehouses": [], "customers": []}

# UI-readable warning buffer
_LAST_WARNING: Optional[str] = None

def _set_warning(msg: str) -> None:
    global _LAST_WARNING
    _LAST_WARNING = msg

def get_last_warning() -> Optional[str]:
    return _LAST_WARNING

# ------------------------------------------------------------
# Secrets / config helpers
# ------------------------------------------------------------
def _get_secret(name: str) -> Optional[str]:
    v = os.environ.get(name)
    if v:
        return v
    try:
        import streamlit as st  # type: ignore
        return st.secrets.get(name)  # type: ignore
    except Exception:
        return None

_GIST_ID = _get_secret("GITHUB_GIST_ID")
_GIST_TOKEN = _get_secret("GITHUB_TOKEN")
_GIST_FILENAME = _get_secret("GITHUB_GIST_FILENAME") or "catalog.json"
_DISABLE_GIST = (_get_secret("DISABLE_GIST") or "").strip() in ("1", "true", "True")

# runtime switch to permanently disable gist after first auth error
_GIST_DISABLED_RUNTIME = False

def _can_use_gist() -> bool:
    return (not _DISABLE_GIST) and (not _GIST_DISABLED_RUNTIME) and bool(_GIST_ID and _GIST_TOKEN)

# ------------------------------------------------------------
# Local file helpers
# ------------------------------------------------------------
def get_catalog_path() -> Path:
    env_path = os.environ.get("CATALOG_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return (_PROJECT_ROOT / _DEFAULT_CATALOG_REL).resolve()

def _ensure_parent_dir(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)

def _write_local_catalog(data: Dict[str, Any]) -> Path:
    """Write to local catalog file with guaranteed flush to disk."""
    path = get_catalog_path()
    _ensure_parent_dir(path)
    tmp = path.with_suffix(".json.tmp")
    
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    
    os.replace(tmp, path)
    
    if not path.exists():
        raise IOError(f"Failed to write catalog to {path}")
    
    return path

def _read_local_catalog() -> Dict[str, Any]:
    """Read from local catalog file."""
    path = get_catalog_path()
    if not path.exists():
        return json.loads(json.dumps(_DEF))
    
    with path.open("r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return json.loads(json.dumps(_DEF))
    
    data.setdefault("warehouses", [])
    data.setdefault("customers", [])
    return data

# ------------------------------------------------------------
# Gist helpers
# ------------------------------------------------------------
class GistError(Exception):
    pass

def _gist_headers() -> Dict[str, str]:
    hdrs = {
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if _GIST_TOKEN:
        hdrs["Authorization"] = f"token {_GIST_TOKEN}"
    return hdrs

def _load_from_gist() -> Dict[str, Any]:
    import requests
    if not _GIST_ID:
        raise GistError("Missing GIST_ID")
    url = f"https://api.github.com/gists/{_GIST_ID}"
    try:
        r = requests.get(url, headers=_gist_headers(), timeout=15)
        if r.status_code in (401, 403, 404):
            raise GistError(f"Gist fetch unauthorized/unavailable (HTTP {r.status_code}).")
        r.raise_for_status()
    except requests.RequestException as e:
        raise GistError(f"Gist fetch error: {e}")

    data = r.json()
    files = data.get("files", {})
    if _GIST_FILENAME not in files or "content" not in files[_GIST_FILENAME]:
        return json.loads(json.dumps(_DEF))

    content = files[_GIST_FILENAME].get("content", "")
    if not content.strip():
        return json.loads(json.dumps(_DEF))
    try:
        obj = json.loads(content)
    except json.JSONDecodeError:
        return json.loads(json.dumps(_DEF))
    
    obj.setdefault("warehouses", [])
    obj.setdefault("customers", [])
    return obj

def _save_to_gist(payload: Dict[str, Any]) -> None:
    import requests
    if not _GIST_ID:
        raise GistError("Missing GIST_ID")
    url = f"https://api.github.com/gists/{_GIST_ID}"
    body = {"files": {_GIST_FILENAME: {"content": json.dumps(payload, ensure_ascii=False, indent=2)}}}
    try:
        r = requests.patch(url, headers=_gist_headers(), data=json.dumps(body), timeout=15)
        if r.status_code in (401, 403):
            raise GistError(f"Gist save unauthorized (HTTP {r.status_code}).")
        r.raise_for_status()
    except requests.RequestException as e:
        raise GistError(f"Gist save error: {e}")

# ------------------------------------------------------------
# Public API (load/save)
# ------------------------------------------------------------
def load_catalog() -> Dict[str, Any]:
    """
    CRITICAL FIX: Load from Gist FIRST, fallback to local cache.
    This ensures data persists across Streamlit restarts.
    """
    global _GIST_DISABLED_RUNTIME
    
    # STEP 1: Try to load from Gist (primary source)
    if _can_use_gist():
        try:
            data = _load_from_gist()
            # Cache to local for faster subsequent reads
            _write_local_catalog(data)
            return data
        except GistError as e:
            _GIST_DISABLED_RUNTIME = True
            _set_warning(f"Cloud storage unavailable: {e}. Using local cache.")
        except Exception as e:
            _GIST_DISABLED_RUNTIME = True
            _set_warning(f"Unexpected error loading from cloud: {e}. Using local cache.")
    
    # STEP 2: Fallback to local cache
    data = _read_local_catalog()
    
    # STEP 3: If local is empty and Gist is available, initialize Gist
    if not data.get("warehouses") and not data.get("customers") and _can_use_gist():
        try:
            _save_to_gist(_DEF)
        except Exception:
            pass
    
    return data

def save_catalog(data: Dict[str, Any]) -> Path:
    """
    CRITICAL: Save to BOTH Gist (primary) and local (cache).
    """
    global _GIST_DISABLED_RUNTIME
    
    # STEP 1: Save to Gist first (primary storage)
    if _can_use_gist():
        try:
            _save_to_gist(data)
        except GistError as e:
            _GIST_DISABLED_RUNTIME = True
            _set_warning(f"Cloud storage sync failed: {e}. Data saved locally only.")
        except Exception as e:
            _GIST_DISABLED_RUNTIME = True
            _set_warning(f"Cloud storage error: {e}. Data saved locally only.")
    
    # STEP 2: Always save to local as cache
    local_path = _write_local_catalog(data)
    
    return local_path

def catalog_mtime() -> str:
    p = get_catalog_path()
    if not p.exists():
        return "(not created yet)"
    ts = datetime.fromtimestamp(p.stat().st_mtime)
    return ts.strftime("%Y-%m-%d %H:%M:%S")

# ------------------------------------------------------------
# ID + CRUD helpers
# ------------------------------------------------------------
def _slugify(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "item"

def unique_id(base: str, existing: set[str]) -> str:
    base = _slugify(base)
    if base not in existing:
        return base
    i = 2
    while f"{base}_{i}" in existing:
        i += 1
    return f"{base}_{i}"

def _existing_customer_ids(customers: Any) -> set[str]:
    if isinstance(customers, list):
        ids: set[str] = set()
        for it in customers:
            if isinstance(it, dict):
                name = it.get("name", "")
                if name:
                    ids.add(str(name))
        return ids
    return set()

def gen_customer_id(name: str, catalog: Dict[str, Any]) -> str:
    customers = catalog.get("customers", [])
    existing = _existing_customer_ids(customers)
    return unique_id(name, existing)

def list_warehouse_ids(catalog: Dict[str, Any]) -> list[str]:
    ws = catalog.get("warehouses", [])
    if not isinstance(ws, list):
        return []
    ids: list[str] = []
    for itm in ws:
        if isinstance(itm, dict):
            wid = itm.get("id", "")
            if wid:
                ids.append(str(wid))
    return sorted(set(ids), key=lambda s: s.lower())

def get_warehouse(catalog: Dict[str, Any], wid: str) -> Dict[str, Any]:
    ws = catalog.get("warehouses", [])
    if isinstance(ws, list):
        for itm in ws:
            if isinstance(itm, dict) and str(itm.get("id", "")) == str(wid):
                return itm
    return {}

def list_customers(catalog: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    if catalog is None:
        catalog = load_catalog()
    customers = catalog.get("customers", [])
    if not isinstance(customers, list):
        return []
    return customers

def _normalize_wh_list(obj: Any) -> List[Dict[str, Any]]:
    if isinstance(obj, dict) and ("warehouses" in obj):
        return _normalize_wh_list(obj["warehouses"])
    if isinstance(obj, list):
        items: List[Dict[str, Any]] = []
        for itm in obj:
            if isinstance(itm, dict) and itm.get("id"):
                items.append(itm)
        return sorted(items, key=lambda x: (str(x.get("name") or ""), str(x.get("id") or "")))
    return []

def list_warehouses(*args, **kwargs) -> List[Dict[str, Any]]:
    path = kwargs.get("path")
    if len(args) >= 1:
        return _normalize_wh_list(args[0])
    if path is not None:
        p = Path(path)
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return _normalize_wh_list(data)
    return _normalize_wh_list(load_catalog())

def get_wh_by_id(*args, **kwargs) -> Optional[Dict[str, Any]]:
    path = kwargs.get("path")
    source = None
    wid = None
    if len(args) == 1:
        wid = str(args[0])
    elif len(args) >= 2:
        source = args[0]
        wid = str(args[1])
    else:
        return None

    if source is not None:
        items = list_warehouses(source)
    else:
        if path is not None:
            p = Path(path)
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            items = list_warehouses(data)
        else:
            items = list_warehouses(load_catalog())

    for w in items:
        if str(w.get("id")) == wid:
            return w
    return None

def upsert_warehouse(catalog: Dict[str, Any], wid: str, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Update or insert a warehouse. Returns (updated_catalog, was_new)."""
    c = json.loads(json.dumps(catalog))
    ws = c.get("warehouses", [])
    
    if not isinstance(ws, list):
        ws = []
        c["warehouses"] = ws
    
    # Try to find and update existing
    was_new = True
    for i, itm in enumerate(ws):
        if isinstance(itm, dict) and str(itm.get("id", "")) == str(wid):
            ws[i] = payload
            was_new = False
            break
    
    # If not found, append
    if was_new:
        if isinstance(payload, dict):
            payload["id"] = str(wid)
        ws.append(payload)
    
    return c, was_new

def add_customer(catalog: Dict[str, Any], payload: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """Add a customer. Returns (updated_catalog, customer_id)."""
    c = json.loads(json.dumps(catalog))
    customers = c.get("customers", [])
    
    if not isinstance(customers, list):
        customers = []
        c["customers"] = customers
    
    cid = gen_customer_id(payload.get("name", "customer"), c)
    
    base_record = {
        "name": payload.get("name", cid),
        "addresses": payload.get("addresses", []),
    }
    
    customers.append(base_record)
    return c, cid