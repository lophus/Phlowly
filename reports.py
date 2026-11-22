"""Printable A4 reports: one per page, light theme, static SVG charts, controlled page breaks.

The same HTML is (a) embedded hidden in the Streamlit page and shown alone when you print, and
(b) offered as a self-contained download that opens and prints anywhere.
"""
import datetime as dt

import pandas as pd

import kpis
import svgcharts as sc
from svgcharts import esc

CSS = """
@page {size: A4; margin: 13mm 13mm 14mm;}
.rp {font-family: Inter, 'Helvetica Neue', Arial, sans-serif; color: #1D232B; font-size: 11px; line-height: 1.4;
     -webkit-print-color-adjust: exact; print-color-adjust: exact;}
.rp, .rp * {box-sizing: border-box;}
.rp svg text {font-family: Inter, 'Helvetica Neue', Arial, sans-serif;}
.rp-head {border-bottom: 2px solid #1D232B; padding-bottom: 8px; margin-bottom: 14px;}
.rp-title {font-size: 22px; font-weight: 700; letter-spacing: -0.01em;}
.rp-sub {color: #5B6571; font-size: 11.5px; margin-top: 2px;}
.rp-meta {color: #5B6571; font-size: 9.5px; margin-top: 7px;}
.rp-sec {font-size: 9.5px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: #5B6571;
         border-bottom: 1px solid #CFD5DC; padding-bottom: 3px; margin: 18px 0 9px;
         page-break-after: avoid; break-after: avoid;}
.rp-tw {margin: 0 -6px;}
.rp-tiles {width: 100%; table-layout: fixed; border-collapse: separate; border-spacing: 6px;}
.rp-tiles td {border: 1px solid #CFD5DC; border-radius: 5px; padding: 8px 10px 7px; vertical-align: top;
              page-break-inside: avoid; break-inside: avoid;}
.rp-tiles td.e {border: none;}
.rp-tiles .l {font-size: 8.5px; font-weight: 700; letter-spacing: .09em; text-transform: uppercase; color: #5B6571;}
.rp-tiles .v {font-size: 17px; font-weight: 700; letter-spacing: -.01em; margin-top: 3px; white-space: nowrap;}
.rp-tiles .s {font-size: 9px; color: #5B6571; margin-top: 1px;}
.rp .pos {color: #2F6B45;} .rp .neg {color: #9A3F3F;}
.rp-two {width: 100%; table-layout: fixed; border-collapse: collapse; margin: 2px 0;}
.rp-two td {vertical-align: top; padding: 0;}
.rp-two, .rp-two tr, .rp-two td {page-break-inside: avoid; break-inside: avoid;}
.rp-fig {margin: 8px 0 12px; page-break-inside: avoid; break-inside: avoid;}
.rp-fig.flow {page-break-inside: auto; break-inside: auto;}
.rp-keep {page-break-inside: avoid; break-inside: avoid;}
.rp-ft {font-size: 10px; font-weight: 700; margin-bottom: 4px;}
.rp-note {font-size: 9px; color: #5B6571; margin-top: 3px;}
.rp-table {width: 100%; border-collapse: collapse; font-size: 10px;}
.rp-table th {text-align: left; border-bottom: 1.5px solid #1D232B; padding: 4px 6px; font-size: 8.5px; font-weight: 700;
              letter-spacing: .07em; text-transform: uppercase; color: #5B6571;}
.rp-table td {border-bottom: 1px solid #E3E7EC; padding: 3.5px 6px; vertical-align: top;}
.rp-table td.nw, .rp-table th.nw {white-space: nowrap;}
.rp-table th.num, .rp-table td.num {text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums;}
.rp-table tr {page-break-inside: avoid; break-inside: avoid;}
.rp-table thead {display: table-header-group;}
.rp-table tr.tot td {font-weight: 700; border-top: 1.5px solid #1D232B; border-bottom: none;}
.rp-table td.pos {color: #2F6B45;} .rp-table td.neg {color: #9A3F3F;}
.rp-donut {width: 100%; border-collapse: collapse;}
.rp-donut td {vertical-align: middle;} .rp-donut td.d {width: 160px; padding-right: 8px;}
.rp-leg {width: 100%; border-collapse: collapse; font-size: 9.5px;}
.rp-leg td {padding: 2.5px 3px; border-bottom: 1px solid #EEF1F4;}
.rp-leg td.dot {width: 12px;} .rp-leg td.dot span {display: inline-block; width: 8px; height: 8px; border-radius: 2px;}
.rp-leg td.num {text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums;} .rp-leg td.mut {color: #5B6571; width: 38px;}
.rp-total {width: 100%; border-collapse: collapse; margin-top: 12px; border: 1px solid #1D232B; page-break-inside: avoid;}
.rp-total td {padding: 8px 12px; vertical-align: top;}
.rp-total .t {font-size: 8.5px; font-weight: 700; letter-spacing: .09em; text-transform: uppercase; color: #5B6571; display: block;}
.rp-total .big {font-size: 20px; font-weight: 700; display: block;} .rp-total .m {font-size: 11.5px; font-weight: 700; display: block;}
.rp-goal {width: 100%; border-collapse: collapse; margin-bottom: 2px;}
.rp-goal td {padding: 5px 0 1px; vertical-align: top;} .rp-goal .n {font-weight: 700; font-size: 10.5px;}
.rp-goal .s {font-size: 9px; color: #5B6571;} .rp-goal td.r {text-align: right; font-weight: 700; white-space: nowrap;}
.rp-goal .b {height: 5px; background: #E8EBEF; border-radius: 3px; overflow: hidden; margin: 3px 0 7px;}
.rp-goal .b span {display: block; height: 100%;}
.rp-center {text-align: center;}
.rp-priv {border: 1px dashed #AEB7C1; padding: 24px; text-align: center; color: #5B6571; margin-top: 30px;}
/* the receipt: table based so it prints identically everywhere, sized to use the page */
.rp .receipt {position: relative; text-align: left; background: #F1EEE3; color: #1C1C1C; width: 100%; max-width: 580px; margin: 6px auto 0;
              padding: 30px 32px 26px; border: 1px solid #D8D4C8; font-family: 'IBM Plex Mono', 'Courier New', monospace;
              box-shadow: none; page-break-inside: avoid; break-inside: avoid;}
.rp .receipt::before, .rp .receipt::after {display: none;}
.rp .rc-head {text-align: center;} .rp .rc-brand {font-size: 19px; font-weight: 700; letter-spacing: .18em; text-transform: uppercase;}
.rp .rc-sub {font-size: 11px; color: #6B685E; margin-top: 5px;}
.rp .rc-hr {border-top: 1px dashed #9A9588; margin: 15px 0;}
.rp .rc-sec {font-weight: 700; letter-spacing: .2em; font-size: 12px; margin: 6px 0 8px;}
.rp .rc-row {display: table; width: 100%; font-size: 12.5px; padding: 3px 0; border-bottom: 1px dotted #CFCABB;}
.rp .rc-row > span {display: table-cell; vertical-align: baseline; white-space: nowrap;}
.rp .rc-row .d {display: none;} .rp .rc-row .n {width: 100%; max-width: none; overflow: hidden;}
.rp .rc-row .p {color: #8A867B; font-size: 10.5px; padding: 0 12px 0 8px;} .rp .rc-row .a {font-weight: 600; text-align: right;}
.rp .rc-row.child {padding-left: 16px; font-size: 11.5px; color: #4A4840;}
.rp .rc-row.total {font-weight: 700; border-top: 1px solid #1C1C1C; border-bottom: none; margin-top: 7px; padding-top: 6px;}
.rp .rc-empty {color: #8A867B; font-size: 11px; text-align: center; padding: 6px 0;}
.rp .rc-net {display: table; width: 100%; font-size: 17px; font-weight: 700; border-top: 1px solid #1C1C1C;
             border-bottom: 3px double #1C1C1C; padding: 10px 0; margin: 14px 0 8px;}
.rp .rc-net > span {display: table-cell;} .rp .rc-net > span:last-child {text-align: right;}
.rp .rc-net.pos {color: #25603A;} .rp .rc-net.neg {color: #8E3636;}
.rp .rc-meta {display: table; width: 100%; font-size: 11px; color: #5B584F;}
.rp .rc-meta > span {display: table-cell;} .rp .rc-meta > span:last-child {text-align: right;}
.rp .rc-qr {width: 170px; margin: 20px auto 5px;} .rp .rc-qr svg {display: block; width: 100%; height: auto;}
.rp .rc-qr-cap {text-align: center; font-size: 9px; letter-spacing: .16em; color: #6B685E;}
/* shown alone when printing from the app, hidden on screen */
.print-report {display: none;}
.rp-sheet {max-width: 794px; margin: 18px auto; padding: 14mm; background: #fff; box-shadow: 0 2px 18px rgba(0,0,0,.18);}
.rp-bar {text-align: center; margin: 14px 0 0;}
.rp-bar button {padding: 8px 18px; border-radius: 6px; border: 1px solid #1D232B; background: #fff; font-size: 13px; cursor: pointer;}
@media print {
  .rp-sheet {margin: 0; padding: 0; max-width: none; box-shadow: none;} .rp-bar {display: none;}
  html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], section.main, .main,
  [data-testid="stMainBlockContainer"], .block-container {
      height: auto !important; max-height: none !important; overflow: visible !important; position: static !important;
      background: #fff !important; margin: 0 !important; padding: 0 !important; max-width: none !important; width: auto !important;}
  section[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stSidebarCollapseButton"],
  header, [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], footer {display: none !important;}
  [data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] > *:not(:has(.print-report)) {display: none !important;}
  .print-report {display: block !important; background: #fff !important; color: #1D232B !important;}
}
"""


