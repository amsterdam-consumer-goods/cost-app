# services/config_manager.py
"""
Single source of truth for loading/saving the catalog and helpers.
Cloud (GitHub Gist) + automatic local fallback. Never crash UI on 401.

This module also exposes backward-compat helpers expected by admin views:
- list_warehouses(source_or_kwargs)
- get_wh_by_id(source_or_id, wid?) 
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
_DEF: Dict[str, Any] = {"warehouses": {}, "customers": {}}

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
        # treat 401/403/404 as fatal but handled
        if r.status_code in (401, 403, 404):
            raise GistError(f"Gist fetch unauthorized/unavailable (HTTP {r.status_code}).")
        r.raise_for_status()
    except requests.RequestException as e:
        raise GistError(f"Gist fetch error: {e}")

    data = r.json()
    files = data.get("files", {})
    if _GIST_FILENAME not in files or "content" not in files[_GIST_FILENAME]:
        _save_to_gist(_DEF)
        return json.loads(json.dumps(_DEF))

    content = files[_GIST_FILENAME].get("content", "")
    if not content.strip():
        return json.loads(json.dumps(_DEF))
    try:
        obj = json.loads(content)
    except json.JSONDecodeError:
        _save_to_gist(_DEF)
        obj = json.loads(json.dumps(_DEF))
    obj.setdefault("warehouses", {})
    obj.setdefault("customers", {})
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
# Public API (load/save) with safe fallback
# ------------------------------------------------------------
def load_catalog() -> Dict[str, Any]:
    global _GIST_DISABLED_RUNTIME
    if _can_use_gist():
        try:
            return _load_from_gist()
        except GistError as e:
            _GIST_DISABLED_RUNTIME = True
            _set_warning(f"Cloud storage (GitHub Gist) erişilemedi: {e}. Yerel dosyaya geçildi.")
        except Exception as e:
            _GIST_DISABLED_RUNTIME = True
            _set_warning(f"Cloud storage beklenmeyen hata: {e}. Yerel dosyaya geçildi.")

    path = get_catalog_path()
    if not path.exists():
        _ensure_parent_dir(path)
        save_catalog(_DEF)
        return json.loads(json.dumps(_DEF))
    with path.open("r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            backup = path.with_suffix(".corrupt.json")
            path.rename(backup)
            save_catalog(_DEF)
            data = json.loads(json.dumps(_DEF))
    data.setdefault("warehouses", {})
    data.setdefault("customers", {})
    return data

def save_catalog(data: Dict[str, Any]) -> Path:
    global _GIST_DISABLED_RUNTIME
    if _can_use_gist():
        try:
            _save_to_gist(data)
            return Path(f"gist://{_GIST_ID}/{_GIST_FILENAME}")
        except GistError as e:
            _GIST_DISABLED_RUNTIME = True
            _set_warning(f"Cloud storage kaydı başarısız: {e}. Yerel dosyaya kaydedildi.")
        except Exception as e:
            _GIST_DISABLED_RUNTIME = True
            _set_warning(f"Cloud storage beklenmeyen hata: {e}. Yerel dosyaya kaydedildi.")

    path = get_catalog_path()
    _ensure_parent_dir(path)
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return path

def catalog_mtime() -> str:
    if _can_use_gist():
        return "(stored in GitHub Gist)"
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
    if isinstance(customers, dict):
        return set(map(str, customers.keys()))
    if isinstance(customers, list):
        ids: set[str] = set()
        for it in customers:
            if isinstance(it, dict):
                cid = it.get("id") or it.get("cid") or it.get("code") or it.get("name")
                if cid:
                    ids.add(str(cid))
        return ids
    return set()

def gen_customer_id(name: str, catalog: Dict[str, Any]) -> str:
    customers = catalog.get("customers", {})
    existing = _existing_customer_ids(customers)
    return unique_id(name, existing)

def list_warehouse_ids(catalog: Dict[str, Any]) -> list[str]:
    ws = catalog.get("warehouses")
    ids: list[str] = []
    if isinstance(ws, dict):
        ids = [str(k) for k in ws.keys()]
    elif isinstance(ws, list):
        for idx, itm in enumerate(ws):
            if isinstance(itm, dict):
                wid = itm.get("id") or itm.get("code") or itm.get("name") or str(idx)
                ids.append(str(wid))
            else:
                ids.append(str(idx))
    else:
        ids = []
    return sorted(set(ids), key=lambda s: s.lower())

def get_warehouse(catalog: Dict[str, Any], wid: str) -> Dict[str, Any]:
    ws = catalog.get("warehouses", {})
    if isinstance(ws, dict):
        return ws.get(wid, {})
    if isinstance(ws, list):
        for idx, itm in enumerate(ws):
            if isinstance(itm, dict):
                iw = str(itm.get("id") or itm.get("code") or itm.get("name") or idx)
                if iw == str(wid):
                    return itm
    return {}

def upsert_warehouse(catalog: Dict[str, Any], wid: str, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    c = json.loads(json.dumps(catalog))
    ws = c.get("warehouses")
    if isinstance(ws, dict) or ws is None:
        c.setdefault("warehouses", {})
        was_new = wid not in c["warehouses"]
        c["warehouses"][wid] = payload
        return c, was_new
    if isinstance(ws, list):
        was_new = True
        replaced = False
        for i, itm in enumerate(ws):
            if isinstance(itm, dict):
                iw = str(itm.get("id") or itm.get("code") or itm.get("name") or i)
                if iw == str(wid):
                    ws[i] = payload
                    replaced = True
                    was_new = False
                    break
        if not replaced:
            if isinstance(payload, dict):
                pl = dict(payload)
                pl.setdefault("id", str(wid))
                ws.append(pl)
            else:
                ws.append(payload)
        return c, was_new
    c["warehouses"] = {wid: payload}
    return c, True

def add_customer(catalog: Dict[str, Any], payload: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    c = json.loads(json.dumps(catalog))
    customers = c.get("customers")
    cid = gen_customer_id(payload.get("name", "customer"), c)
    record = {
        "name": payload.get("name", cid),
        "addresses": payload.get("addresses", []),
        "id": cid,
        **({k: v for k, v in payload.items() if k not in {"name", "addresses"}}),
    }
    if customers is None:
        c["customers"] = {cid: {k: v for k, v in record.items() if k != "id"}}
        return c, cid
    if isinstance(customers, dict):
        customers[cid] = {k: v for k, v in record.items() if k != "id"}
        return c, cid
    if isinstance(customers, list):
        customers.append(record)
        return c, cid
    c["customers"] = {cid: {k: v for k, v in record.items() if k != "id"}}
    return c, cid

def list_customers(catalog: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Returns a normalized list of customers [{id,name,addresses,...}], independent of dict/list storage."""
    if catalog is None:
        catalog = load_catalog()
    customers = catalog.get("customers", {})
    out: List[Dict[str, Any]] = []
    if isinstance(customers, dict):
        for cid, obj in customers.items():
            if isinstance(obj, dict):
                rec = {"id": str(cid), "name": obj.get("name", str(cid)), "addresses": obj.get("addresses", [])}
                # keep other fields
                for k, v in obj.items():
                    if k not in rec:
                        rec[k] = v
                out.append(rec)
    elif isinstance(customers, list):
        for it in customers:
            if isinstance(it, dict):
                cid = str(it.get("id") or it.get("cid") or it.get("code") or it.get("name") or "")
                if not cid:
                    continue
                rec = {"id": cid, "name": it.get("name", cid), "addresses": it.get("addresses", [])}
                for k, v in it.items():
                    if k not in rec:
                        rec[k] = v
                out.append(rec)
    return sorted(out, key=lambda x: x.get("name", "").lower())

