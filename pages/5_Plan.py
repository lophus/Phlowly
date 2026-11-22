import json
import math
import zlib

import pandas as pd
import streamlit as st

import db
import kpis
import logic
import planning as P
import plans
import reports as R
import settings
import svgcharts as sc
import ui

st.set_page_config(page_title="Plan", page_icon=":material/event_note:", layout="wide")
ui.inject_css()
CFG = {"displayModeBar": False}
cc = st.column_config

deltas, flows, all_days = db.load_all()
ui.currency_warning(db.book_currencies(deltas))
cfg = settings.load()
store = plans.load()

# ---------------- where you stand today ----------------
pos = logic.position(deltas, cfg["liquid_assets"], cfg["runway_basis"])

NOW_M = pd.Timestamp.now().to_period("M")
START_OPTS = [str(NOW_M + i) for i in range(0, 13)]
PERIODS = list(P.BASE_PERIODS)
MODE_KEY = {v: k for k, v in P.MODES.items()}


def apply(params: dict):
    """Load a scenario into the widgets. Must run before the widgets are created."""
    b = params["base"]
    ss = st.session_state
    ss["pl_period"] = b["period"] if b["period"] in PERIODS else PERIODS[1]
    ss["pl_stat"] = "Mean"
    ss["pl_level"] = b["level"] if b["level"] in ("Macro", "Detailed") else "Macro"
    ss["pl_excl"] = bool(b["exclude_current"])
    ss["pl_inc"], ss["pl_exp"] = float(params["levers"]["income_pct"]), float(params["levers"]["expense_pct"])
    ss["pl_start"] = params["start"]
    ss["pl_pattern"] = params["pattern"] if params["pattern"] in ("Historical", "Flat") else "Historical"
    ss["pl_ef"] = float(params.get("ef_months", 6.0))
    ss["adj"] = {k: dict(v) for k, v in (params.get("adjust") or {}).items()}
    ss["oneoffs"] = [dict(o) for o in (params.get("oneoffs") or [])]
    ss["alloc"] = [dict(a) for a in (params.get("alloc") or P.DEFAULT_ALLOC)]
    ss["pl_ver"] = ss.get("pl_ver", 0) + 1


# Streamlit forgets the state of widgets that are not drawn during a run, e.g. while you visit another
# page. A mirror kept in plain session keys lets us restore everything when you come back.
PL_KEYS = ["pl_sel", "pl_period", "pl_stat", "pl_level", "pl_excl", "pl_inc", "pl_exp", "pl_start",
           "pl_pattern", "pl_ef", "pl_which", "pl_name"]
PL_REQUIRED = ["pl_period", "pl_stat", "pl_level", "pl_excl", "pl_inc", "pl_exp", "pl_start", "pl_pattern", "pl_ef"]
for _k, _v in st.session_state.get("_pl_mirror", {}).items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ---------------- sidebar: privacy + scenario picker ----------------
with st.sidebar:
    st.header("Filters")
    hide = ui.sidebar_privacy()
    st.header("Scenario")
    names = list(store["plans"])
    options = ["New plan"] + names
    if "_pl_pending" in st.session_state:          # set by Save / Delete, applied before the widget exists
        st.session_state["pl_sel"], st.session_state["_pl_loaded"] = st.session_state.pop("_pl_pending")
    idx = options.index(store["active"]) if store["active"] in options else 0
    if st.session_state.get("pl_sel") not in options:      # e.g. the plan was deleted meanwhile
        st.session_state.pop("pl_sel", None)
    sel = st.selectbox("Scenario", options, key="pl_sel", **({} if "pl_sel" in st.session_state else {"index": idx}))

if st.session_state.get("_pl_loaded") != sel or any(k not in st.session_state for k in PL_REQUIRED):
    apply(store["plans"].get(sel) or P.default_params(P.default_start()))
    st.session_state["pl_name"] = sel if sel in names else "My plan"
    st.session_state["_pl_loaded"] = sel

ss = st.session_state
start_opts = sorted(set(START_OPTS + [ss["pl_start"]]))

# ---------------- baseline from history (follows the current widget values) ----------------
months = P.base_months(flows, ss["pl_period"], ss["pl_excl"])
base = P.baseline(flows, months, ss["pl_level"])
now_base = pos["availability"] if pos["runway_basis"] == "Availability" else pos["liquid"]
k_hist = kpis.compute(base["monthly"], pos["availability"], pos["liquid"], now_base)


