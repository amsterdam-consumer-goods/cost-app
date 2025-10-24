# services/config_manager.py
"""
Single source of truth for loading/saving the catalog and helpers.
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


# ------------------------------------------------------------
# Core file helpers
# ------------------------------------------------------------
def get_catalog_path() -> Path:
    env_path = os.environ.get("CATALOG_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return (_PROJECT_ROOT / _DEFAULT_CATALOG_REL).resolve()


def _ensure_parent_dir(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def load_catalog() -> Dict[str, Any]:
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
    # defaults (mevcut tip korunur; yoksa dict/ver)
    data.setdefault("warehouses", {})
    data.setdefault("customers", {})
    return data


def save_catalog(data: Dict[str, Any]) -> Path:
    path = get_catalog_path()
    _ensure_parent_dir(path)
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return path


def catalog_mtime() -> str:
    p = get_catalog_path()
    if not p.exists():
        return "(not created yet)"
    ts = datetime.fromtimestamp(p.stat().st_mtime)
    return ts.strftime("%Y-%m-%d %H:%M:%S")


# ------------------------------------------------------------
# ID helpers
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
    """
    customers dict/list -> mevcut id seti
    """
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


# ------------------------------------------------------------
# Warehouse / Customer CRUD helpers
# ------------------------------------------------------------
def list_warehouse_ids(catalog: Dict[str, Any]) -> list[str]:
    return sorted(catalog.get("warehouses", {}).keys())


def get_warehouse(catalog: Dict[str, Any], wid: str) -> Dict[str, Any]:
    return catalog.get("warehouses", {}).get(wid, {})


def upsert_warehouse(
    catalog: Dict[str, Any], wid: str, payload: Dict[str, Any]
) -> Tuple[Dict[str, Any], bool]:
    c = json.loads(json.dumps(catalog))
    was_new = wid not in c.get("warehouses", {})
    c.setdefault("warehouses", {})[wid] = payload
    return c, was_new


def add_customer(catalog: Dict[str, Any], payload: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """
    customers alanı dict de olabilir list de.
    - dict ise key->obj
    - list ise append
    - hiç yoksa dict oluşturur
    """
    c = json.loads(json.dumps(catalog))
    customers = c.get("customers")

    # id üret
    cid = gen_customer_id(payload.get("name", "customer"), c)
    record = {
        "name": payload.get("name", cid),
        "addresses": payload.get("addresses", []),
        "id": cid,
    }

    if customers is None:
        # hiç yoksa dict ile başlat
        c["customers"] = {cid: {k: v for k, v in record.items() if k != "id"}}
        return c, cid

    if isinstance(customers, dict):
        customers[cid] = {k: v for k, v in record.items() if k != "id"}
        return c, cid

    if isinstance(customers, list):
        customers.append(record)
        return c, cid

    # beklenmeyen tip: güvenli fallback
    c["customers"] = {cid: {k: v for k, v in record.items() if k != "id"}}
    return c, cid


def default_rates() -> Dict[str, float]:
    return {"inbound": 0.0, "outbound": 0.0, "storage": 0.0, "order_fee": 0.0}


def default_features() -> Dict[str, Any]:
    return {
        "labeling": {"enabled": False, "cost_per_unit": 0.0},
        "transfer": {"mode": "none", "manual_cost": 0.0},
        "double_stack": False,
        "second_leg": {"enabled": False, "target": None},
    }


def default_warehouse(name: str) -> Dict[str, Any]:
    return {"name": name, "rates": default_rates(), "features": default_features()}


# ------------------------------------------------------------
# Backward-compatibility helpers (robust for admin.views)
#   - list_warehouses(...)  supports:
#       * ()
#       * (catalog_or_warehouses)
#       * (path=...)
#   - get_wh_by_id(...)     supports:
#       * (wid)
#       * (catalog_or_warehouses, wid)
#       * (wid, path=...)
# ------------------------------------------------------------
def _normalize_wh_list(obj: Any) -> List[Dict[str, Any]]:
    """
    obj şunlardan biri olabilir:
      - full catalog dict ({"warehouses": {...}} veya {"warehouses": [...]} )
      - warehouses dict (id -> data)
      - warehouses list ([{...}, {...}])
    Hepsini list-of-dicts (id dahil) şekline çevirir.
    """
    # 1) Full catalog dict ise:
    if isinstance(obj, dict) and ("warehouses" in obj):
        return _normalize_wh_list(obj["warehouses"])

    # 2) Warehouses dict (id -> data) ise:
    if isinstance(obj, dict):
        items: List[Dict[str, Any]] = []
        for wid, data in obj.items():
            if isinstance(data, dict):
                item = {"id": str(wid), **data}
            else:
                item = {"id": str(wid), "value": data}
            items.append(item)
        # isme göre, yoksa id'ye göre sırala
        return sorted(items, key=lambda x: (str(x.get("name") or ""), str(x.get("id") or "")))

    # 3) Zaten list ise:
    if isinstance(obj, list):
        items: List[Dict[str, Any]] = []
        for idx, itm in enumerate(obj):
            if isinstance(itm, dict):
                # id yoksa code/name/index’ten türet
                if "id" not in itm:
                    if "code" in itm:       # tercih 1
                        itm = {"id": str(itm["code"]), **itm}
                    elif "name" in itm:     # tercih 2
                        itm = {"id": str(itm["name"]), **itm}
                    else:                   # fallback: index
                        itm = {"id": str(idx), **itm}
                items.append(itm)
            else:
                items.append({"id": str(idx), "value": itm})
        return sorted(items, key=lambda x: (str(x.get("name") or ""), str(x.get("id") or "")))

    # 4) Diğer durumlar: boş
    return []


def list_warehouses(*args, **kwargs) -> List[Dict[str, Any]]:
    """
    Eski çağrılarla uyumlu:
      - list_warehouses()
      - list_warehouses(catalog_veya_warehouses)
      - list_warehouses(path=...)
    """
    path = kwargs.get("path")

    # Argüman verilmişse (catalog veya doğrudan warehouses) onu normalize et
    if len(args) >= 1:
        return _normalize_wh_list(args[0])

    # path verilmişse dosyadan yükle
    if path is not None:
        p = Path(path)
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return _normalize_wh_list(data)

    # default: mevcut catalog'u yükle
    return _normalize_wh_list(load_catalog())


def get_wh_by_id(*args, **kwargs) -> Optional[Dict[str, Any]]:
    """
    Eski çağrılarla uyumlu:
      - get_wh_by_id(wid)
      - get_wh_by_id(catalog_veya_warehouses, wid)
      - get_wh_by_id(wid, path=...)
    """
    path = kwargs.get("path")

    source = None
    wid = None

    if len(args) == 1:
        wid = str(args[0])
    elif len(args) >= 2:
        source = args[0]    # catalog veya warehouses veya list
        wid = str(args[1])
    else:
        return None

    # Kaynak verilmişse normalize et
    if source is not None:
        items = list_warehouses(source)
    else:
        # path verilmişse oradan, yoksa mevcut catalog
        if path is not None:
            p = Path(path)
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            items = list_warehouses(data)
        else:
            items = list_warehouses(load_catalog())

    # id / code / name eşleşmesi
    for w in items:
        if str(w.get("id")) == wid or str(w.get("code")) == wid or str(w.get("name")) == wid:
            return w
    return None
