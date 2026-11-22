"""Persistent user settings (JSON next to the app)."""
import json
from pathlib import Path

PATH = Path(__file__).resolve().parent / "settings.json"
DEFAULTS = {
    "liquid_assets": [],             # ASSET accounts counted as liquid
    "runway_basis": "Availability",  # or "Liquid funds"
    "exclude_current_month": True,    # the month in progress is incomplete
    "reserve": 0.0,
    "goals": [],                     # savings goals of the Simulator page
}


def load() -> dict:
    try:
        return {**DEFAULTS, **json.loads(PATH.read_text())}
    except Exception:
        return dict(DEFAULTS)


def update(**kw) -> None:
    """Merge keys into the stored settings, writing only if something changed."""
    cfg = load()
    if all(cfg.get(k) == v for k, v in kw.items()):
        return
    cfg.update(kw)
    try:
        tmp = PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(cfg, indent=2))
        tmp.replace(PATH)
    except OSError:
        pass  # read-only folder: settings just won't persist