def m(x, **kw):
    return ui.MASK if hide else ui.fmt(x, "money", **kw)


def pct_pts(a, b):
    return "n/a" if any(isinstance(v, float) and math.isnan(v) for v in (a, b)) else f"{(b - a) * 100:+.2f} pp"


ui.hero("Financial plan", "A budget for the year ahead: baseline from your history, your changes, and where the surplus goes",
        chips=[sel if sel in names else "Unsaved plan",
               f"{P.month_label(pd.Period(ss['pl_start'], 'M'))} → "
               f"{P.month_label(pd.Period(ss['pl_start'], 'M') + 11)}",
               f"Baseline: {ss['pl_period'].lower()} ({len(months)} months)"])
ui.active_filters([sel if sel in names else "Unsaved plan",
                   f"Baseline: {ss['pl_period']}", f"Level: {ss['pl_level']}",
                   "Current month excluded" if ss["pl_excl"] else "Current month included",
                   "Privacy on" if hide else "Amounts visible"])
st.caption(f"Source: {ss['pl_period']} · mean of monthly amounts · {ss['pl_level']} · "
           f"start {ss['pl_start']} · current month {'excluded' if ss['pl_excl'] else 'included'}.")

# ---------------- starting point ----------------
ui.section("Starting point", "what the plan builds on")
ui.md(ui.tiles_html([
    ui.tile("Net worth", m(pos["net_worth"]), "today", accent=ui.C_NW),
    ui.tile("Liquid funds", m(pos["liquid"]), f"{ui.fmt(k_hist['liquidity_pct'], 'pct')} of availability", accent=ui.C_TEAL),
    ui.tile("Typical monthly income", m(k_hist["median_income"]), "median over the baseline", accent=ui.C_INCOME),
    ui.tile("Typical monthly spending", m(k_hist["median_burn"]), "median over the baseline", accent=ui.C_EXPENSE),
    ui.tile("Runway today", ui.fmt(k_hist["runway"], "months"), f"{pos['runway_basis'].lower()} ÷ median burn", accent=ui.C_GOLD),
], cols=5))

# ---------------- assumptions ----------------
ui.section("Assumptions")
with ui.card("Baseline and levers"):
    a1 = st.columns([2, 2, 2, 2])
    a1[0].selectbox("History used as baseline", PERIODS, key="pl_period")
    a1[1].radio("Category detail", ["Macro", "Detailed"], horizontal=True, key="pl_level")
    pattern = a1[2].radio("Month-to-month pattern", ["Historical", "Flat"], horizontal=True, key="pl_pattern",
                          help="Historical repeats the shape of your past year: the same months get the same peaks and dips (including one-off peaks). Flat spreads the year evenly.")
    a1[3].toggle("Ignore the current month", key="pl_excl",
                 help="The month in progress is incomplete and skews the average.")
    a2 = st.columns(3)
    inc_pct = a2[0].number_input("Income change vs baseline (%)", min_value=-100.0, max_value=300.0, step=0.5, key="pl_inc",
                                 help="Applied to every income category (a raise, a lost client…).")
    exp_pct = a2[1].number_input("Expense change vs baseline (%)", min_value=-100.0, max_value=300.0, step=0.5, key="pl_exp",
                                 help="Applied to every expense category (inflation, a new lifestyle…).")
    start = a2[2].selectbox("Plan starts in", start_opts, key="pl_start",
                            format_func=lambda s: P.month_label(pd.Period(s, "M")))

months = P.base_months(flows, ss["pl_period"], ss["pl_excl"])
base = P.baseline(flows, months, ss["pl_level"])
if base["table"].empty:
    st.warning("There is no income or expense history in the selected baseline period.")
    st.stop()
plan_labels = [P.month_label(p) for p in P.plan_months(start)]

