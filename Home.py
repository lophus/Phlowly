import os

import pandas as pd
import streamlit as st

import db
import logic
import reports as R
import stats
import svgcharts as sc
import ui

st.set_page_config(page_title="Phlowly", page_icon=":material/account_balance:", layout="wide")
ui.inject_css()
ui.keep_state("hide", "rng")
hide = bool(st.session_state.get("hide", False))
CFG = {"displayModeBar": False}

deltas, _flows, _days = db.load_all()   # validates the database; stops with a message if needed
tx, acc = db.transactions(), db.accounts_info()
balances = logic.account_balances(deltas)       # same rows as the Dashboard balances list
if tx.empty:
    st.info("No transactions yet.")
    st.stop()
S = stats.overview(tx, balances)

ui.hero("Phlowly", "Your GnuCash book at a glance — live and read-only", chips=[
    f"{S['n_tx']:,} transactions",
    f"{S['first']:%d %b %Y} → {S['last']:%d %b %Y}",
    f"{S['n_accounts']} accounts · {S['n_hidden']} closed",
    f"File: {os.path.basename(db.DB_PATH)}"])

ui.currency_warning(db.book_currencies(deltas, tx))

# ---------------- navigation ----------------
NAV = [(":material/space_dashboard:", "Dashboard", "Balances, net worth and cash flow over time.", "pages/1_Dashboard.py"),
       (":material/speed:", "KPIs", "Runway, burn rate, volatility and savings.", "pages/2_KPIs.py"),
       (":material/receipt_long:", "Transactions", "Search and total any slice of the ledger.", "pages/3_Transactions.py"),
       (":material/point_of_sale:", "Receipt", "Your cash flow itemised like a receipt.", "pages/4_Receipt.py"),
       (":material/event_note:", "Plan", "A budget for the year ahead and where the surplus goes.", "pages/5_Plan.py"),
       (":material/query_stats:", "Simulator", "Wealth projections, goals and stress tests.", "pages/6_Simulator.py")]
for row in (NAV[:3], NAV[3:]):
    for col, (icon, title, desc, page) in zip(st.columns(3), row):
        with col:
            with ui.card(title):
                st.caption(desc)
                st.page_link(page, label=f"Open {title}", icon=icon)

# ---------------- headline numbers (no money here) ----------------
ui.section("Your book in numbers")
pm = S["per_month"]
n = max(S["n_tx"], 1)
extra = [f"{S[k]} {lbl}" for k, lbl in (("n_mixed_tx", "mixed"), ("n_equity_tx", "opening/equity")) if S[k]]
mixed = (" · " + " · ".join(extra)) if extra else ""
ui.md(ui.tiles_html([
    ui.tile("Transactions", f"{S['n_tx']:,}",
            f"{S['n_splits']:,} splits · {S['splits_per_tx']:.2f} per transaction",
            accent=ui.C_NW, spark=pm.values.tolist()),
    ui.tile("Expense transactions", f"{S['n_expense_tx']:,}",
            f"{S['n_expense_tx'] / n * 100:.2f}% of all transactions", accent=ui.C_EXPENSE),
    ui.tile("Income transactions", f"{S['n_income_tx']:,}",
            f"{S['n_income_tx'] / n * 100:.2f}% of all transactions", accent=ui.C_INCOME),
    ui.tile("Transfers", f"{S['n_transfer_tx']:,}",
            f"{S['n_transfer_tx'] / n * 100:.2f}% · between your own accounts{mixed}",
            accent=ui.C_TEAL),
]))
st.write("")
ui.md(ui.tiles_html([
    ui.tile("Accounts", f"{S['n_accounts']:,}",
            f"{S['n_active']} active · {S['n_hidden']} closed",
            accent=ui.C_PURPLE),
    ui.tile("Active days", f"{S['active_days']:,}",
            f"{S['active_pct'] * 100:.2f}% of {S['span_days']:,} days", accent=ui.C_NW),
    ui.tile("Average pace", f"{S['avg_per_month']:.2f}", "transactions per month",
            accent=ui.C_GOLD, spark=pm.values.tolist()),
    ui.tile("Longest streak", f"{S['longest_streak']:,} days",
            "consecutive days with activity", accent=ui.C_EXPENSE),
]))
st.write("")
ui.md(ui.tiles_html([
    ui.tile("Busiest day", f"{S['busiest_day']:%d %b %Y}",
            f"{S['busiest_day_n']} transactions", accent=ui.C_INCOME),
    ui.tile("Busiest weekday", S["busiest_weekday"],
            f"{int(S['weekday_counts'].max()):,} transactions in total", accent=ui.C_NW),
    ui.tile("Reconciled", f"{S['reconciled_pct'] * 100:.2f}%",
            f"{S['cleared_n']:,} more cleared", accent=ui.C_TEAL),
    ui.tile("Distinct descriptions", f"{S['distinct_desc']:,}",
            f"{S['n_tags']} tags · {S['tagged_pct'] * 100:.2f}% tagged", accent=ui.C_GOLD),
]))