# ------------------------------------------------------------------ building blocks
def section(title: str) -> str:
    return f'<div class="rp-sec">{esc(title)}</div>'


def tiles(items, cols: int = 4) -> str:
    """items: (label, value, sub, accent, spark_values|None, cls). Table based so it prints everywhere."""
    rows = []
    for i in range(0, len(items), cols):
        chunk, cells = items[i:i + cols], []
        for label, value, sub, accent, spark_vals, cls in chunk:
            sp = sc.spark(spark_vals, accent) if spark_vals is not None else ""
            cells.append(f'<td style="border-top:3px solid {accent};width:{100 / cols:.2f}%"><div class="l">{esc(label)}</div>'
                         f'<div class="v {cls}"{" style=\'font-size:12.5px;padding-top:3px\'" if len(str(value)) > 17 else ""}>{esc(value)}</div><div class="s">{esc(sub)}</div>{sp}</td>')
        cells += [f'<td class="e" style="width:{100 / cols:.2f}%"></td>'] * (cols - len(chunk))
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return f'<div class="rp-tw"><table class="rp-tiles">{"".join(rows)}</table></div>'


def two(left: str, right: str, ratio=(1, 1)) -> str:
    a, b = ratio
    pa = 100 * a / (a + b)
    return (f'<table class="rp-two"><tr><td style="width:{pa:.1f}%;padding-right:9px">{left}</td>'
            f'<td style="width:{100 - pa:.1f}%;padding-left:9px">{right}</td></tr></table>')


