"""KPI engine: pure functions, reusable by the dashboard and by the Plan page.

Input is a monthly series (columns 'income' and 'expense'), so the same code
can run on historical data or on a simulated plan.
"""
import math

import pandas as pd

NAN = float("nan")

# Thresholds shared by the screen, the printed reports and the charts.
RUNWAY_BANDS = (6.0, 12.0, 24.0)     # critical < 6 <= caution < 12 <= healthy; gauges go up to 24
VOL_LOW, VOL_HIGH = 0.30, 0.60       # volatility = std / median


def runway_status(v):
    """(label, level) with level in red/yellow/green, or None when there is no value."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    if math.isinf(v):
        return ("Self-sustaining", "green")
    if v < RUNWAY_BANDS[0]:
        return ("Critical", "red")
    if v < RUNWAY_BANDS[1]:
        return ("Caution", "yellow")
    return ("Healthy", "green")


def volatility_level(v):
    """(label, level) with level in green/yellow/red/grey."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ("n/a", "grey")
    if v < VOL_LOW:
        return ("Stable", "green")
    if v < VOL_HIGH:
        return ("Variable", "yellow")
    return ("Volatile", "red")


def _ok(x) -> bool:
    return x is not None and not math.isnan(x)


def _ratio(a, b):
    return a / b if _ok(a) and _ok(b) and b > 0 else NAN


def _runway(base, burn):
    """Months of coverage; inf if there is no burn, never negative."""
    if not (_ok(base) and _ok(burn)):
        return NAN
    if burn <= 0:
        return math.inf if base > 0 else NAN
    return max(0.0, base / burn)


def compute(monthly: pd.DataFrame, availability: float, liquid: float,
            runway_base: float) -> dict:
    n = len(monthly)
    inc, exp = monthly["income"], monthly["expense"]

    burn = float(exp.median()) if n else NAN
    inc_med = float(inc.median()) if n else NAN
    exp_sd = float(exp.std()) if n > 1 else NAN     # sample std (ddof=1)
    inc_sd = float(inc.std()) if n > 1 else NAN
    tot_inc, tot_exp = float(inc.sum()), float(exp.sum())

    worst_burn = burn + exp_sd if _ok(burn) and _ok(exp_sd) else NAN
    worst_income = max(0.0, inc_med - inc_sd) if _ok(inc_med) and _ok(inc_sd) else NAN
    net = inc_med - burn if _ok(inc_med) and _ok(burn) else NAN
    worst_net_burn = worst_burn - worst_income if _ok(worst_burn) and _ok(worst_income) else NAN

    return {
        "months": n,
        "availability": availability,
        "liquid": liquid,
        "liquidity_pct": _ratio(liquid, availability),
        "median_burn": burn,
        "expense_std": exp_sd,
        "expense_vol": _ratio(exp_sd, burn),
        "median_income": inc_med,
        "income_std": inc_sd,
        "income_vol": _ratio(inc_sd, inc_med),
        "savings_rate": (tot_inc - tot_exp) / tot_inc if tot_inc > 0 else NAN,
        "runway": _runway(runway_base, burn),
        "worst_runway": _runway(runway_base, worst_burn),
        "net_monthly": net,
        "net_rate": _ratio(net, inc_med),
        # worst case: expenses at median+std, income at median-std (floored at 0)
        "worst_net_runway": _runway(runway_base, worst_net_burn),
    }