# ---------------- activity ----------------
ui.section("Activity", "number of transactions")
with ui.card("Daily activity · last 12 months"):
    st.plotly_chart(ui.activity_heatmap(S["per_day"]), key="heat", config=CFG)

c1, c2 = st.columns([2, 1])
with c1:
    with ui.card("Transactions per month"):
        st.plotly_chart(ui.count_bars(list(pm.index.to_timestamp()), pm.values.tolist(),
                                      dates=True), key="per_month", config=CFG)
with c2:
    with ui.card("By weekday"):
        wd = S["weekday_counts"]
        st.plotly_chart(ui.count_bars(stats.WEEKDAYS, wd.values.tolist(), color=ui.C_PURPLE,
                                      highlight=True), key="weekday", config=CFG)

# ---------------- distribution ----------------
ui.section("Distribution", "wallets only · each transaction counted once")
TYPE_NAMES = {"BANK": "Bank", "CASH": "Cash", "ASSET": "Asset", "CREDIT": "Credit card",
              "LIABILITY": "Liability", "MUTUAL": "Mutual fund", "STOCK": "Stock",
              "RECEIVABLE": "Receivable", "PAYABLE": "Payable"}


def wallet_label(name, closed=False):
    return name + (" (closed)" if closed else "")


W = stats.tx_by_wallet(tx, acc)
names = logic.short_names(W["account"])      # plain names, no hierarchy
labels = [wallet_label(names[a], c) for a, c in zip(W["account"], W["closed"])]

left, right = st.columns([3, 2])
with left:
    with ui.card("Transactions by wallet · bricks"):
        st.plotly_chart(ui.wallet_bricks(labels, W["count"].tolist(), W["share"].tolist()),
                        key="bricks", config=CFG)
        st.caption(f"Every brick is a wallet and together they make all {S['n_tx']:,} transactions. "
                   "A transaction is counted under the wallet where the money actually moved "
                   "(the biggest wallet side; for a transfer, the account it left). "
                   "Income and expense categories are not wallets.")
    with ui.card("Wallet ranking"):
        ui.md(ui.rank_html(list(zip(labels, W["count"].astype(int).tolist())), ui.C_NW, S["n_tx"]))

with right:
    with ui.card("Transaction mix"):
        ui.md(ui.segments_html([
            ("Expenses", S["n_expense_tx"], ui.C_EXPENSE), ("Income", S["n_income_tx"], ui.C_INCOME),
            ("Transfers", S["n_transfer_tx"], ui.C_TEAL), ("Mixed", S["n_mixed_tx"], ui.C_GOLD),
            ("Opening / equity", S["n_equity_tx"], ui.C_PURPLE)]))
    with ui.card("Accounts by type"):
        ui.md(ui.segments_html([(TYPE_NAMES.get(t, t.title()), int(c), ui.PALETTE[i % len(ui.PALETTE)])
                                for i, (t, c) in enumerate(S["acc_by_type"].items())]))
        with st.expander(f"Show the {S['n_accounts']} accounts"):
            lst = balances.assign(Name=balances["account"].str.replace(" (Closed)", "", regex=False),
                               Type=balances["acct_type"].map(lambda t: TYPE_NAMES.get(t, t.title())),
                               Status=balances["closed"].map({1: "closed", 0: "active"}))
            st.dataframe(lst.sort_values(["Status", "Name"])[["Name", "Type", "Status"]],
                         hide_index=True)
    with ui.card("Most frequent descriptions"):
        ui.md(ui.rank_html([(k, int(v)) for k, v in S["top_desc"].items()], ui.C_NW, S["n_tx"]))
        st.caption(f"{S['distinct_desc']:,} distinct descriptions in total.")
    with ui.card("Tags"):
        if S["n_tags"]:
            ui.md(ui.rank_html([(f"#{k}", int(v)) for k, v in S["tag_counts"].head(8).items()],
                               ui.C_GOLD))
            st.caption(f"{S['n_tags']} tags · {S['tagged_pct'] * 100:.2f}% of transactions tagged.")
        else:
            st.caption("No tags yet. Add #tags to a transaction's description, notes or split memo in "
                       "GnuCash and they appear here and in the Receipt page.")

