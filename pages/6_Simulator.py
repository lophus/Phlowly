import datetime as dt
import math

import numpy as np
import pandas as pd
import streamlit as st

import db
import kpis
import logic
import planning as P
import plans
import reports as R
import settings
import sim
import svgcharts as sc
import ui

st.set_page_config(page_title="Simulator", page_icon=":material/query_stats:", layout="wide")
ui.inject_css()
CFG = {"displayModeBar": False}
cc = st.column_config
run_mc = st.cache_data(sim.monte_carlo)

deltas, flows, all_days = db.load_all()
ui.currency_warning(db.book_currencies(deltas))
cfg = settings.load()
store = plans.load()

pos = logic.position(deltas, cfg["liquid_assets"], cfg["runway_basis"])
invested_now = float(deltas.loc[deltas["acct_type"].isin(["MUTUAL", "STOCK"]), "delta"].sum())
names = list(store["plans"])
ss = st.session_state

# Streamlit drops the state of widgets that are not drawn while you are on another page: keep a mirror
SM_KEYS = ["sm_src", "sm_start_mode", "sm_start_custom", "sm_contrib", "sm_growth", "sm_ret", "sm_vol", "sm_years",
           "sm_infl", "sm_real", "sm_target", "st_drop", "st_dur", "st_shock", "st_horizon", "fi_swr"]
for _k, _v in ss.get("_sm_mirror", {}).items():
    if _k not in ss:
        ss[_k] = _v

with st.sidebar:
    st.header("Filters")
    hide = ui.sidebar_privacy()
    st.header("Starting point")
    opts = ["Historical data only"] + names
    idx = opts.index(store["active"]) if store["active"] in opts else 0
    if ss.get("sm_src") not in opts:
        ss.pop("sm_src", None)
    src = st.selectbox("Start from plan", opts, key="sm_src",
                       **({} if "sm_src" in ss else {"index": idx}),
                       help="Income, spending and savings come from this plan. Save a plan in the Plan page to use it here.")


def context(src_name: str) -> dict:
    """Typical income/spending, savings and returns, from a saved plan or from the history."""
    basis = pos["availability"] if pos["runway_basis"] == "Availability" else pos["liquid"]
    if src_name in store["plans"]:
        p = store["plans"][src_name]
        b = p["base"]
        base = P.baseline(flows, P.base_months(flows, b["period"], b["exclude_current"]), b["level"])
        ev = P.evaluate(p, base, pos)
        k = ev["outlook"]["end"]
        inv = [r for r in ev["allocation"]["rows"] if r["kind"] == "Invested"]
        invested_m = sum(r["monthly"] for r in inv)
        ret = sum(r["ret"] * r["monthly"] for r in inv) / invested_m if invested_m > 0 else 5.0
        return {"k": k, "invested_m": invested_m, "ret": ret, "surplus_m": ev["budget"]["totals"]["surplus"] / 12,
                "label": f"plan “{src_name}”"}
    base = P.baseline(flows, P.base_months(flows, "Last 12 months", True), "Macro")
    k = kpis.compute(base["monthly"], pos["availability"], pos["liquid"], basis)
    net = k["net_monthly"] if not math.isnan(k["net_monthly"]) else 0.0
    return {"k": k, "invested_m": max(net, 0.0), "ret": 5.0, "surplus_m": net, "label": "your history (last 12 months)"}


ctx = context(src)
k = ctx["k"]
income_m = k["median_income"] if not math.isnan(k["median_income"]) else 0.0
expense_m = k["median_burn"] if not math.isnan(k["median_burn"]) else 0.0
exp_sd = k["expense_std"] if not math.isnan(k["expense_std"]) else 0.0
inc_sd = k["income_std"] if not math.isnan(k["income_std"]) else 0.0
worst_income, worst_expense = max(0.0, income_m - inc_sd), expense_m + exp_sd
fi_default = round(expense_m * 12 / 0.04, -2) if expense_m > 0 else 0.0


def clamp(x, lo, hi):
    return float(min(max(x, lo), hi))


if ss.get("_sm_loaded") != src or any(k not in ss for k in SM_KEYS if k != "sm_src"):   # new start -> fresh defaults
    ss.update({"sm_start_mode": "Net worth", "sm_start_custom": max(pos["net_worth"], 0.0),
               "sm_contrib": round(clamp(ctx["invested_m"] * 12, 0, 1e8), 2), "sm_growth": 0.0,
               "sm_ret": clamp(ctx["ret"], -10, 30), "sm_vol": 12.0, "sm_years": 25, "sm_infl": 2.0,
               "sm_real": False, "sm_target": fi_default,
               "st_drop": 100, "st_dur": 6, "st_shock": 10, "st_horizon": 36, "fi_swr": 4.0})
    ss["_sm_loaded"] = src