# ---------------- budget editors ----------------
ui.section("Budget", "yearly amounts · edit the cells with a pencil")
sig = zlib.crc32(repr((ss["pl_period"], ss["pl_stat"], ss["pl_level"], ss["pl_excl"])).encode()) % 10**6
adj = dict(ss["adj"])
detailed = ss["pl_level"] == "Detailed"
cols = st.columns(2)
for col, acct_type, title, color in [(cols[0], "EXPENSE", "Expenses", ui.C_EXPENSE), (cols[1], "INCOME", "Income", ui.C_INCOME)]:
    t = base["table"][base["table"]["acct_type"] == acct_type]
    with col:
        with ui.card(f"{title} · baseline and adjustments"):
            data = {"Category": t["name"].to_list()}
            if detailed:
                data = {"Group": t["group"].to_list(), **data}
            data.update({"Baseline /mo": t["monthly"].to_list(), "Baseline /yr": t["annual"].to_list(),
                         "Adjust %": [P._f((adj.get(k) or {}).get("pct")) for k in t["key"]],
                         "Override /yr": [(adj.get(k) or {}).get("override") for k in t["key"]]})
            df = pd.DataFrame(data)
            df["Override /yr"] = pd.to_numeric(df["Override /yr"], errors="coerce")
            ed = st.data_editor(
                df, key=f"ed_{acct_type}_{ss['pl_ver']}_{sig}", hide_index=True, height=min(44 + 35 * len(df), 440),
                disabled=[c for c in ("Group", "Category", "Baseline /mo", "Baseline /yr") if c in df],
                column_config={
                    "Baseline /mo": cc.NumberColumn("Baseline / month", format="%.2f"),
                    "Baseline /yr": cc.NumberColumn("Baseline / year", format="%.2f"),
                    "Adjust %": cc.NumberColumn("Adjust (%)", min_value=-100.0, max_value=500.0, step=0.5,
                                                format="%.1f", help="Change this category by a percentage."),
                    "Override /yr": cc.NumberColumn("Fixed / year", min_value=0.0, step=10.0, format="%.2f",
                                                    help="Set the yearly amount yourself. Leave empty to use "
                                                         "baseline + levers + adjustment.")})
            for k, pc, ov in zip(t["key"], ed["Adjust %"], ed["Override /yr"]):
                adj[k] = {"pct": P._f(pc), "override": None if pd.isna(ov) else float(ov)}
ss["adj"] = adj

with ui.card("One-off and new items"):
    oo_df = pd.DataFrame(ss["oneoffs"] or [], columns=["name", "type", "amount", "when"]).rename(
        columns={"name": "Name", "type": "Type", "amount": "Amount", "when": "When"})
    oo_df["Amount"] = pd.to_numeric(oo_df["Amount"], errors="coerce")
    oo = st.data_editor(
        oo_df, key=f"ed_oo_{ss['pl_ver']}", hide_index=True, num_rows="dynamic",
        column_config={
            "Name": cc.TextColumn("Name", help="For example: Holiday, New car, Bonus"),
            "Type": cc.SelectboxColumn("Type", options=["Expense", "Income"], required=True),
            "Amount": cc.NumberColumn("Amount", min_value=0.0, step=10.0, format="%.2f"),
            "When": cc.SelectboxColumn("When", options=[P.EVERY] + plan_labels, required=True,
                                       help="A month of the plan, or every month for a new recurring item.")})
    st.caption("One-off items fall in the month you choose. Pick “Every month” for a new recurring cost or income.")
oneoffs = [{"name": str(r["Name"] or "").strip(), "type": r["Type"], "amount": P._f(r["Amount"]), "when": r["When"]}
           for _, r in oo.iterrows() if P._f(r["Amount"]) > 0 and isinstance(r["Type"], str)]
ss["oneoffs"] = oneoffs

params = {"base": {"period": ss["pl_period"], "stat": ss["pl_stat"], "level": ss["pl_level"],
                   "exclude_current": ss["pl_excl"]},
          "levers": {"income_pct": inc_pct, "expense_pct": exp_pct}, "start": start, "pattern": pattern,
          "ef_months": ss["pl_ef"],
          "adjust": {k: v for k, v in adj.items() if v["override"] is not None or abs(v["pct"]) > 1e-9},
          "oneoffs": oneoffs, "alloc": ss["alloc"]}
bud = P.budget(params, base)
tot = bud["totals"]
if bud["ignored"]:
    st.warning("These items fall outside the plan period and are ignored: " + ", ".join(bud["ignored"]))

# ---------------- result ----------------
ui.section("The budget", "baseline versus plan")
sur = tot["surplus"]
ui.md(ui.tiles_html([
    ui.tile("Planned income", m(tot["income"]), f"{m(tot['income'] - tot['baseline_income'], sign=True)} vs baseline", accent=ui.C_INCOME),
    ui.tile("Planned expenses", m(tot["expense"]), f"{m(tot['expense'] - tot['baseline_expense'], sign=True)} vs baseline", accent=ui.C_EXPENSE),
    ui.tile("Planned surplus", m(sur, sign=True), f"{m(sur / 12, sign=True)} per month",
            cls="" if hide else ("pos" if sur >= 0 else "neg"), accent=ui.C_NW),
    ui.tile("Savings rate", ui.fmt(tot["rate"], "pct"), f"{pct_pts(tot['baseline_rate'], tot['rate'])} vs baseline", accent=ui.C_GOLD),
], cols=4))
st.write("")
r1, r2 = st.columns(2)
with r1:
    with ui.card("From baseline surplus to planned surplus"):
        if hide:
            ui.private_note()
        else:
            st.plotly_chart(ui.bridge_chart(bud["bridge"]), key="bridge", config=CFG)