# ------------------------------------------------------------
# Backward-compat: list_warehouses & get_wh_by_id expected by admin views
# ------------------------------------------------------------
def _normalize_wh_list(obj: Any) -> List[Dict[str, Any]]:
    """Return list of dicts with at least an 'id' key, sorted for UI."""
    if isinstance(obj, dict) and ("warehouses" in obj):
        return _normalize_wh_list(obj["warehouses"])
    if isinstance(obj, dict):
        items: List[Dict[str, Any]] = []
        for wid, data in obj.items():
            if isinstance(data, dict):
                item = {"id": str(wid), **data}
            else:
                item = {"id": str(wid), "value": data}
            items.append(item)
        return sorted(items, key=lambda x: (str(x.get("name") or ""), str(x.get("id") or "")))
    if isinstance(obj, list):
        items: List[Dict[str, Any]] = []
        for idx, itm in enumerate(obj):
            if isinstance(itm, dict):
                if "id" not in itm:
                    if "code" in itm:
                        itm = {"id": str(itm["code"]), **itm}
                    elif "name" in itm:
                        itm = {"id": str(itm["name"]), **itm}
                    else:
                        itm = {"id": str(idx), **itm}
                items.append(itm)
            else:
                items.append({"id": str(idx), "value": itm})
        return sorted(items, key=lambda x: (str(x.get("name") or ""), str(x.get("id") or "")))
    return []

def list_warehouses(*args, **kwargs) -> List[Dict[str, Any]]:
    """
    Compat shim used by admin/views/update_warehouse.py:
    - list_warehouses(catalog_dict)  -> normalized list
    - list_warehouses(path="...")    -> load JSON then normalize
    - list_warehouses()              -> load_catalog() then normalize
    """
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
    """
    Compat shim:
    - get_wh_by_id(wid)
    - get_wh_by_id(catalog, wid)
    - get_wh_by_id(path="...")  # not typical, but supported with kwargs
    """
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
        if str(w.get("id")) == wid or str(w.get("code")) == wid or str(w.get("name")) == wid:
            return w
    return None

def list_customers(catalog: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Return customers as a normalized list: [{id, name, addresses, ...}]."""
    if catalog is None:
        catalog = load_catalog()
    customers = catalog.get("customers", {})
    out: List[Dict[str, Any]] = []
    if isinstance(customers, dict):
        for cid, obj in customers.items():
            if isinstance(obj, dict):
                rec = {"id": str(cid), "name": obj.get("name", str(cid)), "addresses": obj.get("addresses", [])}
                for k, v in obj.items():
                    if k not in rec:
                        rec[k] = v
                out.append(rec)
    elif isinstance(customers, list):
        for it in customers:
            if isinstance(it, dict):
                cid = str(it.get("id") or it.get("cid") or it.get("code") or it.get("name") or "")
                if not cid:
                    continue
                rec = {"id": cid, "name": it.get("name", cid), "addresses": it.get("addresses", [])}
                for k, v in it.items():
                    if k not in rec:
                        rec[k] = v
                out.append(rec)
    return sorted(out, key=lambda x: x.get("name", "").lower())
