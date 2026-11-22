"""Financial planning engine: baseline -> budget -> allocation -> expected KPIs.

Pure functions (no Streamlit), so the same engine serves the Plan page, the scenario
comparison, the Simulator defaults and the printable plan sheet. Amounts are positive for
both income and expenses (like the receipt); surplus = income - expenses.
"""
import math

import numpy as np
import pandas as pd

import kpis
import logic
import sim

EPS = logic.EPS

BASE_PERIODS = {"Last 6 months": 6, "Last 12 months": 12, "Last 24 months": 24, "All history": None}
EVERY = "Every month"
KINDS = ["Cash", "Invested", "Debt"]
MODES = {"%": "% of surplus", "€/mo": "€ per month"}
DEFAULT_ALLOC = [
    {"name": "Emergency fund", "kind": "Cash", "mode": "%", "value": 30.0, "ret": 2.0, "current": 0.0},
    {"name": "Investments", "kind": "Invested", "mode": "%", "value": 40.0, "ret": 5.0, "current": 0.0},
    {"name": "Goals", "kind": "Cash", "mode": "%", "value": 15.0, "ret": 1.0, "current": 0.0},
    {"name": "Debt repayment", "kind": "Debt", "mode": "%", "value": 0.0, "ret": 0.0, "current": 0.0},
]


def _f(x, default=0.0) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return default
    return default if math.isnan(v) else v


def month_label(p: pd.Period) -> str:
    return p.to_timestamp().strftime("%b %Y")


def plan_months(start: str, n: int = 12) -> pd.PeriodIndex:
    return pd.period_range(pd.Period(start, "M"), periods=n, freq="M")


def default_start(now=None) -> str:
    return str((pd.Timestamp(now) if now is not None else pd.Timestamp.now()).to_period("M") + 1)


def default_params(start: str) -> dict:
    return {"base": {"period": "Last 12 months", "stat": "Mean", "level": "Macro", "exclude_current": True},
            "levers": {"income_pct": 0.0, "expense_pct": 0.0},
            "start": start, "pattern": "Historical", "ef_months": 6.0,
            "adjust": {}, "oneoffs": [], "alloc": [dict(a) for a in DEFAULT_ALLOC]}


# ------------------------------------------------------------------ baseline from history
def base_months(flows: pd.DataFrame, choice: str, exclude_current: bool = True, now=None) -> pd.PeriodIndex:
    days = pd.to_datetime(flows["day"]).dropna()
    if days.empty:
        return pd.PeriodIndex([], freq="M")
    first, last = days.min().to_period("M"), days.max().to_period("M")
    now_m = (pd.Timestamp(now) if now is not None else pd.Timestamp.now()).to_period("M")
    last = min(last, now_m)                    # post-dated entries are not history
    if exclude_current and last >= now_m:
        last = now_m - 1                       # last complete month
    if last < first:                           # no complete month in the history
        return pd.PeriodIndex([], freq="M")
    n = BASE_PERIODS.get(choice)
    start = first if n is None else max(first, last - (n - 1))
    return pd.period_range(start, last, freq="M")


def baseline(flows: pd.DataFrame, months: pd.PeriodIndex, level: str = "Macro") -> dict:
    """Typical monthly amount for every category over `months`, plus the monthly totals."""
    cols = ["acct_type", "key", "name", "group", "monthly", "annual"]
    f = logic._prepare_flows(flows, "Macro", None, None)
    f["m"] = f["day"].dt.to_period("M")
    f = f[f["m"].isin(months)].copy()
    empty_tot = pd.DataFrame({"income": 0.0, "expense": 0.0}, index=months)
    if f.empty:
        return {"table": pd.DataFrame(columns=cols), "monthly": empty_tot, "months": months}
    if level == "Detailed":
        f["name"], f["group"] = f["exact"], f["macro"]
        f["key"] = np.where(f["exact"] == f["macro"], f["acct_type"] + "|" + f["macro"],
                            f["acct_type"] + "|" + f["macro"] + "|" + f["exact"])
    else:
        f["name"], f["group"] = f["macro"], f["macro"]
        f["key"] = f["acct_type"] + "|" + f["macro"]
    g = (f.groupby(["acct_type", "key", "name", "group", "m"])["Amount"].sum().unstack("m")
         .reindex(columns=months).fillna(0.0))
    tot = f.groupby(["m", "acct_type"])["Amount"].sum().unstack().reindex(months).fillna(0.0)
    for c in ("INCOME", "EXPENSE"):
        if c not in tot.columns:
            tot[c] = 0.0
    tot = tot.rename(columns={"INCOME": "income", "EXPENSE": "expense"})[["income", "expense"]]
    monthly = g.mean(axis=1)
    tab = monthly.rename("monthly").reset_index()
    tab["annual"] = tab["monthly"] * 12
    tab = tab[tab["annual"].abs() >= 0.005].sort_values(["acct_type", "annual"], ascending=[True, False])
    return {"table": tab.reset_index(drop=True)[cols], "monthly": tot, "months": months}