def figure(title: str, content: str, note: str = "", flow: bool = False) -> str:
    n = f'<div class="rp-note">{esc(note)}</div>' if note else ""
    return f'<div class="rp-fig{" flow" if flow else ""}"><div class="rp-ft">{esc(title)}</div>{content}{n}</div>'


def table(df: pd.DataFrame, num_cols=(), total_last: bool = False, signed_cols=(), max_rows: int = 2000) -> str:
    cols = list(df.columns)
    NOWRAP = {"Date", "Kind", "Type", "Amount", "Moved", "When"}
    head = "".join(f'<th class="{"num" if c in num_cols else ("nw" if c in NOWRAP else "")}">{esc(c)}</th>' for c in cols)
    shown, rows = df.head(max_rows), []
    for i, rec in enumerate(shown.itertuples(index=False)):
        tds = []
        for c, v in zip(cols, rec):
            isnum = c in num_cols
            numeric = isinstance(v, (int, float)) and not (isinstance(v, float) and v != v)
            txt = f"{v:,.2f}" if isnum and numeric else ("" if v is None else str(v))
            klass = ["num"] if isnum else (["nw"] if c in NOWRAP else [])
            if c in signed_cols and numeric and v != 0:
                klass.append("pos" if v > 0 else "neg")
            tds.append(f'<td class="{" ".join(klass)}">{esc(txt)}</td>')
        tr = ' class="tot"' if total_last and i == len(shown) - 1 else ""
        rows.append(f"<tr{tr}>" + "".join(tds) + "</tr>")
    note = (f'<div class="rp-note">Showing the first {max_rows:,} of {len(df):,} rows.</div>' if len(df) > max_rows else "")
    return f'<table class="rp-table"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table>{note}'


def totals(big_label: str, big_value: str, minis) -> str:
    cells = "".join(f'<td><span class="t">{esc(l)}</span><span class="m">{esc(v)}</span></td>' for l, v in minis)
    return (f'<table class="rp-total"><tr><td style="width:30%"><span class="t">{esc(big_label)}</span>'
            f'<span class="big">{esc(big_value)}</span></td>{cells}</tr></table>')


def top_n(items, n: int = 8, other: str = "Other"):
    """Keep the n biggest slices and fold the rest into 'Other' (keeps legends short on paper)."""
    items = sorted(items, key=lambda x: -x[1])
    if len(items) <= n:
        return items
    return items[:n] + [(other, sum(v for _, v in items[n:]))]


def colored(items, palette=None):
    palette = palette or sc.PAL
    return [(l, v, palette[i % len(palette)]) for i, (l, v) in enumerate(items)]


def privacy_page(title: str = "") -> str:
    return (section("Privacy mode is on") + '<div class="rp-priv">Amounts are hidden, so this report is blank on purpose.<br>'
            "Turn off “Hide amounts” in the sidebar to print the full report.</div>")


