import pandas as pd
import streamlit as st

import db
import receipt
import reports as R
import ui

st.set_page_config(page_title="Receipt", page_icon=":material/point_of_sale:", layout="wide")
ui.inject_css()
ui.keep_state("receipt_exclude_guids")

db.load_all()
tx = db.transactions()
base_all = db.receipt_base()

with st.sidebar:
    st.header("Filters")
    hide, start, end = ui.sidebar_common(tx["day"])
    st.header("Receipt")
    detail = st.radio("Detail level", ["Macro", "Detailed"], horizontal=True,
                      help="Macro: one line per category. Detailed: sub-categories listed "
                           "under each category.")
    opts = receipt.exclusion_options(base_all, detail)
    labels = receipt.option_labels(opts)
    excluded = st.multiselect("Exclude categories", opts, key=f"excl_{detail}",
                              format_func=labels.get,
                              help="Remove categories (or, in Detailed mode, single "
                                   "sub-categories) from the receipt.")
    guid_text = st.text_area("Exclude transactions by GUID",
                             key="receipt_exclude_guids", height=96,
                             placeholder="One GUID per line, or separated by commas/spaces",
                             help="Exact GnuCash transaction GUIDs (case-insensitive). Those "
                                  "transactions are left out of the receipt totals, QR summary and "
                                  "printable report.")
    excluded_guids = receipt.parse_guids(guid_text)
    period_all = receipt.select(base_all, start, end)
    period_base = receipt.exclude_guids(period_all, excluded_guids)
    matched_guids = set(period_all["tx_guid"].astype(str).str.lower()) & excluded_guids
    if excluded_guids:
        known = set(base_all["tx_guid"].astype(str).str.lower())
        unknown = sorted(excluded_guids - known)
        if not matched_guids:
            msg = "No matching income/expense transaction in the selected period."
            if unknown:
                msg = (f"{len(unknown)} GUID(s) not found among income/expense transactions; "
                       "no matching transaction in the selected period.")
            st.caption(msg)
        elif unknown:
            st.caption(f"{len(unknown)} GUID(s) not found among income/expense transactions.")
    if st.button("Reload data"):
        st.cache_data.clear()
        st.rerun()

chips = [ui.range_chip(start, end, tx["day"]), f"Detail: {detail}",
         f"{len(excluded)} categories excluded" if excluded else "All categories"]
if matched_guids:
    chips.append(f"{len(matched_guids)} transaction(s) excluded")
ui.hero("Cash flow receipt", "Every expense, then every income, itemised", chips=chips)
ui.active_filters([ui.range_chip(start, end, tx["day"]), f"Detail: {detail}",
                   f"{len(excluded)} categories excluded" if excluded else "All categories",
                   f"{len(matched_guids)} transaction(s) excluded by GUID" if matched_guids else "No GUID exclusions",
                   "Privacy on" if hide else "Amounts visible"])

if excluded_guids:
    hit = period_all[period_all["tx_guid"].astype(str).str.lower().isin(excluded_guids)]
    if not hit.empty:
        desc = tx.drop_duplicates("tx_guid").set_index("tx_guid")["description"].to_dict()
        det = hit.groupby("tx_guid", as_index=False).agg(
            day=("day", "min"), acct_type=("acct_type", "first"), amount=("Amount", "sum"))
        det["Description"] = det["tx_guid"].map(lambda g: desc.get(g, ""))
        det = det[["day", "Description", "acct_type", "amount", "tx_guid"]]
        det.columns = ["Date", "Description", "Type", "Amount", "Transaction GUID"]
        det["Date"] = pd.to_datetime(det["Date"]).dt.date
        det["Amount"] = ui.MASK if hide else det["Amount"].map(lambda x: ui.fmt(x, "money"))
        with st.expander(f"Excluded transactions ({len(det)})"):
            st.dataframe(det, hide_index=True)
            if st.button("Clear GUID exclusions"):
                st.session_state["receipt_exclude_guids"] = ""
                st.rerun()

period = ui.range_chip(start, end, tx["day"]).replace(" → ", " – ")

res = receipt.build(period_base, detail, frozenset(excluded))
qr = ui.qr_svg(receipt.qr_text("Cash flow", period, res))     # summary readable by any phone

_, mid, _ = st.columns([1, 2, 1])
with mid:
    # the QR would reveal the amounts, so it is not drawn in privacy mode
    ui.md(ui.receipt_html("Cash flow", period, res, hide, None if hide else qr))
    st.download_button("Download .txt", "" if hide else receipt.text("Cash flow", period, res),
                       file_name="cashflow_receipt.txt", disabled=hide)
    st.caption("Scan the QR code with your phone camera to read a summary of this receipt; "
               "it can be copied or shared straight from the scanner.")

ui.glossary()

report = R.receipt_report(hide=hide, period=period, receipt_html=ui.receipt_html("Cash flow", period, res, False, qr))
ui.print_report(report, "cashflow_receipt.html", "Cash flow receipt", hide)
