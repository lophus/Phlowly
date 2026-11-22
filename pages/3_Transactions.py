import pandas as pd
import streamlit as st

import db
import logic
import reports as R
import ui

st.set_page_config(page_title="Transactions", page_icon=":material/receipt_long:", layout="wide")
ui.inject_css()

db.load_all()
tx = db.transactions()
ui.currency_warning(db.book_currencies(tx))

with st.sidebar:
    st.header("Filters")
    hide, start, end = ui.sidebar_common(tx["day"])
    if st.button("Reload data"):
        st.cache_data.clear()
        st.rerun()

ui.hero("Transactions", "Search, filter and total any slice of your ledger",
        chips=[ui.range_chip(start, end, tx["day"]),
               f"{tx['tx_guid'].nunique():,} transactions in the book"])


def m(x, **kw):
    return ui.MASK if hide else ui.fmt(x, "money", **kw)


# ---------------- filters ----------------
all_accounts = sorted(tx["account"].unique())
all_types = sorted(tx["acct_type"].unique())
tag_counts = tx.drop_duplicates("tx_guid")["tx_tag_list"].explode().dropna().value_counts()

VIEWS = {
    "Transactions": "One row per transaction. Amount = effect on your money: expenses are negative, "
                    "income positive, transfers between your own accounts 0. "
                    "Moved = how much the transaction shifted around.",
    "Wallets": "Movements on your cash, bank, asset and card accounts, as in a GnuCash register: "
               "money in is positive, money out is negative.",
    "Categories": "Income and expense accounts only: income is positive, expenses are negative.",
}

with ui.card("Filters"):
    r1 = st.columns([3, 3, 2, 2])
    search = r1[0].text_input("Search", placeholder="description, notes, memo or number",
                              help="Several values: separate them with commas.")
    guid = r1[1].text_input("GUID", placeholder="transaction or split GUID (contains)",
                            help="Several GUIDs: separate them with commas.")
    amin = r1[2].number_input("Min amount", min_value=0.0, value=0.0, step=10.0)
    amax = r1[3].number_input("Max amount (0 = no limit)", min_value=0.0, value=0.0, step=10.0)
    r2 = st.columns([4, 2, 2, 2])
    acc_names = logic.short_names(all_accounts)
    accounts = r2[0].multiselect("Accounts", all_accounts, format_func=acc_names.get)
    types_sel = r2[1].multiselect("Account types", all_types)
    tag = r2[2].multiselect("Tags", [f"#{t}" for t in tag_counts.index],
                            help="Pick several tags to match any of them.")
    direction = r2[3].radio("Direction", ["All", "In (+)", "Out (−)"], horizontal=True)
    r3 = st.columns([3, 2, 3])
    view = r3[0].radio("View", list(VIEWS), horizontal=True)
    sort = r3[1].selectbox("Sort by", ["Date (newest)", "Date (oldest)",
                                       "Amount (highest)", "Amount (lowest)"])
    r3[2].caption(VIEWS[view])

f = logic.filter_splits(tx, start, end, search, guid, accounts, types_sel, tag)
v = logic.build_view(tx, f, view, tag_active=bool(tag))

# amount range and direction act on what the view shows
mag = v["Moved"] if view == "Transactions" else v["Amount"].abs()
mask = pd.Series(True, index=v.index)
if amin > 0:
    mask &= mag >= amin
if amax > 0:
    mask &= mag <= amax
if direction == "In (+)":
    mask &= v["Amount"] > 0
elif direction == "Out (−)":
    mask &= v["Amount"] < 0
v = v[mask]

ui.active_filters([ui.range_chip(start, end, tx["day"]), view,
                   f"Search: {', '.join(logic._multi(search))}" if search.strip() else "No search",
                   f"GUID: {', '.join(logic._multi(guid))}" if guid.strip() else "No GUID filter",
                   f"Tags: {', '.join(tag)}" if tag else "All tags",
                   "Privacy on" if hide else "Amounts visible"])

# ---------------- table ----------------
if view == "Transactions":
    d = pd.DataFrame({
        "Date": v["day"].dt.date, "Description": v["description"], "Kind": v["kind"],
        "Wallets": v["wallets"], "Categories": v["categories"],
        "Amount": v["Amount"], "Moved": v["Moved"], "Notes": v["notes"], "Tags": v["tags"],
        "Transaction GUID": v["tx_guid"]})