def m(x, **kw):
    return ui.MASK if hide else ui.fmt(x, "money", **kw)


ui.hero("Simulator", "Long-term projections, savings goals and stress tests",
        chips=[f"Based on {ctx['label']}", f"Typical income {m(income_m)}/month", f"Typical spending {m(expense_m)}/month"])
ui.active_filters([f"Source: {ctx['label']}", f"Start: {ss['sm_start_mode']}",
                   f"Horizon: {ss['sm_years']} years",
                   f"Return {ss['sm_ret']:.1f}% · volatility {ss['sm_vol']:.1f}%",
                   "Today's money" if ss["sm_real"] else "Future money",
                   "Privacy on" if hide else "Amounts visible"])
st.caption(f"Source: {ctx['label']}. Simulator assumptions are independent of the Plan page unless you pick a saved plan.")

# =========================================================== wealth projection
ui.section("Wealth projection", "1,000 simulated futures")
with ui.card("Assumptions"):
    w1 = st.columns(4)
    start_mode = w1[0].radio("Start from", ["Net worth", "Invested accounts", "Custom"], key="sm_start_mode")
    w1[1].number_input(f"Custom start ({ui.CUR})", min_value=0.0, step=100.0, key="sm_start_custom",
                       disabled=start_mode != "Custom")
    contrib = w1[2].number_input(f"Yearly contribution ({ui.CUR})", min_value=0.0, step=100.0, key="sm_contrib",
                                 help="What you add over a whole year. By default: what your plan puts in investments per year.")
    growth = w1[3].number_input("Contribution growth (%/yr)", min_value=0.0, max_value=30.0, step=0.5, key="sm_growth",
                                help="Raise the yearly contribution by this much every year.")
    w2 = st.columns(4)
    ret = w2[0].number_input("Expected return (%/yr)", min_value=-10.0, max_value=30.0, step=0.5, key="sm_ret")
    vol = w2[1].number_input("Volatility (%/yr)", min_value=0.0, max_value=60.0, step=0.5, key="sm_vol",
                             help="How bumpy returns are. Around 15% for a stock fund, 5% for bonds.")
    years = w2[2].slider("Horizon (years)", 1, 50, key="sm_years")
    infl = w2[3].number_input("Inflation (%/yr)", min_value=0.0, max_value=20.0, step=0.1, key="sm_infl")
    w3 = st.columns(2)
    real = w3[0].toggle("Show in today's money (remove inflation)", key="sm_real")
    target = w3[1].number_input(f"Target ({ui.CUR}, 0 = none)", min_value=0.0, step=1000.0, key="sm_target",
                                help="In today's money. Drawn as a line that rises with inflation when amounts are shown in future money. "
                                     "By default: the financial-independence number at a 4% withdrawal rate.")
start_cap = {"Net worth": pos["net_worth"], "Invested accounts": invested_now,
             "Custom": ss["sm_start_custom"]}[start_mode]
mc = run_mc(float(start_cap), float(contrib), float(growth), float(ret), float(vol), int(years), float(infl), bool(real))
fin = mc["final"]
# Targets are in today's money: in future money they are raised by inflation, year by year.
infl_path = np.ones(years + 1) if real else (1 + infl / 100.0) ** np.arange(years + 1)
target_path = target * infl_path if target > 0 else None
p_hit = float(np.mean(fin >= target_path[-1])) if target > 0 else math.nan
gained = mc["p50"][-1] - mc["contributed"][-1]
with ui.card(f"Where your money could be in {years} years" + (" · today's money" if real else "")):
    if hide:
        ui.private_note()
    else:
        st.plotly_chart(ui.fan_chart(mc, target_path), key="fan", config=CFG)
    st.caption("Every year the return is random. The bands show where 80% (light) and 50% (dark) of the "
               "simulated futures end. The dotted line is the plan with no volatility: the median sits "
               "slightly below it because losses hurt more than gains of the same size help.")
    ui.formula_caption(f"Volatility drag: the smooth path ends at {m(mc['det'][-1])}, the median at "
                       f"{m(mc['p50'][-1])} — a difference of {m(mc['det'][-1] - mc['p50'][-1])}.")
