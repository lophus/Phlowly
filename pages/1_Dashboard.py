import streamlit as st

import db
import logic
import reports as R
import settings
import ui

st.set_page_config(page_title="Dashboard", page_icon=":material/space_dashboard:", layout="wide")
ui.inject_css()
CFG = {"displayModeBar": False}

deltas, flows, all_days = db.load_all()
ui.currency_warning(db.book_currencies(deltas))
balances = logic.account_balances(deltas)
currency_totals = logic.currency_totals(balances)
saved = settings.load()

with st.sidebar:
    st.header("Filters")
    hide, start, end = ui.sidebar_common(all_days)
    step = st.selectbox("Time step", ["Month", "Day", "Week", "Year"])
    detail = st.selectbox("Detail level", ["Macro", "Detailed"])
    reserve = st.number_input("Reserve line (0 = hidden)", min_value=0.0,
                              value=float(saved["reserve"]), step=500.0)
    if st.button("Reload data"):
        st.cache_data.clear()
        st.rerun()
settings.update(reserve=reserve)

ui.hero("Dashboard", "Balances, net worth and cash flow",
        chips=[ui.range_chip(start, end, all_days), f"Time step: {step}", f"Detail: {detail}"])
ui.active_filters([ui.range_chip(start, end, all_days), f"Step: {step}", f"Detail: {detail}",
                   "Privacy on" if hide else "Amounts visible",
                   f"Data updated {ui.data_stamp(db.DB_PATH)}"])


def m(x, **kw):
    return ui.MASK if hide else ui.fmt(x, "money", **kw)


# ---------------- data ----------------
s_time = logic.account_balance_series(deltas, step, start, end)
pn = logic.net_worth_series(deltas, step, start, end)
by_category = {"EXPENSE": logic.category_totals(flows, "EXPENSE", detail, start, end), "INCOME": logic.category_totals(flows, "INCOME", detail, start, end)}
f_time = logic.flows_by_period(flows, step, detail, start, end)
net_df = logic.net_by_period(flows, step, start, end)

# ---------------- headline numbers ----------------
monthly = logic.monthly_series(flows, start, end)
nw_all = logic.net_worth_series(deltas, "Month")
nw = logic.net_worth_now(deltas)
inc_t, exp_t = float(monthly["income"].sum()), float(monthly["expense"].sum())
saved_t = inc_t - exp_t
rate = f"{saved_t / inc_t * 100:.2f}%" if inc_t else "n/a"
ui.md(ui.tiles_html([
    ui.tile("Net worth", m(nw), "current total", accent=ui.C_NW,
            spark=nw_all["Balance"].tail(24).tolist()),
    ui.tile("Income", m(inc_t), "selected period", accent=ui.C_INCOME,
            spark=monthly["income"].tolist()),
    ui.tile("Expenses", m(exp_t), "selected period", accent=ui.C_EXPENSE,
            spark=monthly["expense"].tolist()),
    ui.tile("Savings", m(saved_t, sign=True), "savings rate " + (ui.MASK if hide else rate),
            cls="" if hide else ("pos" if saved_t >= 0 else "neg"), accent=ui.C_GOLD,
            spark=(monthly["income"] - monthly["expense"]).tolist()),
]))

# ================= Accounts overview =================
ui.section("Accounts overview")
col_l, col_r = st.columns([2, 3])
with col_l:
    with ui.card("Balances"):
        ui.md(ui.account_list_html(balances, currency_totals, hide))
with col_r:
    with ui.card("Assets distribution"):
        ui.donut_block(balances[balances["balance"] > 0], "account", "balance", key="assets",
                       hide=hide, height=ui.H_ACC)

with ui.card("Account balance over time"):
    if hide:
        ui.private_note()
    else:
        st.plotly_chart(ui.balances_over_time(s_time, step), key="acc_time", config=CFG)

# ================= Net worth & cash flow =================
ui.section("Net worth & cash flow")
with ui.card("Net worth"):
    if hide:
        ui.private_note()
    else:
        st.plotly_chart(ui.net_worth(pn, step, reserve), key="nw", config=CFG)

c1, c2 = st.columns(2)
for col, acct_type, title, key in [(c1, "EXPENSE", "Expenses by category", "exp"),
                              (c2, "INCOME", "Income by category", "inc")]:
    with col:
        with ui.card(title):
            ui.donut_block(by_category[acct_type], "Category", "Amount",
                           key=key, hide=hide)

with ui.card("Income vs expenses over time"):
    if hide:
        ui.private_note()
    else:
        st.plotly_chart(ui.income_vs_expense(f_time, step, net_df), key="ie", config=CFG)

ui.glossary()

report = R.dashboard(hide=hide, period=ui.range_chip(start, end, all_days), step=step, detail=detail, nw=nw,
                     nw_series=nw_all["Balance"].tail(24).tolist(), monthly=monthly, balances=balances, currency_totals=currency_totals,
                     s_time=s_time, pn=pn, expense=by_category["EXPENSE"], income=by_category["INCOME"], flows_t=f_time,
                     net=net_df, reserve=reserve)
ui.print_report(report, "dashboard_report.html", "Dashboard", hide)