with r2:
    with ui.card("Where the plan differs, by category"):
        which = st.radio("Show", ["Expenses", "Income"], horizontal=True, label_visibility="collapsed", key="pl_which")
        tb = bud["table"]
        tb = tb[tb["acct_type"] == ("EXPENSE" if which == "Expenses" else "INCOME")]
        if hide:
            ui.private_note()
        else:
            st.plotly_chart(ui.category_compare(tb, ui.C_EXPENSE if which == "Expenses" else ui.C_INCOME),
                            key="catcmp", config=CFG)

tb = bud["table"]
lines = [{"Type": "Expense" if r.acct_type == "EXPENSE" else "Income", "Category": r.name,
          "Baseline / year": m(r.annual), "Plan / year": m(r.planned), "Change": m(r.delta, sign=True)}
         for r in tb.itertuples()]
lines += [{"Type": "Total", "Category": "Income", "Baseline / year": m(tot["baseline_income"]),
           "Plan / year": m(tot["income"]), "Change": m(tot["income"] - tot["baseline_income"], sign=True)},
          {"Type": "Total", "Category": "Expenses", "Baseline / year": m(tot["baseline_expense"]),
           "Plan / year": m(tot["expense"]), "Change": m(tot["expense"] - tot["baseline_expense"], sign=True)},
          {"Type": "Total", "Category": "Surplus", "Baseline / year": m(tot["baseline_surplus"], sign=True),
           "Plan / year": m(sur, sign=True), "Change": m(sur - tot["baseline_surplus"], sign=True)}]
budget_df = pd.DataFrame(lines)
with ui.card("Budget table"):
    ui.md(ui.table_html(budget_df, num_cols=("Baseline / year", "Plan / year", "Change"), cls="dtable", total_last=True))
    st.caption("Expenses and income are both shown as positive amounts. Surplus = income − expenses.")

# ---------------- allocation ----------------
ui.section("Where the surplus goes", "give every euro a job")
left, right = st.columns([5, 6])
with left:
    with ui.card("Buckets"):
        st.number_input("Emergency fund target (months of spending)", min_value=0.0, max_value=36.0, step=0.5, key="pl_ef")
        al_df = pd.DataFrame(ss["alloc"] or [], columns=["name", "kind", "mode", "value", "ret", "current"])
        al_df["mode"] = al_df["mode"].map(P.MODES).fillna(P.MODES["%"])
        al_df = al_df.rename(columns={"name": "Bucket", "kind": "Kind", "mode": "How", "value": "Value",
                                      "ret": "Return %/yr", "current": "Already there"})
        for c in ("Value", "Return %/yr", "Already there"):
            al_df[c] = pd.to_numeric(al_df[c], errors="coerce")
        ale = st.data_editor(
            al_df, key=f"ed_al_{ss['pl_ver']}", hide_index=True, num_rows="dynamic",
            column_config={
                "Bucket": cc.TextColumn("Bucket"),
                "Kind": cc.SelectboxColumn("Kind", options=P.KINDS, required=True,
                                           help="Cash stays liquid. Invested grows but is not liquid. Debt pays a loan down (Return = its interest rate; Already there is ignored)."),
                "How": cc.SelectboxColumn("How", options=list(P.MODES.values()), required=True),
                "Value": cc.NumberColumn("Value", min_value=0.0, step=1.0, format="%.2f",
                                         help="A percentage of the surplus, or euros per month, depending on “How”."),
                "Return %/yr": cc.NumberColumn("Return %/yr", min_value=-50.0, max_value=50.0, step=0.5, format="%.1f"),
                "Already there": cc.NumberColumn("Already there", min_value=0.0, step=10.0, format="%.2f",
                                                 help="What this bucket already holds today.")})
        st.caption("Cash buckets stay liquid. Invested buckets stay in your accounts but are not liquid. "
                   "Debt repayments leave your cash and shrink the loan (net worth only gains the interest you avoid).")