def month_weights(hist: pd.Series, months, pattern: str) -> np.ndarray:
    """How a year's total is spread over the plan months (mean 1): the same calendar month's
    typical share in the history, or flat."""
    if pattern == "Flat" or len(hist) < 6 or hist.sum() <= 0:
        return np.ones(len(months))
    prof = hist.groupby(hist.index.month).mean()
    fill = float(hist.mean())
    w = np.array([prof.get(p.month, fill) for p in months], float)
    return w / w.mean() if w.mean() > 0 else np.ones(len(months))


# ------------------------------------------------------------------ stage 1: the budget
def budget(params: dict, base: dict) -> dict:
    months = plan_months(params["start"])
    labels = [month_label(p) for p in months]
    tab = base["table"].copy()
    adj, lev = params.get("adjust", {}) or {}, params["levers"]

    def planned(r):
        a = adj.get(r["key"]) or {}
        ov = a.get("override")
        if ov is not None and not (isinstance(ov, float) and math.isnan(ov)):
            return float(ov)
        g = lev["income_pct"] if r["acct_type"] == "INCOME" else lev["expense_pct"]
        return r["annual"] * (1 + g / 100.0) * (1 + _f(a.get("pct")) / 100.0)

    tab["planned"] = [planned(r) for _, r in tab.iterrows()]
    tab["delta"] = tab["planned"] - tab["annual"]
    rec, bas = tab.groupby("acct_type")["planned"].sum(), tab.groupby("acct_type")["annual"].sum()
    inc_rec, exp_rec = float(rec.get("INCOME", 0.0)), float(rec.get("EXPENSE", 0.0))
    b_inc, b_exp = float(bas.get("INCOME", 0.0)), float(bas.get("EXPENSE", 0.0))

    income = inc_rec / 12 * month_weights(base["monthly"]["income"], months, params["pattern"])
    expense = exp_rec / 12 * month_weights(base["monthly"]["expense"], months, params["pattern"])
    oo_inc = oo_exp = 0.0
    ignored = []
    for o in params.get("oneoffs", []) or []:
        amt = _f(o.get("amount"))
        if amt <= 0:
            continue
        when = o.get("when")
        if when == EVERY:
            add = np.full(len(months), amt)
        elif when in labels:
            add = np.zeros(len(months))
            add[labels.index(when)] = amt
        else:
            ignored.append(str(o.get("name") or "item"))
            continue
        if o.get("type") == "Income":
            income, oo_inc = income + add, oo_inc + add.sum()
        else:
            expense, oo_exp = expense + add, oo_exp + add.sum()

    monthly = pd.DataFrame({"income": income, "expense": expense}, index=months)
    monthly["net"] = monthly["income"] - monthly["expense"]
    inc_t, exp_t = float(monthly["income"].sum()), float(monthly["expense"].sum())
    tot = {"baseline_income": b_inc, "baseline_expense": b_exp, "baseline_surplus": b_inc - b_exp,
           "baseline_rate": (b_inc - b_exp) / b_inc if b_inc > 0 else math.nan,
           "income": inc_t, "expense": exp_t, "surplus": inc_t - exp_t,
           "rate": (inc_t - exp_t) / inc_t if inc_t > 0 else math.nan,
           "oneoff_income": oo_inc, "oneoff_expense": oo_exp}
    bridge = [("Baseline surplus", b_inc - b_exp, "absolute"),
              ("Income changes", inc_rec - b_inc, "relative"),
              ("Expense changes", -(exp_rec - b_exp), "relative"),
              ("One-off & new items", oo_inc - oo_exp, "relative"),
              ("Planned surplus", inc_t - exp_t, "total")]
    return {"months": months, "labels": labels, "table": tab, "monthly": monthly,
            "totals": tot, "bridge": bridge, "ignored": ignored}


