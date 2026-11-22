"""Saved planning scenarios (JSON next to the app)."""
import json
import math
from pathlib import Path

import numpy as np

PATH = Path(__file__).resolve().parent / "plans.json"


def _clean(o):
    """Make anything JSON-safe (numpy types, NaN -> None)."""
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if math.isnan(float(o)) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def load() -> dict:
    try:
        d = json.loads(PATH.read_text())
        return {"plans": d.get("plans", {}), "active": d.get("active")}
    except Exception:
        return {"plans": {}, "active": None}


def _write(d: dict) -> bool:
    try:
        tmp = PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(_clean(d), indent=2))
        tmp.replace(PATH)
        return True
    except OSError:
        return False


def save_plan(name: str, params: dict, make_active: bool = True) -> bool:
    d = load()
    d["plans"][name] = params
    if make_active:
        d["active"] = name
    return _write(d)


def delete_plan(name: str) -> bool:
    d = load()
    d["plans"].pop(name, None)
    if d["active"] == name:
        d["active"] = next(iter(d["plans"]), None)
    return _write(d)