alloc = [{"name": str(r["Bucket"] or "").strip(), "kind": r["Kind"] if r["Kind"] in P.KINDS else "Cash",
          "mode": MODE_KEY.get(r["How"], "%"), "value": P._f(r["Value"]), "ret": P._f(r["Return %/yr"]),
          "current": P._f(r["Already there"])} for _, r in ale.iterrows() if str(r["Bucket"] or "").strip()]
ss["alloc"] = alloc
params["alloc"], params["ef_months"] = alloc, ss["pl_ef"]
al = P.allocation(bud, alloc, pos, ss["pl_ef"])
ol = P.outlook(bud, al, base, pos)

with right:
    with ui.card("The plan for the surplus"):
        if sur <= 0:
            st.warning("The plan has no surplus: percentage buckets get nothing. Reduce expenses or raise income.")
        if al["over"]:
            st.error(f"Over-allocated by {m(-al['unalloc'])}: the buckets ask for more than the surplus. "
                     "The difference comes out of money you already have.")
        items = [(r["name"], r["annual"], ui.PALETTE[i % len(ui.PALETTE)]) for i, r in enumerate(al["rows"]) if r["annual"] > 0]
        if al["unalloc"] > 0.005:
            items.append(("Free cash", al["unalloc"], "#5E6875"))
        if hide:
            ui.private_note()
        elif items:
            ui.md(ui.segments_html(items, money_values=True))
        else:
            st.caption("Nothing allocated yet.")

rows = [{"Bucket": r["name"], "Kind": r["kind"], "Per month": m(r["monthly"]), "Per year": m(r["annual"]),
         "Growth": m(r["growth"], sign=True), "End of plan": m(r["end"])} for r in al["rows"]]
rows.append({"Bucket": "Free cash", "Kind": "Cash", "Per month": m(max(al["unalloc"], 0) / 12),
             "Per year": m(max(al["unalloc"], 0)), "Growth": m(0.0), "End of plan": "—"})
total_year = al["total"] + max(al["unalloc"], 0.0)
rows.append({"Bucket": "Total", "Kind": "", "Per month": m(total_year / 12), "Per year": m(total_year),
             "Growth": m(al["growth"], sign=True), "End of plan": ""})
alloc_df = pd.DataFrame(rows)
with ui.card("Buckets at a glance"):
    ui.md(ui.table_html(alloc_df, num_cols=("Per month", "Per year", "Growth", "End of plan"), cls="dtable", total_last=True))

# ---------------- expected KPIs ----------------
k0, k1 = ol["now"], ol["end"]
ui.section("What the plan delivers", "today versus the end of the plan")
g1, g2 = st.columns(2)
for col, title, key, val, sub in [(g1, "Runway today (months)", "g_now", k0["runway"], f"{pos['runway_basis']} ÷ median burn"),
                                  (g2, "Runway after the plan (months)", "g_end", k1["runway"], "with the plan's money and spending")]:
    with col:
        with ui.card(title):
            if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                ui.md(ui.tiles_html([ui.tile(title, ui.fmt(val, "months"), sub, accent=ui.C_TEAL)], cols=1, flat=True))
            else:
                ui.md(ui.gauge_svg(val, uid=key))
            ui.md(ui.status_pill_html(ui.runway_status(val)))
            st.caption(sub)
st.write("")
ef = al["ef"]
ui.md(ui.tiles_html([
    ui.tile("Savings rate", ui.fmt(k1["savings_rate"], "pct"), f"today {ui.fmt(k0['savings_rate'], 'pct')}", accent=ui.C_GOLD),
    ui.tile("Median monthly spending", m(k1["median_burn"]), f"today {m(k0['median_burn'])}", accent=ui.C_EXPENSE),
    ui.tile("Expense volatility", ui.fmt(k1["expense_vol"], "pct"), f"today {ui.fmt(k0['expense_vol'], 'pct')}", accent=ui.C_PURPLE),
    ui.tile("Net worth after the plan", m(al["net_worth_end"]), f"{m(al['net_worth_end'] - pos['net_worth'], sign=True)} in 12 months", accent=ui.C_NW),
], cols=4))
st.write("")