# ------------------------------------------------------------------ page / document
def keep_headings(body: str) -> str:
    """Wrap every section heading together with the block that follows it, so a page break can never
    leave the heading stranded at the bottom. Long tables are left to flow."""
    import re
    out, pos = [], 0
    for m in re.finditer(r'<div class="rp-sec">.*?</div>', body):
        if m.start() < pos:
            continue
        e = m.end()
        nxt = re.match(r'<(div|table)\b[^>]*>', body[e:])
        if not nxt or 'class="rp-table"' in nxt.group(0):
            continue
        tag, depth, i = nxt.group(1), 0, e
        for t in re.finditer(rf'<{tag}\b|</{tag}>', body[e:]):
            depth += 1 if t.group(0).startswith("<" + tag) else -1
            if depth == 0:
                i = e + t.end()
                break
        else:
            continue
        out += [body[pos:m.start()], '<div class="rp-keep">', body[m.start():i], "</div>"]
        pos = i
    return "".join(out) + body[pos:]


def page(title: str, subtitle: str, meta: str, body: str) -> str:
    body = keep_headings(body)
    gen = dt.datetime.now().strftime("%d %b %Y, %H:%M")
    return (f'<div class="rp"><div class="rp-head"><div class="rp-title">{esc(title)}</div>'
            f'<div class="rp-sub">{esc(subtitle)}</div><div class="rp-meta">{esc(meta)} · Generated {gen}</div></div>{body}</div>')


def embed(page_html: str) -> str:
    """Hidden in the app; shown alone (and everything else hidden) when you print."""
    return f'<style>{CSS}</style><div class="print-report">{page_html}</div>'


def document(title: str, page_html: str) -> str:
    """Self-contained printable HTML: opens in any browser, works offline."""
    out = (f'<!doctype html><html><head><meta charset="utf-8"><title>{esc(title)}</title><style>{CSS}'
           f'body {{margin: 0; background: #E9ECEF;}}</style></head><body><div class="rp-bar">'
           f'<button onclick="window.print()">Print / save as PDF</button></div>'
           f'<div class="rp-sheet">{page_html}</div></body></html>')
    return out.replace("$", "&#36;")


# ================================================================== helpers for the builders
def _nan(x) -> bool:
    return x is None or (isinstance(x, float) and x != x)


def pct(x, sign=False) -> str:
    return "n/a" if _nan(x) else (f"{x * 100:+.2f}%" if sign else f"{x * 100:.2f}%")


def months_txt(x) -> str:
    return "n/a" if _nan(x) else ("∞" if x == float("inf") else f"{x:,.2f} months")


_LEVEL_INK = {"green": "#2F6B45", "yellow": "#8A6A1C", "red": "#9A3F3F"}


def runway_status(v):
    st_ = kpis.runway_status(v)
    return None if st_ is None else (st_[0], _LEVEL_INK[st_[1]])


def vol_level(v):
    return kpis.volatility_level(v)[0]


def plabels(periods, step):
    fmt = {"Day": "%d %b", "Week": "%d %b", "Month": "%b %y", "Year": "%Y"}[step]
    return [pd.Timestamp(p).strftime(fmt) for p in periods]


def _clean(vals):
    return [None if _nan(v) else float(v) for v in vals]


def gauge_figure(title, val, formula):
    if _nan(val) or val == float("inf"):
        body = f'<div class="rp-center" style="font-size:22px;font-weight:700;padding:34px 0">{esc(months_txt(val))}</div>'
    else:
        body = sc.gauge(val)
    st_ = runway_status(val)
    status = f'<div class="rp-center" style="font-weight:700;color:{st_[1]};margin-top:2px">{esc(st_[0])}</div>' if st_ else ""
    return figure(title, body + status, formula)


def _tile(label, value, sub, accent, spark_vals=None, cls=""):
    return (label, value, sub, accent, spark_vals, cls)


