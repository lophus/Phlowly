"""Long-term projections: compound growth, Monte Carlo, goals, stress tests.

Pure functions (no Streamlit). Returns are *effective annual* rates; the monthly
rate is (1 + r) ** (1/12) - 1 everywhere, so every module agrees to the cent.
"""
import math

import numpy as np


def monthly_rate(ret_pct: float) -> float:
    ret_pct = max(ret_pct, -99.9)      # a return of -100% or less is not defined
    return (1 + ret_pct / 100.0) ** (1 / 12) - 1


def fv(current: float, monthly: float, ret_pct: float, months: int) -> float:
    """Value after `months` of growth with a contribution at the end of every month."""
    r = monthly_rate(ret_pct)
    ann = ((1 + r) ** months - 1) / r if r else months
    return current * (1 + r) ** months + monthly * ann


def required_monthly(target: float, current: float, months: int, ret_pct: float) -> float:
    """Monthly saving needed to reach `target` in `months`."""
    n = max(int(months), 0)
    r = monthly_rate(ret_pct)
    need = target - current * (1 + r) ** n
    if need <= 0:
        return 0.0
    if n == 0:
        return math.inf
    return need / (((1 + r) ** n - 1) / r if r else n)


def months_to_target(target: float, current: float, monthly: float, ret_pct: float,
                     growth_pct: float = 0.0, max_months: int = 1200) -> float:
    """Months until `target` is reached (inf if not within `max_months`)."""
    eps = 0.005                       # half a cent: float noise must not cost a whole month
    r, w = monthly_rate(ret_pct), float(current)
    if w >= target - eps:
        return 0.0
    for t in range(max_months):
        w = w * (1 + r) + monthly * (1 + growth_pct / 100.0) ** (t // 12)
        if w >= target - eps:
            return float(t + 1)
    return math.inf


def years_to_target(target: float, start: float, yearly: float, ret_pct: float,
                    growth_pct: float = 0.0, infl_pct: float = 0.0, max_years: int = 200) -> float:
    """Whole years until a target is reached with one contribution per year.

    `target` is in today's money and the wealth path is nominal, so the target is raised by
    `infl_pct` every year (0 = compare as they are)."""
    w = float(start)
    if w >= target - 0.005:
        return 0.0
    r = ret_pct / 100.0
    for t in range(max_years):
        w = w * (1 + r) + yearly * (1 + growth_pct / 100.0) ** t
        if w >= target * (1 + infl_pct / 100.0) ** (t + 1) - 0.005:
            return float(t + 1)
    return math.inf


def inflate(amount: float, infl_pct: float, years: int) -> float:
    """Today's money expressed in money of `years` from now."""
    return amount * (1 + infl_pct / 100.0) ** max(int(years), 0)


def monte_carlo(start: float, yearly: float, growth_pct: float, ret_pct: float,
                vol_pct: float, years: int, infl_pct: float = 0.0, real: bool = False,
                n: int = 1000, seed: int = 7) -> dict:
    """Annual wealth paths: one contribution per year, annual log-normal returns.

    `yearly` is added at the end of each year and rises by `growth_pct` every year.
    `ret_pct` and `vol_pct` are annual. With real=True everything is expressed in
    today's money. The seed is fixed so the chart is stable between reruns."""
    years = max(int(years), 0)
    rng = np.random.default_rng(seed)
    s = vol_pct / 100.0
    m = math.log1p(ret_pct / 100.0) - 0.5 * s * s
    R = np.exp(rng.normal(m, s, size=(n, years)))
    contrib = np.array([yearly * (1 + growth_pct / 100.0) ** t for t in range(years)])
    paths = np.empty((n, years + 1))
    paths[:, 0] = start
    w = np.full(n, float(start))
    for t in range(years):
        w = w * R[:, t] + contrib[t]
        paths[:, t + 1] = w
    gd = 1 + ret_pct / 100.0
    det = np.empty(years + 1)
    det[0] = start
    d = float(start)
    for t in range(years):
        d = d * gd + contrib[t]
        det[t + 1] = d
    contributed = start + np.concatenate([[0.0], np.cumsum(contrib)])
    if real:
        defl = (1 + infl_pct / 100.0) ** np.arange(years + 1)
        paths, det = paths / defl, det / defl
        # Each contribution is deflated by the price level when it was made, not by the final one.
        contributed = float(start) + np.concatenate([[0.0], np.cumsum(contrib / defl[1:])])
    p10, p25, p50, p75, p90 = np.percentile(paths, [10, 25, 50, 75, 90], axis=0)
    return {"years": years, "p10": p10, "p25": p25, "p50": p50, "p75": p75, "p90": p90,
            "det": det, "contributed": contributed, "final": paths[:, -1]}


def cash_path(liquid: float, horizon: int, income, expense, drop_pct: float = 0.0,
              duration: int = 0, shock_pct: float = 0.0) -> np.ndarray:
    """Cash balance month by month. Income falls by `drop_pct` for `duration` months
    (duration 0 = the whole horizon); expenses rise by `shock_pct` throughout."""
    p = np.empty(horizon + 1)
    p[0] = bal = float(liquid)
    for t in range(1, horizon + 1):
        cut = drop_pct / 100.0 if (duration <= 0 or t <= duration) else 0.0
        bal += income * (1 - cut) - expense * (1 + shock_pct / 100.0)
        p[t] = bal
    return p


def cash_lasts(path: np.ndarray) -> float:
    """Months until the balance goes below zero (interpolated); inf if it never does."""
    below = np.where(path < 0)[0]
    if len(below) == 0:
        return math.inf
    t = int(below[0])
    if t == 0:
        return 0.0
    a, b = path[t - 1], path[t]
    return (t - 1) + (a / (a - b) if a != b else 0.0)