with ui.card("Today vs end of the plan"):
    def _delta(a, b, kind="money"):
        if hide:
            return ui.MASK
        if any(isinstance(v, float) and (math.isnan(v) or math.isinf(v)) for v in (a, b)):
            return "n/a"
        d = b - a
        if kind == "money":
            return m(d, sign=True)
        if kind == "pct":
            return f"{d * 100:+.2f} pp"
        return f"{d:+,.2f} months"

    cmp_rows = [
        {"KPI": "Savings rate", "Today": ui.fmt(k0["savings_rate"], "pct"),
         "After plan": ui.fmt(k1["savings_rate"], "pct"),
         "Change": pct_pts(k0["savings_rate"], k1["savings_rate"])},
        {"KPI": "Median monthly spending", "Today": m(k0["median_burn"]),
         "After plan": m(k1["median_burn"]),
         "Change": _delta(k0["median_burn"], k1["median_burn"])},
        {"KPI": "Expense volatility", "Today": ui.fmt(k0["expense_vol"], "pct"),
         "After plan": ui.fmt(k1["expense_vol"], "pct"),
         "Change": _delta(k0["expense_vol"], k1["expense_vol"], "pct")},
        {"KPI": "Runway (months)", "Today": ui.fmt(k0["runway"], "months"),
         "After plan": ui.fmt(k1["runway"], "months"),
         "Change": _delta(k0["runway"], k1["runway"], "months")},
        {"KPI": "Net worth", "Today": m(pos["net_worth"]),
         "After plan": m(al["net_worth_end"]),
         "Change": _delta(pos["net_worth"], al["net_worth_end"])},
        {"KPI": "Liquid funds", "Today": m(pos["liquid"]),
         "After plan": m(al["liquid_end"]),
         "Change": _delta(pos["liquid"], al["liquid_end"])},
        {"KPI": "Emergency cover (months)", "Today": ui.fmt(ef["coverage_now"], "months"),
         "After plan": ui.fmt(ef["coverage_end"], "months"),
         "Change": _delta(ef["coverage_now"], ef["coverage_end"], "months")},
    ]
    ui.md(ui.table_html(pd.DataFrame(cmp_rows), cls="dtable"))
    ui.formula_caption("Change = end of plan − today. A rising runway or cover is good; rising spending is not.")

with ui.card("Emergency fund"):
    cover_end = ef["coverage_end"]
    frac = (min(cover_end / ef["months"], 1.0) if ef["months"] > 0 and not math.isinf(cover_end) else 1.0)
    c1, c2 = st.columns([2, 3], vertical_alignment="center")
    ui.md(ui.tiles_html([ui.tile("Cover after the plan", ui.fmt(cover_end, "months"),
                                 f"today {ui.fmt(ef['coverage_now'], 'months')} · target {ef['months']:.1f} months",
                                 accent=ui.C_TEAL, extra=ui.meter_html(frac, ui.C_TEAL, "of the target",
                                                                       f"{frac * 100:.0f}%"))], cols=1, flat=True), c1)
    if ef["gap_end"] <= 0.005:
        msg = "Target reached by the end of the plan."
    elif math.isinf(ef["months_to_fill"]):
        msg = "No money goes to cash buckets, so the target is not reached."
    else:
        msg = f"At this pace the target is reached in about {ef['months_to_fill']:.0f} months."
    c2.markdown(f"**Target:** {m(ef['target'])} ({ef['months']:.1f} months of planned spending).  \n"
                f"**Still missing after the plan:** {m(ef['gap_end'])}.  \n{msg}")

# ---------------- month by month ----------------
ui.section("Month by month")
mo = bud["monthly"]
with ui.card("Planned cash flow"):
    if hide:
        ui.private_note()
    else:
        st.plotly_chart(ui.month_chart(mo, al["cash_path"]), key="months", config=CFG)
mrows = [{"Month": P.month_label(p), "Income": m(r.income), "Expenses": m(r.expense), "Net": m(r.net, sign=True),
          "Cash after allocation": m(c)} for (p, r), c in zip(mo.iterrows(), al["cash_path"])]
mrows.append({"Month": "Year", "Income": m(tot["income"]), "Expenses": m(tot["expense"]), "Net": m(sur, sign=True),
              "Cash after allocation": m(al["cash_path"][-1])})
month_df = pd.DataFrame(mrows)
with ui.card("Month table"):
    ui.md(ui.table_html(month_df, num_cols=("Income", "Expenses", "Net", "Cash after allocation"), cls="dtable", total_last=True))

# ---------------- scenarios ----------------
ui.section("Scenarios", "compare saved plans side by side")
cache = {}