# ================================================================== Dashboard
def dashboard(*, hide, period, step, detail, nw, nw_series, monthly, balances, currency_totals, s_time, pn, expense, income,
              flows_t, net, reserve=0.0):
    sub, meta = "Balances, net worth and cash flow", f"{period} · Time step: {step} · Detail: {detail}"
    if hide:
        return page("Dashboard", sub, meta, privacy_page())
    inc_t, exp_t = float(monthly["income"].sum()), float(monthly["expense"].sum())
    saved = inc_t - exp_t
    body = section("Key figures") + tiles([
        _tile("Net worth", sc.money(nw), "current total", sc.NETWORTH, nw_series),
        _tile("Income", sc.money(inc_t), "selected period", sc.INCOME, monthly["income"].tolist()),
        _tile("Expenses", sc.money(exp_t), "selected period", sc.EXPENSE, monthly["expense"].tolist()),
        _tile("Savings", sc.money(saved, sign=True), "savings rate " + (pct(saved / inc_t) if inc_t else "n/a"), sc.GOLD,
              (monthly["income"] - monthly["expense"]).tolist(), "pos" if saved >= 0 else "neg")], 4)

    rows = [{"Account": str(r.account).replace(" (Closed)", "") + (" (closed)" if r.closed else ""),
             "Balance": sc.money(r.balance, sym=r.symbol)} for r in balances.itertuples()]
    rows += [{"Account": f"Total ({r.symbol})", "Balance": sc.money(r.balance, sym=r.symbol)} for r in currency_totals.itertuples()]
    pos = [(str(r.account).replace(" (Closed)", ""), r.balance) for r in balances.itertuples() if r.balance > 0]
    body += section("Accounts") + two(
        figure("Balances", table(pd.DataFrame(rows), num_cols=("Balance",), total_last=True), flow=True),
        figure("Assets distribution", donut_or_note(pos, sc.money(sum(v for _, v in pos)), "Total")), (1, 1))

    if len(s_time):
        piv = s_time.pivot_table(index="Period", columns="Account", values="Balance", aggfunc="sum").sort_index()
        top = piv.ffill().iloc[-1].sort_values(ascending=False).head(8).index
        ch = sc.XY(plabels(piv.index, step), height=235)
        for i, acc in enumerate(top):
            ch.line(str(acc).replace(" (Closed)", ""), _clean(piv[acc].tolist()), sc.PAL[i % len(sc.PAL)])
        body += figure("Account balance over time", ch.render(),
                       "The eight largest accounts." if piv.shape[1] > 8 else "")

    body += section("Net worth & cash flow")
    if len(pn):
        ch = sc.XY(plabels(pn["Period"], step), height=215).line("Net worth", _clean(pn["Balance"].tolist()), sc.NETWORTH, area=True)
        if reserve and reserve > 0:
            ch.hline(reserve, "Reserve")
        body += figure("Net worth", ch.render())

    def donut_for(df):
        items = top_n([(r.Category, r.Amount) for r in df.itertuples() if r.Amount > 0])
        return donut_or_note(items, sc.money(sum(v for _, v in items)), "Total")

    body += two(figure("Expenses by category", donut_for(expense)), figure("Income by category", donut_for(income)), (1, 1))
    if len(flows_t):
        g = flows_t.groupby(["Period", "Type"])["Amount"].sum().unstack(fill_value=0.0)
        periods = sorted(set(g.index) | set(net["Period"]))
        get = lambda col: [float(g[col].get(p, 0.0)) if col in g.columns else 0.0 for p in periods]
        ch = sc.XY(plabels(periods, step), height=230).bars([("Income", get("Income"), sc.INCOME), ("Expense", get("Expense"), sc.EXPENSE)])
        nmap = dict(zip(net["Period"], net["Net"]))
        ch.line("Net", [float(nmap.get(p, 0.0)) for p in periods], sc.INK, width=1.6)
        body += figure("Income vs expenses over time", ch.render())
    return page("Dashboard", sub, meta, body)


def donut_or_note(items, center, sub):
    items = colored(top_n(items)) if items else []
    return sc.donut_block(items, center, sub) if items else '<div class="rp-note">Nothing to show in this period.</div>'