# ------------------------------------------------------------------ stage 2: where the surplus goes
def allocation(bud: dict, alloc: list, pos: dict, ef_months: float = 6.0) -> dict:
    """Give the surplus a job and follow what it does to cash, availability and net worth.

    * Cash buckets: the money stays liquid, and so does its growth.
    * Invested buckets: contributions and growth stay in your accounts (availability, net worth)
      but are no longer liquid.
    * Debt buckets: contributions repay a loan. The cash leaves your accounts, and the loan falls by
      the same amount, so net worth is unchanged. `ret` is the loan's interest rate: the interest
      you avoid is a net-worth gain, not cash. "Already there" does not apply to debts.
    """
    surplus = bud["totals"]["surplus"]
    available = max(surplus, 0.0)            # a deficit leaves nothing to allocate
    rows, total = [], 0.0
    for a in alloc or []:
        name = str(a.get("name") or "").strip()
        if not name:
            continue
        kind = a.get("kind", "Cash")
        mode, val = a.get("mode", "%"), _f(a.get("value"))
        annual = available * val / 100.0 if mode == "%" else val * 12.0
        monthly, ret = annual / 12.0, _f(a.get("ret"))
        cur = 0.0 if kind == "Debt" else _f(a.get("current"))
        end = sim.fv(cur, monthly, ret, 12)
        rows.append({"name": name, "kind": kind, "mode": mode, "value": val,
                     "annual": annual, "monthly": monthly, "ret": ret, "current": cur,
                     "end": end, "growth": end - cur - annual})
        total += annual
    unalloc = available - total

    def part(kind, key):
        return sum(r[key] for r in rows if r["kind"] == kind)

    cash_growth, invested_growth = part("Cash", "growth"), part("Invested", "growth")
    growth = sum(r["growth"] for r in rows)
    invested = part("Invested", "annual") + invested_growth     # leaves liquid funds, stays in availability
    debt_paid = part("Debt", "annual")                          # leaves cash and availability

    liquid_end = pos["liquid"] + surplus + cash_growth - invested - debt_paid
    avail_end = pos["availability"] + surplus + cash_growth + invested_growth - debt_paid
    nw_end = pos["net_worth"] + surplus + growth

    # Month by month. The monthly net follows the budget; growth and transfers are spread evenly,
    # so month 12 lands exactly on liquid_end / avail_end.
    net = bud["monthly"]["net"].to_numpy()
    cash = pos["liquid"] + np.cumsum(net + (cash_growth - invested - debt_paid) / 12.0)
    avail = pos["availability"] + np.cumsum(net + (cash_growth + invested_growth - debt_paid) / 12.0)

    burn = float(bud["monthly"]["expense"].median())
    target = ef_months * burn
    cash_monthly = (liquid_end - pos["liquid"]) / 12.0
    if pos["liquid"] >= target:
        to_fill = 0.0
    else:
        to_fill = (target - pos["liquid"]) / cash_monthly if cash_monthly > 0 else math.inf
    ef = {"months": ef_months, "target": target, "coverage_now": pos["liquid"] / burn if burn > 0 else math.inf,
          "coverage_end": liquid_end / burn if burn > 0 else math.inf,
          "gap_end": max(target - liquid_end, 0.0), "months_to_fill": to_fill}
    return {"rows": rows, "unalloc": unalloc, "over": unalloc < -EPS, "total": total,
            "liquid_end": liquid_end, "availability_end": avail_end, "net_worth_end": nw_end,
            "growth": growth, "debt_paid": debt_paid, "invested": invested,
            "cash_path": cash, "availability_path": avail, "ef": ef}


# ------------------------------------------------------------------ stage 3: expected KPIs
def outlook(bud: dict, al: dict, base: dict, pos: dict) -> dict:
    avail_basis = pos.get("runway_basis", "Availability") == "Availability"
    now_base = pos["availability"] if avail_basis else pos["liquid"]
    end_base = al["availability_end"] if avail_basis else al["liquid_end"]
    return {"now": kpis.compute(base["monthly"], pos["availability"], pos["liquid"], now_base),
            "end": kpis.compute(bud["monthly"][["income", "expense"]], al["availability_end"],
                                al["liquid_end"], end_base)}


def evaluate(params: dict, base: dict, pos: dict) -> dict:
    """Run the three stages and add a flat summary (used to compare scenarios)."""
    bud = budget(params, base)
    al = allocation(bud, params.get("alloc", []), pos, params.get("ef_months", 6.0))
    ol = outlook(bud, al, base, pos)
    t = bud["totals"]
    summary = {"Income": t["income"], "Expenses": t["expense"], "Surplus": t["surplus"],
               "Savings rate": t["rate"], "Runway after plan (months)": ol["end"]["runway"],
               "Liquid funds after plan": al["liquid_end"], "Net worth after plan": al["net_worth_end"],
               "Emergency fund coverage (months)": al["ef"]["coverage_end"]}
    return {"budget": bud, "allocation": al, "outlook": ol, "summary": summary}


def scenario_fan(params: dict, base: dict, pos: dict, *, n: int = 500, seed: int = 7) -> dict:
    """Random availability paths for one scenario, shocked with historic monthly net volatility.

    The deterministic path is the plan's own availability path, which ends on the plan's
    availability after 12 months.
    Each simulated month adds a random shock with the standard deviation of the historical
    monthly net cash flow, so the fan shows how fragile the plan is without changing its
    expected result."""
    ev = evaluate(params, base, pos)
    start = float(pos["availability"])
    det = np.concatenate([[start], np.asarray(ev["allocation"]["availability_path"], dtype=float)])
    hist = base["monthly"]
    net = (hist["income"] - hist["expense"]).to_numpy(dtype=float)
    sd = float(np.std(net, ddof=1)) if len(net) > 1 else 0.0
    rng = np.random.default_rng(seed)
    steps = np.diff(det)
    noise = rng.normal(0.0, sd, size=(n, len(steps)))
    paths = start + np.cumsum(steps + noise, axis=1)
    paths = np.concatenate([np.full((n, 1), start), paths], axis=1)

    def q(percentile):
        return np.percentile(paths, percentile, axis=0)

    return {"p10": q(10), "p25": q(25), "p50": q(50), "p75": q(75), "p90": q(90),
            "det": det, "months": len(det) - 1, "sd": sd}