else:
    d = pd.DataFrame({
        "Date": v["day"].dt.date, "Description": v["description"],
        "Account": v["account"], "Type": v["acct_type"],
        "Amount": v["Amount"], "Notes": v["notes"], "Tags": v["tags"],
        "Transaction GUID": v["tx_guid"], "Split GUID": v["split_guid"]})

if sort.startswith("Date"):
    d = d.sort_values("Date", ascending=sort.endswith("(oldest)"), kind="stable")
else:
    d = d.sort_values("Amount", ascending=sort.endswith("(lowest)"), kind="stable")

ui.section("Results", f"{len(d):,} {'transactions' if view == 'Transactions' else 'rows'}")
if d.empty:
    st.info("Nothing matches these filters. Try another view or loosen the filters.")
else:
    if hide:
        masked = d.assign(Amount=ui.MASK)
        if "Moved" in masked:
            masked["Moved"] = ui.MASK
        st.dataframe(masked, hide_index=True, height=520)
    else:
        fmt_cols = {c: "{:,.2f}" for c in ("Amount", "Moved") if c in d}
        sty = d.style.format(fmt_cols)
        mapper = getattr(sty, "map", None) or sty.applymap
        sty = mapper(lambda x: f"color: {'#EF8C8C' if x < 0 else '#88BF4D' if x > 0 else '#8FA0AF'};"
                               f" font-weight: 600", subset=["Amount"])
        st.dataframe(sty, hide_index=True, height=520)

# ---------------- totals (always at the end) ----------------
amt = d["Amount"]
total = float(amt.sum()) if len(d) else 0.0
minis = [("Rows", f"{len(d):,}"),
         ("Money in (+)", m(float(amt[amt > 0].sum()))),
         ("Money out (−)", m(float(amt[amt < 0].sum()))),
         ("Average", m(float(amt.mean())) if len(d) else "n/a"),
         ("Largest", m(float(amt.abs().max())) if len(d) else "n/a")]
if view == "Transactions":
    k = d["Kind"].value_counts() if len(d) else {}
    minis.append(("Mix", f"{k.get('Expense', 0):,} expenses · {k.get('Income', 0):,} income · "
                         f"{k.get('Transfer', 0):,} transfers"
                         + (f" · {len(d) - sum(k.get(x, 0) for x in ('Expense', 'Income', 'Transfer')):,} other"
                            if len(d) - sum(k.get(x, 0) for x in ('Expense', 'Income', 'Transfer')) else "")))
totals = ui.totals_bar_html("Total amount · filtered", m(total, sign=True), minis)
ui.md(totals)
st.caption("Totals add up one side of each transaction only (never both), so nothing is "
           "counted twice or cancels out. Currencies are summed as if they were one.")
st.download_button("Download CSV", b"" if hide else d.to_csv(index=False).encode("utf-8"),
                   file_name="transactions.csv", mime="text/csv", disabled=hide,
                   help="Disabled while privacy mode is on." if hide else None)

# ---------------- help ----------------
ui.glossary()

# ---------------- printable report ----------------
flt = []
if search.strip():
    flt.append(("Search", ", ".join(logic._multi(search))))
if guid.strip():
    flt.append(("GUID contains", ", ".join(logic._multi(guid))))
if amin > 0:
    flt.append(("Minimum amount", f"{amin:,.2f}"))
if amax > 0:
    flt.append(("Maximum amount", f"{amax:,.2f}"))
if accounts:
    flt.append(("Accounts", ", ".join(acc_names[a] for a in accounts)))
if types_sel:
    flt.append(("Account types", ", ".join(types_sel)))
if tag:
    flt.append(("Tags", ", ".join(tag)))
if direction != "All":
    flt.append(("Direction", direction))
cols_pr = (["Date", "Description", "Kind", "Wallets", "Categories", "Amount", "Moved", "Tags"]
           if view == "Transactions" else ["Date", "Description", "Account", "Type", "Amount", "Tags"])
report = R.transactions_report(hide=hide, period=ui.range_chip(start, end, tx["day"]), view=view, filters=flt,
                               df=d[cols_pr], num_cols=("Amount", "Moved"), total_big=ui.fmt(total, "money", sign=True),
                               minis=minis, max_rows=1200)
ui.print_report(report, "transactions_report.html", "Transactions", hide)