# ================================================================== KPIs
def kpis_report(*, hide, period, basis, k, availability, liquid, monthly, excl_current):
    sub, meta = "Runway, burn rate and volatility from your GnuCash history", f"{period} · runway basis: {basis}"
    if hide:
        return page("Key indicators", sub, meta, privacy_page())
    body = section("Runway") + two(
        gauge_figure("Runway (months)", k["runway"], f"{basis} ÷ median burn rate"),
        gauge_figure("Worst-case runway (months)", k["worst_runway"], f"{basis} ÷ (median burn + std. deviation)"), (1, 1))
    wn = k["worst_net_runway"]
    body += section("Position") + tiles([
        _tile("Availability", sc.money(availability), f"liquid {sc.money(liquid)} · {pct(k['liquidity_pct'])}", sc.NETWORTH),
        _tile("Savings rate", pct(k["savings_rate"]), "(income − expenses) ÷ income", sc.GOLD, None,
              "" if _nan(k["savings_rate"]) else ("pos" if k["savings_rate"] >= 0 else "neg")),
        _tile("Net runway", ("n/a" if _nan(k["net_monthly"]) else sc.money(k["net_monthly"], sign=True) + " / month"),
              f"{pct(k['net_rate'], True)} of median income", sc.INCOME, None,
              "" if _nan(k["net_monthly"]) else ("pos" if k["net_monthly"] >= 0 else "neg")),
        _tile("Worst-case net runway", months_txt(wn), "worst-case burn vs. downside income", sc.EXPENSE)], 4)
    if availability > 0:
        lf = min(max(liquid / availability, 0.0), 1.0)
        items = [("Liquid", lf, sc.TEAL), ("Other", 1 - lf, sc.NETWORTH)]
        leg = sc.legend_table([("Liquid", liquid, sc.TEAL), ("Other", availability - liquid, sc.NETWORTH)], total=availability, style="max-width:380px")
        body += figure("Availability: liquid versus the rest", sc.segbar(items) + leg)

    body += section("Monthly behaviour")
    labels = [p.to_timestamp().strftime("%b %y") for p in monthly.index] if len(monthly) else []

    def panel(title, series, med, sd, vol, color):
        stats = pd.DataFrame([{"Measure": "Median", "Value": "n/a" if _nan(med) else sc.money(med)},
                              {"Measure": "Standard deviation", "Value": "n/a" if _nan(sd) else sc.money(sd)},
                              {"Measure": "Volatility (std. dev. ÷ median)", "Value": f"{pct(vol)} · {vol_level(vol)}"}])
        ch = ""
        if len(monthly):
            c = sc.XY(labels, width=380, height=200).bars([("Monthly", series.tolist(), color)])
            if not _nan(med) and not _nan(sd):
                c.band([max(0.0, med - sd)] * len(labels), [med + sd] * len(labels), color, 0.13, "±1σ")
            if not _nan(med):
                c.hline(med, f"Median {sc.money(med)}", sc.INK)
            ch = c.render()
        return figure(title, ch + table(stats, num_cols=("Value",)))

    body += two(panel("Expenses · monthly", monthly["expense"], k["median_burn"], k["expense_std"], k["expense_vol"], sc.EXPENSE),
                panel("Income · monthly", monthly["income"], k["median_income"], k["income_std"], k["income_vol"], sc.INCOME), (1, 1))
    body += f'<div class="rp-note">Statistics use {k["months"]} month(s)' + (" (current month excluded)." if excl_current else ".") + "</div>"
    return page("Key indicators", sub, meta, body)


# ================================================================== Transactions
def transactions_report(*, hide, period, view, filters, df, num_cols, total_big, minis, max_rows=1500):
    sub, meta = "Search, filter and total any slice of the ledger", f"{period} · view: {view}"
    if hide:
        return page("Transactions", sub, meta, privacy_page())
    body = section("Filters")
    if filters:
        body += table(pd.DataFrame(filters, columns=["Filter", "Value"]))
    else:
        body += '<div class="rp-note">No filters: every transaction in the period.</div>'
    body += section(f"Results · {len(df):,} {'transactions' if view == 'Transactions' else 'rows'}")
    df = df.loc[:, [c for c in df.columns if (df[c].astype(str).str.strip() != "").any()]]      # no empty columns
    body += table(df, num_cols=tuple(c for c in num_cols if c in df.columns), signed_cols=("Amount",), max_rows=max_rows) if len(df) else '<div class="rp-note">Nothing matches.</div>'
    body += totals("Total amount · filtered", total_big, minis)
    body += '<div class="rp-note">Totals add up one side of each transaction only, so nothing is counted twice or cancels out.</div>'
    return page("Transactions", sub, meta, body)


# ================================================================== Receipt
def receipt_report(*, hide, period, receipt_html):
    sub, meta = "Every expense, then every income, itemised", period
    if hide:
        return page("Cash flow receipt", sub, meta, privacy_page())
    return page("Cash flow receipt", sub, meta, f'<div class="rp-center">{receipt_html}</div>')