ui.md(ui.tiles_html([
    ui.tile("Median outcome", m(mc["p50"][-1]), f"in {years} years", accent=ui.C_NW),
    ui.tile("Likely range", f"{m(mc['p10'][-1])} – {m(mc['p90'][-1])}" if not hide else ui.MASK, "10th to 90th percentile",
            accent=ui.C_PURPLE),
    ui.tile("Contributed", m(mc["contributed"][-1]), f"market growth {m(gained, sign=True)} (median)", accent=ui.C_TEAL),
    ui.tile("Chance of reaching the target", ui.fmt(p_hit, "pct") if target > 0 else "—",
            f"target {m(target)}" if target > 0 else "set a target above", accent=ui.C_GOLD),
], cols=4))

# =========================================================== goals
ui.section("Goals", "how much to put aside each month")
today = dt.date.today()
saved_goals = cfg.get("goals") or []
g_df = pd.DataFrame([{"Goal": g.get("name", ""), "Target": g.get("target"), "By": pd.to_datetime(g.get("date")).date()
                      if g.get("date") else None, "Saved": g.get("saved", 0.0), "Return %/yr": g.get("ret", 0.0)}
                     for g in saved_goals], columns=["Goal", "Target", "By", "Saved", "Return %/yr"])
for c in ("Target", "Saved", "Return %/yr"):
    g_df[c] = pd.to_numeric(g_df[c], errors="coerce")
gl, gr = st.columns([5, 6])
with gl:
    with ui.card("Your goals"):
        ge = st.data_editor(
            g_df, key="sm_goals", hide_index=True, num_rows="dynamic",
            column_config={
                "Goal": cc.TextColumn("Goal", help="A trip, a car, a deposit…"),
                "Target": cc.NumberColumn(f"Target ({ui.CUR})", min_value=0.0, step=100.0, format="%.2f"),
                "By": cc.DateColumn("By", help="When you want it."),
                "Saved": cc.NumberColumn(f"Saved so far ({ui.CUR})", min_value=0.0, step=50.0, format="%.2f"),
                "Return %/yr": cc.NumberColumn("Return %/yr", min_value=-10.0, max_value=30.0, step=0.5, format="%.1f",
                                               help="What the money earns while it waits (savings account, fund…).")})
goals, rows = [], []
for _, r in ge.iterrows():
    name, tgt, by = str(r["Goal"] or "").strip(), P._f(r["Target"]), r["By"]
    if not name or tgt <= 0 or by is None or pd.isna(by):
        continue
    by = pd.to_datetime(by).date()
    saved_, rt = P._f(r["Saved"]), P._f(r["Return %/yr"])
    goals.append({"name": name, "target": tgt, "date": by.isoformat(), "saved": saved_, "ret": rt})
    n = (by.year - today.year) * 12 + (by.month - today.month)
    req = sim.required_monthly(tgt, saved_, n, rt)
    done = saved_ >= tgt
    due = not done and n <= 0
    note = ("Funded" if done else "Date has passed" if by < today else "Due this month" if n <= 0
            else f"{n} months left")
    rows.append({"name": name, "target": tgt, "saved": saved_, "required": 0.0 if done or due else (req if math.isfinite(req) else 0.0),
                 "sub": f"by {by:%b %Y}", "note": note, "done": done, "due": due,
                 "color": ui.C_INCOME if done else (ui.C_EXPENSE if due else ui.C_NW)})
settings.update(goals=goals)
with gr:
    with ui.card("Progress and what each goal needs"):
        ui.md(ui.goal_rows_html(rows, hide))
need = sum(g["required"] for g in rows)
due_gap = sum(max(g["target"] - g["saved"], 0.0) for g in rows if g.get("due"))
surplus_m = ctx["surplus_m"]
monthly_gap = max(need - max(surplus_m, 0.0), 0.0)
fits = due_gap <= 0.005 and monthly_gap <= 0.005
if fits:
    verdict, verdict_sub = "Within reach", "your surplus covers every goal"
elif due_gap > 0:
    verdict = f"Short by {m(due_gap)}" if not hide else "Short"
    verdict_sub = "a goal is due now: add the money or move the date"
else:
    verdict = f"Short by {m(monthly_gap)}" if not hide else "Short"
    verdict_sub = "per month: adjust dates, amounts or the plan"
ui.md(ui.tiles_html([
    ui.tile("Needed per month", m(need), f"for {len([g for g in rows if not g.get('done')])} open goal(s)", accent=ui.C_NW),
    ui.tile("Surplus available per month", m(surplus_m, sign=True), f"from {ctx['label']}", accent=ui.C_INCOME),
    ui.tile("Verdict", verdict, verdict_sub,
            cls="" if hide else ("pos" if fits else "neg"), accent=ui.C_GOLD),
], cols=3))