def base_for(p):
    b = p["base"]
    k = (b["period"], b["level"], b["exclude_current"])
    if k not in cache:
        cache[k] = P.baseline(flows, P.base_months(flows, b["period"], b["exclude_current"]), b["level"])
    return cache[k]


if sel == "New plan":
    cands = {"Current (editing)": params, **store["plans"]}
elif json.dumps(params, sort_keys=True, default=str) != json.dumps(store["plans"][sel], sort_keys=True, default=str):
    cands = {"Unsaved changes": params, **store["plans"]}
else:
    cands = dict(store["plans"])
evals = {n: P.evaluate(p, base_for(p), pos)["summary"] for n, p in cands.items()}
FMT = {"Savings rate": "pct", "Runway after plan (months)": "months", "Emergency fund coverage (months)": "months"}
cmp_rows = []
for metric in next(iter(evals.values())):
    row = {"Metric": metric}
    for n, s_ in evals.items():
        v = s_[metric]
        row[n] = ui.MASK if (hide and FMT.get(metric) is None) else ui.fmt(v, FMT.get(metric, "money"), sign=metric == "Surplus")
    cmp_rows.append(row)
with ui.card("Scenario comparison · availability"):
    ui.md(ui.table_html(pd.DataFrame(cmp_rows), num_cols=tuple(cands), cls="dtable"))
    fans = {name: P.scenario_fan(p, base_for(p), pos, seed=zlib.crc32(name.encode()) % (2**31 - 1))
            for name, p in cands.items()}
    month_labels = ["Now"] + [P.month_label(p) for p in bud["months"]]
    if hide:
        ui.private_note()
    else:
        st.caption("**Expected path** · availability if each plan unfolds exactly as assumed, "
                   "month by month from the plan start. Compare the end points; no randomness here.")
        st.plotly_chart(ui.scenario_lines_chart({n: f["det"] for n, f in fans.items()},
                                                labels=month_labels),
                        key="scenario_lines", config=CFG)

        ui.keep_state("pl_vol_plan")
        vol_options = list(cands)
        if st.session_state.get("pl_vol_plan") not in vol_options:
            st.session_state.pop("pl_vol_plan", None)
        vol_plan = st.selectbox("Plan to stress-test", vol_options, key="pl_vol_plan",
                                **({} if "pl_vol_plan" in st.session_state else {"index": 0}),
                                help="Show the simulated volatility for one plan only, so the bands stay readable.")
        st.plotly_chart(ui.scenario_fan_chart(fans[vol_plan], vol_plan, labels=month_labels),
                        key="scenario_fan", config=CFG)
        st.caption(f"**Volatility · {vol_plan}** · solid = median of 500 simulated paths; "
                   "light band = 10th–90th percentile; dark band = 25th–75th; dotted = the same "
                   "plan without shocks. Hover shows No volatility, Median and, for the hovered "
                   "month, each band's range: 75th = P25–P75, 90th = P10–P90. Shocks use "
                   f"{ui.money(fans[vol_plan]['sd'])}/month of historical net-cash volatility.")
    if not store["plans"]:
        st.caption("Save the plan from the sidebar to compare it with other versions. Try a cautious "
                   "and an optimistic one.")

# ---------------- sidebar: save / delete / export ----------------
with st.sidebar:
    st.header("Save")
    name = st.text_input("Name", key="pl_name")
    c1, c2 = st.columns(2)
    if c1.button("Save"):
        if name.strip() and plans.save_plan(name.strip(), params):
            st.session_state["_pl_pending"] = (name.strip(), name.strip())
            st.toast(f"Saved “{name.strip()}”. The Simulator will start from it.")
            st.rerun()
        else:
            st.error("Could not save: give the plan a name and check the folder is writable.")
    if c2.button("Delete", disabled=sel == "New plan"):
        plans.delete_plan(sel)
        st.session_state["_pl_pending"] = ("New plan", "")
        st.rerun()

    st.header("Data")
    st.download_button("Download budget (.csv)", b"" if hide else budget_df.to_csv(index=False).encode("utf-8"),
                       file_name="budget.csv", mime="text/csv", disabled=hide)

# ---------------- printable report ----------------
F = lambda x, **kw: ui.fmt(x, "money", **kw)
free = max(al["unalloc"], 0.0)
alloc_items = [(r["name"], r["annual"]) for r in al["rows"] if r["annual"] > 0] + ([("Free cash", free)] if free > 0.005 else [])
alloc_msg = " ".join(x for x in (
    "The plan has no surplus, so percentage buckets get nothing." if sur <= 0 else "",
    f"Over-allocated by {F(-al['unalloc'])}: the difference comes out of money you already have." if al["over"] else "") if x)