# ================================================================== Plan
def plan_report(c: dict):
    sub = "A budget for the year ahead and where the surplus goes"
    meta = f"{c['scenario']} · {c['plan_period']} · baseline {c['base_label']}"
    if c["hide"]:
        return page("Financial plan", sub, meta, privacy_page())
    body = section("Assumptions") + table(c["assumptions"])
    body += section("Starting point") + tiles([_tile(*t[:3], t[3]) for t in c["start_tiles"]], 5)
    body += section("The budget") + tiles([_tile(*t[:3], t[3], None, t[4] if len(t) > 4 else "") for t in c["budget_tiles"]], 4)
    cmp_items = [(r.name, [r.annual, r.planned]) for r in c["cat_expense"].assign(_m=lambda d: d[["annual", "planned"]].max(axis=1))
                 .sort_values("_m", ascending=False).head(9).itertuples()]
    body += two(figure("From baseline surplus to planned surplus", sc.waterfall(c["bridge"], 380, 235)),
                figure("Expenses: baseline versus plan", sc.hbars(cmp_items, [("Baseline", "#AEB7C1"), ("Plan", sc.EXPENSE)],
                                                                 width=380, label_w=90, value_fmt=lambda v: sc.money(v, 0), bar_h=9, row_pad=7)), (1, 1))
    body += figure("Budget table", table(c["budget_df"], num_cols=("Baseline / year", "Plan / year", "Change"), total_last=True), flow=True)
    if c.get("oneoffs") is not None and len(c["oneoffs"]):
        body += figure("One-off and new items", table(c["oneoffs"], num_cols=("Amount",)))
    body += section("Where the surplus goes")
    if c.get("alloc_msg"):
        body += f'<div class="rp-note" style="color:#9A3F3F;font-weight:700">{esc(c["alloc_msg"])}</div>'
    items = colored(c["alloc_items"], [sc.PAL[i % len(sc.PAL)] for i in range(len(c["alloc_items"]))])
    if items:
        body += figure("The plan for the surplus", sc.segbar(items) + sc.legend_table(items))
    body += figure("Buckets at a glance", table(c["alloc_df"], num_cols=("Per month", "Per year", "Growth", "End of plan"), total_last=True), flow=True)
    body += section("What the plan delivers") + two(
        gauge_figure("Runway today (months)", c["runway_now"], c["runway_basis"] + " ÷ median burn"),
        gauge_figure("Runway after the plan (months)", c["runway_end"], "with the plan's money and spending"), (1, 1))
    body += tiles([_tile(*t[:3], t[3]) for t in c["kpi_tiles"]], 4)
    body += f'<div class="rp-note" style="margin-top:6px">{esc(c["ef_text"])}</div>'
    body += section("Month by month")
    mo = c["months"]
    ch = sc.XY([p.to_timestamp().strftime("%b %y") for p in mo.index], height=235, y2_fmt=sc.axis_money).bars(
        [("Income", mo["income"].tolist(), sc.INCOME), ("Expenses", mo["expense"].tolist(), sc.EXPENSE)]).line(
        "Cash after allocation", [float(v) for v in c["cash_path"]], sc.INK, axis="r", width=1.8)
    body += figure("Planned cash flow", ch.render())
    body += figure("Month table", table(c["month_df"], num_cols=("Income", "Expenses", "Net", "Cash after allocation"), total_last=True), flow=True)
    if c.get("compare") is not None and c["compare"].shape[1] > 2:
        body += section("Scenarios") + table(c["compare"], num_cols=tuple(c["compare"].columns[1:]))
    return page("Financial plan", sub, meta, body)