# =========================================================== stress test
ui.section("Stress test", "what if the worst happens")
with ui.card("Scenario"):
    s1 = st.columns(4)
    drop = s1[0].slider("Income drops by (%)", 0, 100, key="st_drop", help="100% = you lose your income.")
    dur = s1[1].slider("…for how many months", 0, 36, key="st_dur", help="0 = for the whole period.")
    shock = s1[2].slider("Spending changes by (%)", -30, 100, key="st_shock", help="A permanent change, for example +10% in a crisis.")
    hor = s1[3].slider("Look ahead (months)", 12, 60, key="st_horizon")
cash = pos["liquid"]
p_plan = sim.cash_path(cash, hor, income_m, expense_m)
p_stress = sim.cash_path(cash, hor, income_m, expense_m, drop, dur, shock)
p_worst = sim.cash_path(cash, hor, worst_income, worst_expense)
lasts, lasts_w = sim.cash_lasts(p_stress), sim.cash_lasts(p_worst)
low_t = int(p_stress.argmin())
with ui.card("Your cash, month by month"):
    if hide:
        ui.private_note()
    else:
        st.plotly_chart(ui.cash_paths_chart([("Typical month", p_plan, ui.C_NW, "solid"),
                                             ("Your scenario", p_stress, ui.C_GOLD, "solid"),
                                             ("Worst case", p_worst, ui.C_EXPENSE, "dot")]), key="cash", config=CFG)
    st.caption(f"Starts from your liquid funds ({m(cash)}). Typical month = median income {m(income_m)} and spending "
               f"{m(expense_m)}. Worst case = income {m(worst_income)} and spending {m(worst_expense)} every month "
               "(one standard deviation against you).")
ui.md(ui.tiles_html([
    ui.tile("Your scenario: cash lasts", "Never within the period" if math.isinf(lasts) else ui.fmt(lasts, "months"),
            "the balance stays above zero" if math.isinf(lasts) else "until the balance reaches zero",
            cls="pos" if math.isinf(lasts) else "neg", accent=ui.C_GOLD),
    ui.tile("Lowest point", m(float(p_stress.min())), f"in month {low_t}", accent=ui.C_PURPLE),
    ui.tile("Worst case: cash lasts", "Never within the period" if math.isinf(lasts_w) else ui.fmt(lasts_w, "months"),
            "even with income and spending against you" if math.isinf(lasts_w) else "until the balance reaches zero",
            cls="pos" if math.isinf(lasts_w) else "neg", accent=ui.C_EXPENSE),
], cols=3))

st.write("")
with ui.card("What if your spending changes?"):
    basis = pos["availability"] if pos["runway_basis"] == "Availability" else pos["liquid"]
    if basis > 0 and expense_m > 0:
        st.plotly_chart(ui.runway_sensitivity(basis, expense_m), key="sens", config=CFG)
        st.caption(f"Runway on {pos['runway_basis'].lower()} for spending between 50% and 200% of today's. "
                   "The dot is where you are; green is 12+ months, amber 6–12, red under 6.")
    else:
        st.caption("Needs a positive balance and positive monthly spending.")

# =========================================================== financial independence
ui.section("Financial independence", "when your money can pay for your life")
fi_c = st.columns([1, 3])
swr = fi_c[0].slider("Withdrawal rate (%/yr)", 2.0, 6.0, step=0.1, key="fi_swr",
                     help="How much of the pot you can spend each year. 4% is the classic rule of thumb.")
annual_spend = expense_m * 12
fi_number = annual_spend / (swr / 100.0) if swr > 0 else math.inf
progress = start_cap / fi_number if fi_number > 0 and not math.isinf(fi_number) else 0.0
years_fi = sim.years_to_target(fi_number, start_cap, contrib, ret, growth, 0.0 if real else infl) if fi_number > 0 else math.inf
p_fi = float(np.mean(fin >= fi_number * infl_path[-1])) if fi_number > 0 else math.nan
ui.md(ui.tiles_html([
    ui.tile("Independence number", m(fi_number), f"{m(annual_spend)} a year ÷ {swr:.1f}%", accent=ui.C_NW),
    ui.tile("Reached so far", ui.fmt(progress, "pct"), f"{m(start_cap)} of the number", accent=ui.C_TEAL,
            extra=ui.meter_html(progress, ui.C_TEAL, "progress", f"{min(progress, 1) * 100:.0f}%")),
    ui.tile("Time to get there", "More than 200 years" if math.isinf(years_fi) else
            ("Already there" if years_fi == 0 else f"{years_fi:.1f} years"),
            "no volatility, with your yearly contribution", accent=ui.C_GOLD),
    ui.tile(f"Chance by year {years}", ui.fmt(p_fi, "pct"), "in the simulation above", accent=ui.C_INCOME),
], cols=4))
st.caption("Based on your typical spending. A rule of thumb, not advice: real returns, taxes and spending change.")