cmp_df = pd.DataFrame(cmp_rows) if store["plans"] else None
ui.glossary()

report = R.plan_report({
    "hide": hide, "scenario": sel if sel in names else "Unsaved plan",
    "plan_period": f"{plan_labels[0]} – {plan_labels[-1]}", "base_label": f"{ss['pl_period'].lower()} ({len(months)} months)",
    "assumptions": pd.DataFrame([
        {"Setting": "Baseline", "Value": f"{ss['pl_period']} · mean of monthly amounts · {ss['pl_level'].lower()} detail"
                                          + (" · current month ignored" if ss["pl_excl"] else "")},
        {"Setting": "Income change vs baseline", "Value": f"{inc_pct:+.1f}%"},
        {"Setting": "Expense change vs baseline", "Value": f"{exp_pct:+.1f}%"},
        {"Setting": "Plan period", "Value": f"{plan_labels[0]} – {plan_labels[-1]}"},
        {"Setting": "Month-to-month pattern", "Value": pattern},
        {"Setting": "Emergency fund target", "Value": f"{ss['pl_ef']:.1f} months of spending"}]),
    "start_tiles": [("Net worth", F(pos["net_worth"]), "today", sc.NETWORTH),
                    ("Liquid funds", F(pos["liquid"]), f"{ui.fmt(k_hist['liquidity_pct'], 'pct')} of availability", sc.TEAL),
                    ("Typical monthly income", F(k_hist["median_income"]), "median over the baseline", sc.INCOME),
                    ("Typical monthly spending", F(k_hist["median_burn"]), "median over the baseline", sc.EXPENSE),
                    ("Runway today", ui.fmt(k_hist["runway"], "months"), f"{pos['runway_basis'].lower()} ÷ median burn", sc.GOLD)],
    "budget_tiles": [("Planned income", F(tot["income"]), f"{F(tot['income'] - tot['baseline_income'], sign=True)} vs baseline", sc.INCOME, ""),
                     ("Planned expenses", F(tot["expense"]), f"{F(tot['expense'] - tot['baseline_expense'], sign=True)} vs baseline", sc.EXPENSE, ""),
                     ("Planned surplus", F(sur, sign=True), f"{F(sur / 12, sign=True)} per month", sc.NETWORTH, "pos" if sur >= 0 else "neg"),
                     ("Savings rate", ui.fmt(tot["rate"], "pct"), f"{pct_pts(tot['baseline_rate'], tot['rate'])} vs baseline", sc.GOLD, "")],
    "bridge": bud["bridge"], "cat_expense": bud["table"][bud["table"]["acct_type"] == "EXPENSE"], "budget_df": budget_df,
    "oneoffs": pd.DataFrame([{"Name": o["name"] or "—", "Type": o["type"], "When": o["when"], "Amount": o["amount"]} for o in oneoffs]) if oneoffs else None,
    "alloc_msg": alloc_msg, "alloc_items": alloc_items, "alloc_df": alloc_df,
    "runway_now": k0["runway"], "runway_end": k1["runway"], "runway_basis": pos["runway_basis"],
    "kpi_tiles": [("Savings rate", ui.fmt(k1["savings_rate"], "pct"), f"today {ui.fmt(k0['savings_rate'], 'pct')}", sc.GOLD),
                  ("Median monthly spending", F(k1["median_burn"]), f"today {F(k0['median_burn'])}", sc.EXPENSE),
                  ("Expense volatility", ui.fmt(k1["expense_vol"], "pct"), f"today {ui.fmt(k0['expense_vol'], 'pct')}", sc.PURPLE),
                  ("Net worth after the plan", F(al["net_worth_end"]), f"{F(al['net_worth_end'] - pos['net_worth'], sign=True)} in 12 months", sc.NETWORTH)],
    "ef_text": f"Emergency fund target: {F(ef['target'])} ({ef['months']:.1f} months of planned spending). "
               f"Still missing after the plan: {F(ef['gap_end'])}. {msg}",
    "months": mo, "cash_path": al["cash_path"], "month_df": month_df, "compare": cmp_df})
ui.print_report(report, "financial_plan_report.html", "Financial plan", hide)

# remember the widget values for when you come back to this page
st.session_state["_pl_mirror"] = {k: st.session_state[k] for k in PL_KEYS if k in st.session_state}