# ---------------- data quality ----------------
with ui.card("Data quality"):
    st.caption("Read-only signals to review in GnuCash. Nothing here changes your book.")

    _sums = tx.groupby("tx_guid")["value"].sum()
    _bad_ids = _sums.index[_sums.abs() > 0.005]
    _unbal = tx[tx["tx_guid"].isin(_bad_ids)]
    _known = set(logic.BS_TYPES + ["INCOME", "EXPENSE", "EQUITY"])
    _uncat = tx[~tx["acct_type"].isin(_known)]
    _q99 = tx["value"].abs().quantile(0.99) if len(tx) > 1 else None
    _large_splits = tx[tx["value"].abs() > _q99] if _q99 is not None else tx.iloc[0:0]
    # One row per transaction: prefer the income/expense/equity side, otherwise the main
    # account side of a transfer. Income and expenses are shown as positive amounts.
    _large_rows = []
    for _guid, _g in _large_splits.groupby("tx_guid", sort=False):
        _side = _g[_g["acct_type"].isin(["INCOME", "EXPENSE", "EQUITY"])]
        if _side.empty:
            _side = _g[_g["is_primary"]] if "is_primary" in _g else _g.iloc[0:0]
        if _side.empty:
            _side = _g.loc[[_g["value"].abs().idxmax()]]
        _side = _side.sort_values("value", key=lambda s: s.abs(), ascending=False)
        _r = _side.iloc[0]
        if _r["acct_type"] in ("INCOME", "EXPENSE", "EQUITY"):
            _detail, _amt = _r["account"], abs(_r["value"])
        else:
            # Transfer: show where the money left from and where it arrived.
            _all = tx[tx["tx_guid"] == _guid]
            _wallet = _all[_all["is_wallet"]]
            _names = logic.short_names(list(_wallet["account"]))
            _src = " + ".join(_names[a] for a in _wallet.loc[_wallet["value"] < 0, "account"]) or "?"
            _dst = " + ".join(_names[a] for a in _wallet.loc[_wallet["value"] > 0, "account"]) or "?"
            _detail, _amt = f"{_src} → {_dst}", abs(_r["value"])
        _large_rows.append({"Date": _r["day"].date(), "Description": _r["description"],
                            "Account / transfer": _detail, "Type": _r["acct_type"], "Amount": _amt,
                            "Transaction GUID": _guid})

    def _amt(x):
        return ui.MASK if hide else ui.fmt(x, "money")

    t_unbal, t_uncat, t_large = st.tabs([
        f"Unbalanced · {len(_bad_ids):,}",
        f"Uncategorised · {len(_uncat):,}",
        f"Large amounts · {len(_large_rows):,}",
    ])

    with t_unbal:
        st.caption("Transactions whose splits do not add up to zero.")
        if _unbal.empty:
            st.success("Nothing to review here.")
        else:
            rows = [{"Date": g["day"].iloc[0].date(),
                     "Description": g["description"].iloc[0],
                     "Splits": len(g),
                     "Balance": g["value"].sum(),
                     "Transaction GUID": guid}
                    for guid, g in _unbal.groupby("tx_guid", sort=False)]
            d = pd.DataFrame(rows)
            d = d.sort_values("Balance", key=lambda s: s.abs(), ascending=False)
            d["Balance"] = d["Balance"].map(_amt)
            st.dataframe(d, hide_index=True, height=320)
            st.download_button("Download CSV", b"" if hide else d.to_csv(index=False).encode("utf-8"),
                               file_name="unbalanced_transactions.csv", mime="text/csv", disabled=hide)

    with t_uncat:
        st.caption("Splits whose account type is not one of the known income, expense or account types.")
        if _uncat.empty:
            st.success("Nothing to review here.")
        else:
            d = pd.DataFrame({"Date": _uncat["day"].dt.date,
                              "Description": _uncat["description"],
                              "Account": _uncat["account"],
                              "Type": _uncat["acct_type"],
                              "Amount": _uncat["value"].map(_amt),
                              "Transaction GUID": _uncat["tx_guid"],
                              "Split GUID": _uncat["split_guid"]})
            st.dataframe(d, hide_index=True, height=320)
            st.download_button("Download CSV", b"" if hide else d.to_csv(index=False).encode("utf-8"),
                               file_name="uncategorised_splits.csv", mime="text/csv", disabled=hide)

    with t_large:
        if not _large_rows:
            st.success("Nothing to review here.")
        else:
            st.caption(f"Splits above the 99th percentile: more than "
                       f"{ui.MASK if hide else ui.fmt(_q99, 'money')} in absolute value. "
                       "One row per transaction: income, expense and equity show their category; "
                       "transfers show source → destination. All amounts are positive.")
            d = pd.DataFrame(_large_rows)
            d = d.sort_values("Amount", key=lambda s: s.abs(), ascending=False)
            d["Amount"] = d["Amount"].map(_amt)
            st.dataframe(d, hide_index=True, height=320)
            st.download_button("Download CSV", b"" if hide else d.to_csv(index=False).encode("utf-8"),
                               file_name="large_splits.csv", mime="text/csv", disabled=hide)