# ================================================================== Simulator
def simulator_report(c: dict):
    sub, meta = "Long-term projections, savings goals and stress tests", f"Based on {c['source']}"
    if c["hide"]:
        return page("Simulator", sub, meta, privacy_page())
    mc = c["mc"]
    n = len(mc["det"])
    yr0 = pd.Timestamp.now().year
    k = max(1, -(-(n - 1) // 8))                         # at most about eight year labels
    labels = [str(yr0 + y) if y % k == 0 else "" for y in range(n)]    # one point per year
    ch = sc.XY(labels, height=250, max_labels=n, zero=True)
    ch.band(mc["p10"].tolist(), mc["p90"].tolist(), sc.NETWORTH, 0.11, "10–90%")
    ch.band(mc["p25"].tolist(), mc["p75"].tolist(), sc.NETWORTH, 0.20, "25–75%")
    ch.line("Median", mc["p50"].tolist(), sc.NETWORTH, markers=False, width=2.2)
    ch.line("Plan without volatility", mc["det"].tolist(), sc.INK, dash=True, markers=False, width=1.3)
    ch.line("Contributed", mc["contributed"].tolist(), "#8B95A1", dash=True, markers=False, width=1.2)
    if c["target"] > 0:
        ch.line("Target", [float(v) for v in c["target_path"]], sc.GOLD, dash=True, markers=False, width=1.3)
    body = section("Assumptions") + table(c["assumptions"])
    body += section("Wealth projection") + figure(c["fan_title"], ch.render(),
                                                  "Bands show where 80% and 50% of 1,000 simulated futures end; the median sits slightly "
                                                  "below the no-volatility line because losses hurt more than equal gains help.")
    body += tiles([_tile(*t[:3], t[3]) for t in c["wealth_tiles"]], 4)
    body += section("Goals")
    rows = ""
    for g in c["goals"]:
        pctv = min(max(g["saved"] / g["target"], 0), 1) * 100 if g["target"] > 0 else 0
        if g.get("done"):
            req = g["note"]
        elif g.get("due"):
            req = f"{sc.money(max(g['target'] - g['saved'], 0.0))} now"
        else:
            req = f"{sc.money(g['required'])} / month"
        small = "" if g.get("done") else f'<div class="s" style="font-weight:400">{esc(g["note"])}</div>'
        col = sc.INCOME if g.get("done") else (sc.EXPENSE if g.get("due") else sc.NETWORTH)
        rows += (f'<table class="rp-goal"><tr><td><div class="n">{esc(g["name"])}</div><div class="s">{esc(g["sub"])} · '
                 f'{sc.money(g["saved"])} of {sc.money(g["target"])} · {pctv:.0f}%</div></td>'
                 f'<td class="r">{esc(req)}{small}</td></tr></table><div class="b"><span style="width:{pctv:.1f}%;background:{col}"></span></div>')
    body += rows or '<div class="rp-note">No goals yet.</div>'
    body += tiles([_tile(*t[:3], t[3], None, t[4] if len(t) > 4 else "") for t in c["goal_tiles"]], 3)
    body += section("Stress test")
    hor = len(c["paths"][0][1]) - 1
    sch = sc.XY([str(m) if m % 6 == 0 else "" for m in range(hor + 1)], height=235, max_labels=hor + 1)
    for name, arr, color, dash in c["paths"]:
        sch.line(name, [float(v) for v in arr], color, dash=(dash == "dot"), markers=False, width=2.0)
    sch.hline(0, "Out of cash", sc.EXPENSE)
    body += figure("Your cash, month by month (months from now)", sch.render(), c["stress_note"])
    body += tiles([_tile(*t[:3], t[3], None, t[4] if len(t) > 4 else "") for t in c["stress_tiles"]], 3)
    if c.get("sens"):
        base, burn = c["sens"]
        mult = [0.5 + 0.05 * i for i in range(31)]
        ys = [max(0.0, base / (burn * m)) for m in mult]
        top = max(max(ys) * 1.08, 26.0)
        sens = sc.XY([f"{int(round(m * 100))}%" for m in mult], height=215, max_labels=8, zero=True, y_fmt=lambda v: f"{v:g} mo")
        for (a, b, color), hi in zip(sc.ZONES, (6, 12, top)):
            sens.band([a] * len(mult), [hi] * len(mult), color, 0.12)
        sens.line("Runway", ys, sc.NETWORTH, markers=False, width=2.4).vmark(10, "Today")
        body += figure("What if your spending changes? Runway (months) by monthly spending versus today",
                       sens.render(), "Green is 12+ months, amber 6–12, red under 6.")
    body += section("Financial independence") + tiles([_tile(*t[:3], t[3]) for t in c["fi_tiles"]], 4)
    body += '<div class="rp-note">Illustrations, not advice: real returns, taxes and spending change.</div>'
    return page("Simulator", sub, meta, body)


# ================================================================== Home
def home_report(c: dict):
    sub, meta = "Your GnuCash book at a glance", c["meta"]
    body = section("Your book in numbers") + tiles([_tile(*t[:3], t[3], t[4] if len(t) > 4 else None) for t in c["tiles"]], 4)
    body += section("Activity") + figure("Daily activity · last 12 months", sc.heatmap(c["per_day"]))
    pm = c["per_month"]
    wd = c["weekday"]
    body += two(
        figure("Transactions per month", sc.XY([p.to_timestamp().strftime("%b %y") for p in pm.index], width=470, height=205, y_fmt=lambda v: f"{v:g}")
               .bars([("Transactions", [float(v) for v in pm.values], sc.NETWORTH)]).render()),
        figure("By weekday", sc.XY(list(wd.index), width=250, height=205, y_fmt=lambda v: f"{v:g}")
               .bars([("Transactions", [float(v) for v in wd.values], sc.PURPLE)]).render()), (2, 1))
    body += section("Distribution")
    body += two(figure("Transactions by account", sc.hbars([(l, [float(n)]) for l, n in c["wallets"]], [("Transactions", sc.NETWORTH)],
                                                           width=380, label_w=120, value_fmt=lambda v: f"{int(v):,}", bar_h=10, row_pad=8),
                       "Each transaction is counted once, under the account where the money moved."),
                figure("Transaction mix", sc.segbar([(l, v, col) for l, v, col in c["mix"]]) +
                       sc.legend_table([(l, v, col) for l, v, col in c["mix"]], value_fmt=lambda v: f"{int(v):,}")), (1, 1))
    body += two(figure("Most frequent descriptions", sc.hbars([(l, [float(n)]) for l, n in c["top_desc"]], [("Count", sc.NETWORTH)],
                                                              width=380, label_w=130, value_fmt=lambda v: f"{int(v):,}", bar_h=10, row_pad=8)),
                figure("Tags", sc.hbars([(f"#{l}", [float(n)]) for l, n in c["tags"]], [("Count", sc.GOLD)], width=380, label_w=100,
                                        value_fmt=lambda v: f"{int(v):,}", bar_h=10, row_pad=8) if c["tags"] else
                       '<div class="rp-note">No tags yet.</div>'), (1, 1))
    return page("Home", sub, meta, body)
