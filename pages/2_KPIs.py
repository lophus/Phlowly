import math

import pandas as pd
import streamlit as st

import db
import kpis
import logic
import reports as R
import settings
import ui

st.set_page_config(page_title="KPIs", page_icon=":material/speed:", layout="wide")
ui.inject_css()
CFG = {"displayModeBar": False}

deltas, flows, all_days = db.load_all()
ui.currency_warning(db.book_currencies(deltas))
balances = logic.account_balances(deltas)
saved = settings.load()

with st.sidebar:
    st.header("Filters")
    hide, start, end = ui.sidebar_common(all_days)

    st.header("KPI settings")
    asset_opts = sorted(balances.loc[balances["acct_type"] == "ASSET", "account"].unique())
    liquid_assets = st.multiselect(
        "Asset accounts counted as liquid", asset_opts,
        default=[a for a in saved["liquid_assets"] if a in asset_opts],
        help="Bank, cash and card accounts are always liquid. "
             "Asset-type accounts count only if selected here.")
    bases = ["Availability", "Liquid funds"]
    runway_basis = st.radio("Runway based on", bases, horizontal=True,
                            index=bases.index(saved["runway_basis"])
                            if saved["runway_basis"] in bases else 0)
    excl_current = st.checkbox("Exclude current month from statistics",
                               value=saved["exclude_current_month"],
                               help="The month in progress is incomplete and skews "
                                    "median and standard deviation.")
    if st.button("Reload data"):
        st.cache_data.clear()
        st.rerun()
settings.update(liquid_assets=liquid_assets, runway_basis=runway_basis,
                exclude_current_month=excl_current)

# ---------------- computation ----------------
pos = logic.position(deltas, liquid_assets, runway_basis)
availability, liquid = pos["availability"], pos["liquid"]
monthly = logic.monthly_series(flows, start, end, excl_current)
base = availability if runway_basis == "Availability" else liquid
k = kpis.compute(monthly, availability, liquid, base)


def m(x, **kw):
    return ui.MASK if hide else ui.fmt(x, "money", **kw)


def sign_cls(x):
    return "" if (hide or (isinstance(x, float) and math.isnan(x))) else ("pos" if x >= 0 else "neg")


ui.hero("Key indicators", "Runway, burn rate and volatility, computed from your GnuCash history",
        chips=[ui.range_chip(start, end, all_days), f"{k['months']} month(s) of data",
               f"Runway basis: {runway_basis}"])
ui.active_filters([ui.range_chip(start, end, all_days), f"Runway basis: {runway_basis}",
                   "Current month excluded" if excl_current else "Current month included",
                   "Privacy on" if hide else "Amounts visible"])

# ================= Row 1: availability + gauges =================
c0, c1, c2 = st.columns([5, 4, 4])
ui.md(ui.hero_availability_html(availability, liquid, hide), c0)

for col, title, key, val, formula in [
        (c1, "Runway (months)", "g1", k["runway"], f"{runway_basis} ÷ median burn rate"),
        (c2, "Worst-case runway (months)", "g2", k["worst_runway"],
         f"{runway_basis} ÷ (median burn + std. deviation)")]:
    with col:
        with ui.card(title):
            if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                ui.md(ui.tiles_html([ui.tile(title, ui.fmt(val, "months"), formula,
                                             accent=ui.C_TEAL)], cols=1, flat=True))
            else:
                ui.md(ui.gauge_svg(val, uid=key))
            ui.md(ui.status_pill_html(ui.runway_status(val)))
            st.caption(formula)

# ================= Row 2: headline tiles =================
st.write("")
inc, exp = monthly["income"], monthly["expense"]
net_s = inc - exp
rate_s = net_s / inc.where(inc > 0)
wn = k["worst_net_runway"]
ui.md(ui.tiles_html([
    ui.tile("Savings rate", ui.fmt(k["savings_rate"], "pct"),
            "(income − expenses) ÷ income", sign_cls(k["savings_rate"]), ui.C_GOLD,
            spark=rate_s.tolist()),
    ui.tile("Net runway",
            ui.MASK if hide else ui.fmt(k["net_monthly"], "money", sign=True) + " / month",
            f"{ui.fmt(k['net_rate'], 'pct', sign=True)} of median income",
            sign_cls(k["net_monthly"]), ui.C_INCOME, spark=net_s.tolist()),
    ui.tile("Worst-case net runway", ui.fmt(wn, "months"),
            "self-sustaining even in the worst case" if wn == math.inf
            else "worst-case burn vs. downside income", "", ui.C_EXPENSE),
    ui.tile("Liquidity", ui.fmt(k["liquidity_pct"], "pct"),
            (ui.MASK if hide else ui.fmt(k["liquid"], "money")) + " readily available",
            "", ui.C_TEAL,
            extra=ui.meter_html(k["liquidity_pct"], ui.C_TEAL, "of availability",
                                ui.fmt(k["liquidity_pct"], "pct"))),
], cols=4))

# ================= Row 3: expenses & income =================
ui.section("Monthly behaviour", "median, spread and volatility")
e_col, i_col = st.columns(2)
for col, title, series, med, sd, vol, color, key, label in [
        (e_col, "Expenses · monthly", exp, k["median_burn"], k["expense_std"], k["expense_vol"],
         ui.C_EXPENSE, "exp_band", "Median burn rate"),
        (i_col, "Income · monthly", inc, k["median_income"], k["income_std"], k["income_vol"],
         ui.C_INCOME, "inc_band", "Median income")]:
    with col:
        with ui.card(title):
            lvl, lcol = ui.vol_level(vol)
            ui.md(ui.tiles_html([
                ui.tile(label, m(med),
                        "median of monthly totals", accent=color),
                ui.tile("Std. deviation", m(sd), "monthly spread", accent=color),
                ui.tile("Volatility", ui.fmt(vol, "pct"), "std. dev. ÷ median", accent=lcol,
                        extra=ui.meter_html(vol, lcol, lvl, ui.fmt(vol, "pct"))),
            ], cols=3, flat=True))
            if hide:
                ui.private_note()
            elif monthly.empty:
                st.caption("No months in the selected range.")
            else:
                st.plotly_chart(ui.monthly_band_chart(series, med, sd, color), key=key, config=CFG)

st.caption(f"Statistics use {k['months']} month(s) in the selected date range"
           + (" (current month excluded)." if excl_current else "."))

rows = [("Availability", availability), ("Liquid funds", liquid),
        ("Runway months", k["runway"]), ("Worst runway months", k["worst_runway"]),
        ("Median burn", k["median_burn"]), ("Burn std dev", k["expense_std"]),
        ("Expense volatility", k["expense_vol"]), ("Median income", k["median_income"]),
        ("Income std dev", k["income_std"]), ("Income volatility", k["income_vol"]),
        ("Savings rate", k["savings_rate"]), ("Net monthly", k["net_monthly"]),
        ("Liquidity pct", k["liquidity_pct"]), ("Months of data", k["months"])]
out = pd.DataFrame([{"KPI": name, "Value": val} for name, val in rows])
st.download_button("Download CSV", b"" if hide else out.to_csv(index=False).encode("utf-8"),
                   file_name="kpi_summary.csv", mime="text/csv", disabled=hide,
                   help="Disabled while privacy mode is on." if hide else None)

ui.glossary()

report = R.kpis_report(hide=hide, period=ui.range_chip(start, end, all_days), basis=runway_basis, k=k,
                       availability=availability, liquid=liquid, monthly=monthly, excl_current=excl_current)
ui.print_report(report, "kpis_report.html", "Key indicators", hide)