# ---------------- help ----------------
ui.glossary()

# ---------------- printable report ----------------
n_ = max(S["n_tx"], 1)
wd_series = S["weekday_counts"].copy()
wd_series.index = stats.WEEKDAYS
report = R.home_report({
    "meta": f"{S['n_tx']:,} transactions · {S['first']:%d %b %Y} – {S['last']:%d %b %Y} · "
            f"{S['n_accounts']} accounts, {S['n_hidden']} closed",
    "tiles": [
        ("Transactions", f"{S['n_tx']:,}", f"{S['n_splits']:,} splits · {S['splits_per_tx']:.2f} per transaction", sc.NETWORTH, S["per_month"].tolist()),
        ("Expense transactions", f"{S['n_expense_tx']:,}", f"{S['n_expense_tx'] / n_ * 100:.2f}% of all", sc.EXPENSE),
        ("Income transactions", f"{S['n_income_tx']:,}", f"{S['n_income_tx'] / n_ * 100:.2f}% of all", sc.INCOME),
        ("Transfers", f"{S['n_transfer_tx']:,}", f"{S['n_transfer_tx'] / n_ * 100:.2f}% between your own accounts", sc.TEAL),
        ("Accounts", f"{S['n_accounts']:,}", f"{S['n_active']} active · {S['n_hidden']} closed", sc.PURPLE),
        ("Active days", f"{S['active_days']:,}", f"{S['active_pct'] * 100:.2f}% of {S['span_days']:,} days", sc.NETWORTH),
        ("Average pace", f"{S['avg_per_month']:.2f}", "transactions per month", sc.GOLD, S["per_month"].tolist()),
        ("Longest streak", f"{S['longest_streak']:,} days", "consecutive days with activity", sc.EXPENSE),
        ("Busiest day", f"{S['busiest_day']:%d %b %Y}", f"{S['busiest_day_n']} transactions", sc.INCOME),
        ("Busiest weekday", S["busiest_weekday"], f"{int(S['weekday_counts'].max()):,} transactions in total", sc.NETWORTH),
        ("Reconciled", f"{S['reconciled_pct'] * 100:.2f}%", f"{S['cleared_n']:,} more cleared", sc.TEAL),
        ("Distinct descriptions", f"{S['distinct_desc']:,}", f"{S['n_tags']} tags · {S['tagged_pct'] * 100:.2f}% tagged", sc.GOLD)],
    "per_day": S["per_day"], "per_month": S["per_month"], "weekday": wd_series,
    "wallets": list(zip(labels, W["count"].astype(int).tolist()))[:12],
    "mix": [x for x in [("Expenses", S["n_expense_tx"], sc.EXPENSE), ("Income", S["n_income_tx"], sc.INCOME),
                        ("Transfers", S["n_transfer_tx"], sc.TEAL), ("Mixed", S["n_mixed_tx"], sc.GOLD),
                        ("Opening / equity", S["n_equity_tx"], sc.PURPLE)] if x[1] > 0],
    "top_desc": [(k_, int(v_)) for k_, v_ in S["top_desc"].items()],
    "tags": [(k_, int(v_)) for k_, v_ in S["tag_counts"].head(8).items()]})
ui.print_report(report, "home_report.html", "Home")