# ---------------- help ----------------
ui.glossary()

# ---------------- printable report ----------------
F = lambda x, **kw: ui.fmt(x, "money", **kw)
n_open = len([g for g in rows if not g.get("done")])
report = R.simulator_report({
    "hide": hide, "source": ctx["label"], "mc": mc, "target": target, "target_path": target_path,
    "assumptions": pd.DataFrame([
        {"Setting": "Starting capital", "Value": f"{start_mode} · {F(start_cap)}"},
        {"Setting": "Yearly contribution", "Value": f"{F(contrib)} (growing {growth:.1f}% a year)"},
        {"Setting": "Expected return / volatility", "Value": f"{ret:.1f}% / {vol:.1f}% a year"},
        {"Setting": "Horizon", "Value": f"{years} years"},
        {"Setting": "Inflation", "Value": f"{infl:.1f}% a year" + (" · amounts in today's money" if real else "")},
        {"Setting": "Target", "Value": F(target) if target > 0 else "none"}]),
    "fan_title": f"Where your money could be in {years} years" + (" · today's money" if real else ""),
    "wealth_tiles": [("Median outcome", F(mc["p50"][-1]), f"in {years} years", sc.NETWORTH),
                     ("Likely range", f"{F(mc['p10'][-1])} – {F(mc['p90'][-1])}", "10th to 90th percentile", sc.PURPLE),
                     ("Contributed", F(mc["contributed"][-1]), f"market growth {F(gained, sign=True)} (median)", sc.TEAL),
                     ("Chance of reaching the target", ui.fmt(p_hit, "pct") if target > 0 else "—",
                      f"target {F(target)}" if target > 0 else "no target set", sc.GOLD)],
    "goals": rows,
    "goal_tiles": [("Needed per month", F(need), f"for {n_open} open goal(s)", sc.NETWORTH),
                   ("Surplus available per month", F(surplus_m, sign=True), f"from {ctx['label']}", sc.INCOME),
                   ("Verdict", "Within reach" if fits else f"Short by {F(due_gap if due_gap > 0 else monthly_gap)}",
                    "your surplus covers every goal" if fits else
                    ("a goal is due now: add the money or move the date" if due_gap > 0
                     else "per month: adjust dates, amounts or the plan"),
                    sc.GOLD, "pos" if fits else "neg")],
    "paths": [("Typical month", p_plan, sc.NETWORTH, "solid"), ("Your scenario", p_stress, sc.GOLD, "solid"),
              ("Worst case", p_worst, sc.EXPENSE, "dot")],
    "stress_note": f"Starts from your liquid funds ({F(cash)}). Your scenario: income down {drop}% for "
                   f"{'the whole period' if dur == 0 else f'{dur} months'}, spending {shock:+d}%. Worst case: income "
                   f"{F(worst_income)} and spending {F(worst_expense)} every month.",
    "stress_tiles": [("Your scenario: cash lasts", "Never within the period" if math.isinf(lasts) else ui.fmt(lasts, "months"),
                      "the balance stays above zero" if math.isinf(lasts) else "until the balance reaches zero", sc.GOLD,
                      "pos" if math.isinf(lasts) else "neg"),
                     ("Lowest point", F(float(p_stress.min())), f"in month {low_t}", sc.PURPLE),
                     ("Worst case: cash lasts", "Never within the period" if math.isinf(lasts_w) else ui.fmt(lasts_w, "months"),
                      "even with income and spending against you" if math.isinf(lasts_w) else "until the balance reaches zero",
                      sc.EXPENSE, "pos" if math.isinf(lasts_w) else "neg")],
    "sens": (basis, expense_m) if basis > 0 and expense_m > 0 else None,
    "fi_tiles": [("Independence number", F(fi_number), f"{F(annual_spend)} a year ÷ {swr:.1f}%", sc.NETWORTH),
                 ("Reached so far", ui.fmt(progress, "pct"), f"{F(start_cap)} of the number", sc.TEAL),
                 ("Time to get there", "More than 200 years" if math.isinf(years_fi) else
                  ("Already there" if years_fi == 0 else f"{years_fi:.1f} years"), "no volatility, with your yearly contribution", sc.GOLD),
                 (f"Chance by year {years}", ui.fmt(p_fi, "pct"), "in the simulation above", sc.INCOME)]})
ui.print_report(report, "simulator_report.html", "Simulator", hide)

ss["_sm_mirror"] = {k: ss[k] for k in SM_KEYS if k in ss}
