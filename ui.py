"""Design system: calm dark theme, CSS, HTML components and Plotly charts."""
import html
import math
import os
import zlib

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import kpis

CUR = "€"
MASK = "••••"
FONT = "Inter, -apple-system, 'Segoe UI', Roboto, sans-serif"

# muted, desaturated palette
PALETTE = ["#7A9CC6", "#7FAE93", "#C8A66A", "#C98080", "#9B92BD", "#7AAEB0",
           "#C99572", "#A5B38B", "#8E9AA8", "#B79BB0"]
C_INCOME, C_EXPENSE, C_NW = "#7FAE93", "#C98080", "#7A9CC6"
C_TEAL, C_GOLD, C_PURPLE = "#7AAEB0", "#C8A66A", "#9B92BD"
BG, SURFACE = "#0D1117", "#151B23"
TRANSP = "rgba(0,0,0,0)"
GRID = "rgba(255,255,255,0.06)"
LINE = "rgba(255,255,255,0.08)"
TEXT, MUTED = "#E7EAEE", "#8B95A1"
HOVER_BG = "#1B222C"

H_DONUT, H_LINE, H_ACC = 340, 380, 400
_b = kpis.RUNWAY_BANDS
GAUGE_STEPS = [(0, _b[0], "#C26B6B"), (_b[0], _b[1], "#C8A25A"), (_b[1], _b[2], "#6FA582")]
STATUS_COLORS = {"green": C_INCOME, "yellow": C_GOLD, "red": C_EXPENSE, "grey": MUTED}

_BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap');

/* ---------- canvas ---------- */
.stApp {font-family: Inter, -apple-system, 'Segoe UI', Roboto, sans-serif; color: #E7EAEE;
        background: radial-gradient(900px 380px at 50% -220px, rgba(122,156,198,0.07), transparent), #0D1117;}
[data-testid="stAppViewContainer"], [data-testid="stMain"], .main {background: transparent;}
header[data-testid="stHeader"] {background: transparent;}
[data-testid="stDecoration"] {display: none;}
#MainMenu, footer {visibility: hidden;}
.block-container {padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1480px;}
*::-webkit-scrollbar {width: 8px; height: 8px;}
*::-webkit-scrollbar-thumb {background: rgba(255,255,255,0.12); border-radius: 8px;}

/* ---------- sidebar ---------- */
section[data-testid="stSidebar"] {border-right: 1px solid rgba(255,255,255,0.07);}
section[data-testid="stSidebar"] > div {background: #0F141B;}
section[data-testid="stSidebar"] h2 {font-size: 0.7rem !important; font-weight: 600 !important;
    text-transform: uppercase; letter-spacing: 0.14em; color: #8B95A1; margin-top: 0.8rem;}

/* ---------- page header ---------- */
.hero {padding: 4px 2px 18px; margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.08);}
.hero-t {font-size: 1.7rem; font-weight: 600; letter-spacing: -0.02em; line-height: 1.2; color: #E7EAEE;}
.hero-s {color: #8B95A1; font-size: 0.93rem; margin: 5px 0 14px;}
.chip {display: inline-block; padding: 3px 10px; border-radius: 6px; font-size: 0.74rem; font-weight: 500;
       margin: 0 6px 4px 0; color: #AEB7C2; background: rgba(255,255,255,0.04);
       border: 1px solid rgba(255,255,255,0.08);}

/* ---------- section titles ---------- */
.sec {display: flex; align-items: center; gap: 14px; margin: 2.1rem 0 0.95rem; font-size: 0.72rem;
      font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: #8B95A1;}
.sec::after {content: ""; flex: 1; height: 1px; background: rgba(255,255,255,0.08);}
.sec small {text-transform: none; letter-spacing: 0; font-weight: 400; color: #5E6875; font-size: 0.78rem;
            margin-left: -6px;}

/* ---------- cards ---------- */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 12px; border: 1px solid rgba(255,255,255,0.08); background: #151B23;
    box-shadow: none; transition: border-color .2s ease;}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {border-color: rgba(255,255,255,0.16);}
.card-title {font-size: 0.7rem; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase;
             color: #8B95A1; margin: 2px 0 10px 2px;}

/* ---------- KPI tiles ---------- */
.kpis {display: grid; grid-template-columns: repeat(var(--cols, 4), 1fr); gap: 12px;}
@media (max-width: 1000px) {.kpis {grid-template-columns: repeat(2, 1fr);}}
.kpi {position: relative; padding: 16px 18px 14px; border-radius: 12px;
      border: 1px solid rgba(255,255,255,0.08); background: #151B23;}
.kpis.flat .kpi {background: rgba(255,255,255,0.02);}
.kpi .l {display: flex; align-items: center; gap: 8px; color: #8B95A1; font-size: 0.68rem; font-weight: 600;
         text-transform: uppercase; letter-spacing: 0.1em; line-height: 1.25;}
.kpi .l::before {content: ""; width: 6px; height: 6px; border-radius: 50%; background: var(--accent); flex: none;}
.kpi .v {font-size: 1.6rem; font-weight: 600; margin-top: 10px; letter-spacing: -0.02em;
         white-space: nowrap; font-variant-numeric: tabular-nums;}
.kpi .s {color: #8B95A1; font-size: 0.78rem; margin-top: 3px;}
.kpi .sp svg {width: 100%; height: 34px; display: block; margin-top: 12px;}
.pos {color: #7FAE93;} .neg {color: #C98080;}

/* ---------- availability panel ---------- */
.hero-kpi {padding: 22px 24px; border-radius: 12px; min-height: 330px; display: flex; flex-direction: column;
           justify-content: center; border: 1px solid rgba(255,255,255,0.08); background: #151B23;}
.hero-kpi .l {display: flex; align-items: center; gap: 8px; color: #8B95A1; font-size: 0.7rem; font-weight: 600;
              text-transform: uppercase; letter-spacing: 0.12em;}
.hero-kpi .l::before {content: ""; width: 6px; height: 6px; border-radius: 50%; background: #7A9CC6;}
.hero-kpi .big {font-size: 2.5rem; font-weight: 600; letter-spacing: -0.03em; margin: 14px 0 4px;
                font-variant-numeric: tabular-nums;}
.hero-kpi .s {color: #8B95A1; font-size: 0.86rem;}
.split {display: flex; height: 8px; border-radius: 4px; overflow: hidden; gap: 2px; margin-top: 26px;
        background: rgba(255,255,255,0.05);}
.split span {display: block; height: 100%;}
.split-leg {display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-top: 12px;
            font-size: 0.8rem; color: #AEB7C2; font-variant-numeric: tabular-nums;}
.split-leg i {display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 7px;}

/* ---------- gauge ---------- */
.gauge-wrap {display: flex; justify-content: center; padding: 6px 0 0;}
.gauge-wrap svg {width: 100%; max-width: 380px; height: auto; overflow: visible;}

/* ---------- meters & pills ---------- */
.meter {margin-top: 12px;}
.meter-bar {height: 4px; border-radius: 3px; background: rgba(255,255,255,0.07); overflow: hidden;}
.meter-bar span {display: block; height: 100%; border-radius: 3px;}
.meter-lab {display: flex; justify-content: space-between; margin-top: 6px; font-size: 0.72rem;
            font-weight: 500; color: #8B95A1; font-variant-numeric: tabular-nums;}
.pill-row {display: flex; justify-content: center; margin: 0 0 4px;}
.pill {display: inline-flex; align-items: center; gap: 7px; padding: 3px 12px; border-radius: 999px;
       font-size: 0.68rem; font-weight: 600; letter-spacing: 0.09em; text-transform: uppercase;
       border: 1px solid transparent;}
.pill i {width: 6px; height: 6px; border-radius: 50%; background: currentColor;}
.pill.green {color: #82B596; border-color: rgba(111,165,130,0.4); background: rgba(111,165,130,0.08);}
.pill.yellow {color: #CDAE70; border-color: rgba(200,162,90,0.4); background: rgba(200,162,90,0.08);}
.pill.red {color: #CC8383; border-color: rgba(194,107,107,0.4); background: rgba(194,107,107,0.08);}

/* ---------- account list ---------- */
.acc-card {display: flex; flex-direction: column;}
.acc-wrap {flex: 1; min-height: 0; overflow-y: auto; padding-right: 4px;}
.acc-foot {border-top: 1px solid rgba(255,255,255,0.14); margin-top: 6px; padding-top: 6px;}
.acc-total {display: flex; justify-content: space-between; align-items: baseline; padding: 6px 2px;
            font-variant-numeric: tabular-nums;}
.acc-total .t {font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; color: #8B95A1; font-weight: 600;}
.acc-total .v {font-size: 1.2rem; font-weight: 600;}
.acc {display: flex; align-items: center; gap: 12px; padding: 10px 6px; border-radius: 8px;
      border-bottom: 1px solid rgba(255,255,255,0.06); transition: background .15s ease;}
.acc:hover {background: rgba(255,255,255,0.03);}
.acc.zero {opacity: 0.4;}
.acc .dot {width: 8px; height: 8px; border-radius: 50%; flex: none;}
.acc .main {flex: 1; min-width: 0;}
.acc .name {font-size: 0.9rem; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
.acc .bar {height: 3px; border-radius: 2px; background: rgba(255,255,255,0.06); margin-top: 7px;}
.acc .bar span {display: block; height: 100%; border-radius: 2px;}
.acc .amt {font-size: 0.9rem; font-weight: 600; white-space: nowrap; font-variant-numeric: tabular-nums;}
.badge {font-size: 0.6rem; padding: 2px 7px; border-radius: 4px; margin-left: 8px; color: #8B95A1;
        border: 1px solid rgba(255,255,255,0.12); font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.06em; vertical-align: middle;}

/* ---------- donut legend ---------- */
.lg-wrap {display: flex; flex-direction: column; justify-content: center; overflow-y: auto;}
.lg {display: flex; align-items: center; gap: 10px; padding: 7px 6px; border-radius: 8px;
     border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.85rem; transition: background .15s;}
.lg:hover {background: rgba(255,255,255,0.03);}
.lg:last-child {border-bottom: none;}
.lg .dot {width: 8px; height: 8px; border-radius: 2px; flex: none;}
.lg .nm {flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: 500;}
.lg .pc {color: #8B95A1; width: 58px; text-align: right; font-variant-numeric: tabular-nums;}
.lg .am {font-weight: 600; width: 92px; text-align: right; font-variant-numeric: tabular-nums;}

/* ---------- totals bar ---------- */
.totbar {display: flex; align-items: center; justify-content: space-between; gap: 24px; flex-wrap: wrap;
         margin-top: 14px; padding: 16px 22px; border-radius: 12px; background: #151B23;
         border: 1px solid rgba(255,255,255,0.08); border-left: 3px solid #7A9CC6;}
.totbar .t {font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; color: #8B95A1;}
.totbar .big .v {font-size: 1.9rem; font-weight: 600; letter-spacing: -0.02em; font-variant-numeric: tabular-nums;}
.totbar .mini {display: flex; gap: 28px; flex-wrap: wrap;}
.totbar .mini > div {display: flex; flex-direction: column; gap: 2px;}
.totbar .mini .v {font-weight: 600; font-size: 0.98rem; font-variant-numeric: tabular-nums;}

/* ---------- segmented bar ---------- */
.segbar {display: flex; height: 10px; border-radius: 5px; overflow: hidden; gap: 2px; margin-top: 6px;}
.segbar span {display: block; height: 100%;}
.seg-leg {display: grid; grid-template-columns: repeat(2, 1fr); gap: 9px 16px; margin-top: 14px; font-size: 0.83rem;}
.seg-leg div {display: flex; align-items: center; gap: 8px; min-width: 0;}
.seg-leg i {width: 8px; height: 8px; border-radius: 2px; flex: none;}
.seg-leg span {white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #AEB7C2;}
.seg-leg b {margin-left: auto; font-weight: 600; font-variant-numeric: tabular-nums;}

/* ---------- data tables & goals ---------- */
.dwrap {max-height: 470px; overflow: auto;}
.dtable {border-collapse: collapse; width: 100%; font-size: 0.86rem;}
.dtable th {text-align: left; padding: 8px 10px; font-size: 0.68rem; font-weight: 600; letter-spacing: 0.1em;
            text-transform: uppercase; color: #8B95A1; border-bottom: 1px solid rgba(255,255,255,0.14);
            white-space: nowrap; position: sticky; top: 0; background: #151B23;}
.dtable td {padding: 9px 10px; border-bottom: 1px solid rgba(255,255,255,0.06); font-variant-numeric: tabular-nums;}
.dtable th.num, .dtable td.num {text-align: right; white-space: nowrap;}
.dtable tbody tr:hover {background: rgba(255,255,255,0.03);}
.dtable tr.tot td {font-weight: 600; border-top: 1px solid rgba(255,255,255,0.20); border-bottom: none;}
.dtable td.pos {color: #7FAE93;} .dtable td.neg {color: #C98080;}
.goal {padding: 13px 6px; border-bottom: 1px solid rgba(255,255,255,0.06);}
.goal:last-child {border-bottom: none;}
.goal-top {display: flex; justify-content: space-between; align-items: baseline; gap: 14px;}
.goal-name {font-weight: 600; font-size: 0.92rem;}
.goal-sub {color: #8B95A1; font-size: 0.78rem; margin-top: 2px;}
.goal-req {font-weight: 600; font-variant-numeric: tabular-nums; white-space: nowrap; text-align: right;}
.goal-req small {display: block; color: #8B95A1; font-weight: 500; font-size: 0.72rem;}
.goal .bar {height: 6px; border-radius: 3px; background: rgba(255,255,255,0.07); margin-top: 10px; overflow: hidden;}
.goal .bar span {display: block; height: 100%; border-radius: 3px;}

/* ---------- receipt ---------- */
.receipt {position: relative; background: #ECE8DC; color: #1C1C1C; max-width: 470px; margin: 18px auto 30px;
          padding: 30px 26px 26px; font-family: 'IBM Plex Mono', 'Courier New', ui-monospace, monospace;
          box-shadow: 0 10px 34px rgba(0,0,0,0.40);}
.receipt::before, .receipt::after {content: ""; position: absolute; left: 0; width: 100%; height: 8px;
          background-repeat: repeat-x; background-size: 16px 16px;}
.receipt::after {bottom: -8px; background-position: left bottom;
          background-image: linear-gradient(-135deg, #ECE8DC 8px, transparent 0),
                            linear-gradient(135deg, #ECE8DC 8px, transparent 0);}
.receipt::before {top: -8px; background-position: left top;
          background-image: linear-gradient(45deg, #ECE8DC 8px, transparent 0),
                            linear-gradient(-45deg, #ECE8DC 8px, transparent 0);}
.rc-head {text-align: center;}
.rc-brand {font-size: 1.05rem; font-weight: 600; letter-spacing: 0.16em; text-transform: uppercase;}
.rc-sub {font-size: 0.72rem; color: #6B685E; margin-top: 5px;}
.rc-hr {border-top: 1px dashed #9A9588; margin: 16px 0;}
.rc-sec {font-weight: 600; letter-spacing: 0.18em; font-size: 0.78rem; margin: 6px 0 9px;}
.rc-row {display: flex; align-items: baseline; font-size: 0.82rem; padding: 2px 0;}
.rc-row .n {white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 55%;}
.rc-row .d {flex: 1; border-bottom: 1px dotted #A9A497; margin: 0 6px; transform: translateY(-3px); min-width: 14px;}
.rc-row .p {color: #8A867B; font-size: 0.7rem; margin-right: 8px;}
.rc-row .a {font-weight: 500; white-space: nowrap;}
.rc-row.child {padding-left: 16px; font-size: 0.76rem; color: #4A4840;}
.rc-row.total {font-weight: 600; border-top: 1px solid #1C1C1C; margin-top: 8px; padding-top: 6px;}
.rc-empty {color: #8A867B; font-size: 0.76rem; text-align: center; padding: 6px 0;}
.rc-net {display: flex; justify-content: space-between; align-items: baseline; font-size: 1.1rem; font-weight: 600;
         border-top: 1px solid #1C1C1C; border-bottom: 3px double #1C1C1C; padding: 10px 0; margin: 16px 0 8px;}
.rc-net.pos {color: #25603A;} .rc-net.neg {color: #8E3636;}
.rc-meta {display: flex; justify-content: space-between; font-size: 0.74rem; color: #5B584F;}
.rc-qr {width: 176px; margin: 22px auto 6px;}
.rc-qr svg {display: block; width: 100%; height: auto;}
.rc-qr-cap {text-align: center; font-size: 0.62rem; letter-spacing: 0.16em; color: #6B685E;}

/* ---------- accessibility ---------- */
button:focus-visible, [role="button"]:focus-visible, input:focus-visible, textarea:focus-visible,
select:focus-visible, [data-testid="stExpander"] summary:focus-visible {
    outline: 2px solid #7A9CC6; outline-offset: 2px;}
"""
CSS = _BASE_CSS


# ============================================================ helpers
def money(x, sym=CUR, dec=2, sign=False) -> str:
    sym = sym + (" " if len(sym) > 1 else "")
    x = round(float(x), dec)
    x = 0.0 if x == 0 else x          # no "-€0.00" from float noise
    pre = "-" if x < 0 else ("+" if sign and x > 0 else "")
    return f"{pre}{sym}{abs(x):,.{dec}f}"


def fmt(x, kind="money", sign=False) -> str:
    """Display helper: n/a for missing values, ∞ for infinite runway."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    if isinstance(x, float) and math.isinf(x):
        return "∞"
    if kind == "money":
        return money(x, sign=sign)
    if kind == "pct":
        return f"{x * 100:+.2f}%" if sign else f"{x * 100:.2f}%"
    if kind == "months":
        return f"{x:,.2f} months"
    return f"{x:,.2f}"


def _rgba(hex_color: str, a: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{a})"


def color_map(labels):
    return {l: PALETTE[i % len(PALETTE)] for i, l in enumerate(labels)}


def esc(s) -> str:
    return html.escape(str(s)).replace("$", "&#36;")


def md(s: str, target=None):
    """Render raw HTML safely ($ would otherwise trigger LaTeX rendering)."""
    (target or st).markdown(s.replace("$", "&#36;"), unsafe_allow_html=True)


def inject_css():
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def keep_state(*keys):
    """Keep widget values when navigating between pages."""
    store = st.session_state.setdefault("_keep_state", {})
    for k in keys:
        if k in st.session_state:
            store[k] = st.session_state[k]
        elif k in store:
            st.session_state[k] = store[k]


def sidebar_privacy() -> bool:
    """Privacy toggle only (pages that do not use the shared date range)."""
    keep_state("hide", "rng")
    return st.toggle("Hide amounts (privacy)", key="hide")


def sidebar_common(all_days):
    """Privacy toggle + date range, shared by every page. Returns (hide, start, end)."""
    keep_state("hide", "rng")
    if "rng" not in st.session_state:
        st.session_state["rng"] = (all_days.min().date(), all_days.max().date())
    hide = st.toggle("Hide amounts (privacy)", key="hide")
    rng = st.date_input("Date range", key="rng")
    rng = tuple(rng) if isinstance(rng, (list, tuple)) else (rng,)
    if not rng:                      # range cleared: fall back to the whole history
        return hide, all_days.min().date(), None
    return hide, rng[0], (rng[1] if len(rng) == 2 else None)


GLOSSARY = {
    "Availability": "Money in bank, cash, card and asset accounts. It is the default base for the runway.",
    "Liquid funds": "Bank, cash and card accounts, plus the asset accounts you flagged as liquid. It excludes assets you did not flag, money parked in Invested buckets and money used to repay debts.",
    "Burn / median monthly spending": "The middle month of your monthly expenses. The runway divides by this, not by the average.",
    "Runway": "How many months you can pay for with the chosen money base, at the current (or planned) burn rate. Base ÷ burn.",
    "Cover": "Same idea as runway, but only for the emergency fund: liquid money at the end of the plan ÷ planned monthly spending.",
    "Baseline surplus": "Income minus expenses before you change anything in the plan, calculated from the chosen history period.",
    "Surplus": "Income minus expenses after your plan changes. It is annual in the budget table; divide by 12 for a monthly figure.",
    "Free cash": "The part of the surplus that is not assigned to any bucket. It stays liquid.",
    "Over-allocated": "The buckets ask for more than the surplus: the difference comes out of money you already have.",
    "Return %/yr": "The annual growth assumed for a bucket or investment. A forecast, not a guarantee.",
    "Volatility": "How bumpy the returns are. Higher volatility widens the range of outcomes and lowers the median slightly.",
    "Volatility drag": "The gap between the smooth projection and the median of the random simulations: equal losses hurt more than equal gains help.",
    "FI number": "Financial-independence number: annual spending ÷ withdrawal rate. With 4%, it is 25 × annual spending.",
    "Withdrawal rate": "How much of the pot you can spend each year in retirement. 4% is the classic rule of thumb.",
}


def glossary(label: str = "Understand the numbers — glossary"):
    """Expandable plain-language glossary for the terms used across the app."""
    with st.expander(label):
        for term, meaning in GLOSSARY.items():
            st.markdown(f"**{term}** — {meaning}")


def active_filters(chips=(), label: str = "Active filters"):
    """Small chip bar summarising the filters applied to the current view."""
    chips = [c for c in chips if c]
    if not chips:
        return
    body = "".join(f'<span class="chip">{esc(c)}</span>' for c in chips)
    md(f'<div class="sec">{esc(label)}</div><div>{body}</div>')


def formula_caption(text: str):
    """Show the arithmetic behind a number, e.g. '26.000 € ÷ 2.000 € = 13 mesi'."""
    st.caption(text)


def data_stamp(path: str) -> str:
    """Human-readable last-modified time of the read-only GnuCash database."""
    try:
        import datetime as _dt
        return _dt.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%d %b %Y %H:%M")
    except OSError:
        return "unknown"


def range_chip(start, end, all_days) -> str:
    end = end or all_days.max().date()
    return f"{start:%d %b %Y} → {end:%d %b %Y}"


def hero(title: str, subtitle: str, chips=()):
    ch = "".join(f'<span class="chip">{esc(c)}</span>' for c in chips)
    md(f'<div class="hero"><div class="hero-t">{esc(title)}</div>'
       f'<div class="hero-s">{esc(subtitle)}</div><div>{ch}</div></div>')


def section(title: str, note: str = ""):
    n = f"<small>{esc(note)}</small>" if note else ""
    md(f'<div class="sec">{esc(title)}{n}</div>')


def card(title: str):
    c = st.container(border=True)
    md(f'<div class="card-title">{esc(title)}</div>', c)
    return c


def print_button(label: str = "Print / save as PDF"):
    """A button that opens the browser print dialog for the whole page."""
    html = (
        "<style>body{margin:0}button{width:100%;padding:8px 12px;border-radius:8px;"
        "border:1px solid rgba(255,255,255,.18);background:#151B23;color:#E7EAEE;"
        "font:500 13px Inter,Arial,sans-serif;cursor:pointer}"
        "button:hover{border-color:#7A9CC6}</style>"
        f"<button onclick=\"window.parent.print()\">{label}</button>"
    )
    if hasattr(st, "iframe"):  # Streamlit >= 1.56
        st.iframe(html, height=44)
    else:  # Streamlit < 1.56: keep working until the dependency is raised
        import streamlit.components.v1 as components
        components.html(html, height=44)


def print_report(page_html: str, filename: str, title: str, hide: bool = False):
    """Print support: the A4 report is embedded in the page (hidden on screen, shown alone when you
    print) and offered as a self-contained download. Call it at the end of a page, in the main area."""
    import reports
    md(reports.embed(page_html))
    with st.sidebar:
        st.header("Export")
        print_button()
        st.download_button("Download report (.html)", b"" if hide else reports.document(title, page_html).encode("utf-8"),
                           file_name=filename, mime="text/html", disabled=hide,
                           help="A self-contained A4 report: open it anywhere and print it." if not hide else
                           "Disabled while privacy mode is on.")
        st.caption("Printing gives a clean A4 report of this page. Choose “Save as PDF” as the destination for a file.")


def currency_warning(currencies):
    """Amounts are added up as if they were one currency, so say so when the book has several."""
    if len(currencies) > 1:
        st.warning("This book has more than one currency (" + ", ".join(currencies)
                   + "). Amounts are summed as if they were one currency: totals, net worth and KPIs "
                   "are not converted.")


def private_note():
    st.info("Amounts hidden (privacy mode).")


# ============================================================ HTML components
def sparkline(values, color, w=120, h=34) -> str:
    vals = [float(v) for v in values if v == v and not math.isinf(v)]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    pts = [(i / (len(vals) - 1) * w, h - 4 - (v - lo) / span * (h - 8)) for i, v in enumerate(vals)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    gid = f"sg{zlib.crc32((color + line).encode()) % 10**8}"
    return (f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none"><defs>'
            f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{color}" stop-opacity="0.22"/>'
            f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></linearGradient></defs>'
            f'<polygon points="0,{h} {line} {w},{h}" fill="url(#{gid})"/>'
            f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="1.5" '
            f'stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>'
            f'</svg>')


def meter_html(frac, color, left="", right="") -> str:
    w = 0 if frac is None or (isinstance(frac, float) and math.isnan(frac)) \
        else min(max(frac, 0.0), 1.0) * 100
    return (f'<div class="meter"><div class="meter-bar"><span style="width:{w:.1f}%;'
            f'background:{color}"></span></div><div class="meter-lab">'
            f'<span>{esc(left)}</span><span>{esc(right)}</span></div></div>')


def tile(label, value, sub="", cls="", accent=C_NW, spark=None, extra="") -> str:
    sp = f'<div class="sp">{sparkline(spark, accent)}</div>' if spark is not None else ""
    return (f'<div class="kpi" style="--accent:{accent}"><div class="l">{esc(label)}</div>'
            f'<div class="v {cls}">{esc(value)}</div><div class="s">{esc(sub)}</div>{extra}{sp}</div>')


def tiles_html(tiles, cols=4, flat=False) -> str:
    return (f'<div class="kpis{" flat" if flat else ""}" style="--cols:{cols}">'
            f'{"".join(tiles)}</div>')


def hero_availability_html(availability, liquid, hide=False) -> str:
    val = MASK if hide else money(availability)
    split = ""
    if availability > 0:
        lf = min(max(liquid / availability, 0.0), 1.0)
        lt = MASK if hide else money(liquid)
        ot = MASK if hide else money(availability - liquid)
        split = (f'<div class="split"><span style="width:{lf * 100:.2f}%;background:{C_TEAL}"></span>'
                 f'<span style="width:{(1 - lf) * 100:.2f}%;background:{C_NW}"></span></div>'
                 f'<div class="split-leg"><span><i style="background:{C_TEAL}"></i>Liquid {lt} '
                 f'· {lf * 100:.2f}%</span><span><i style="background:{C_NW}"></i>Other {ot} '
                 f'· {(1 - lf) * 100:.2f}%</span></div>')
    return (f'<div class="hero-kpi"><div class="l">Availability</div><div class="big">{val}</div>'
            f'<div class="s">All bank, cash, asset &amp; card balances</div>{split}</div>')


runway_status = kpis.runway_status


def status_pill_html(status) -> str:
    if not status:
        return ""
    label, kind = status
    return f'<div class="pill-row"><span class="pill {kind}"><i></i>{esc(label)}</span></div>'


def vol_level(v):
    """(label, colour) for the volatility meter."""
    label, level = kpis.volatility_level(v)
    return label, STATUS_COLORS[level]


def account_list_html(balances: pd.DataFrame, currency_totals: pd.DataFrame, hide=False, height=H_ACC) -> str:
    pos = balances[balances["balance"] > 0]
    cmap = color_map(pos["account"])
    top = pos["balance"].max() if len(pos) else 1
    rows = []
    for _, r in balances.iterrows():
        name = str(r.account)
        closed = name.endswith(" (Closed)")
        if closed:
            name = name[: -len(" (Closed)")]
        col = cmap.get(r.account, "#4B5563")
        width = 0 if (hide or r.balance <= 0) else max(2, r.balance / top * 100)
        amt = MASK if hide else money(r.balance, r.symbol)
        neg = " neg" if (r.balance < 0 and not hide) else ""
        zero = " zero" if abs(r.balance) < 0.005 else ""
        badge = '<span class="badge">closed</span>' if closed else ""
        rows.append(
            f'<div class="acc{zero}"><span class="dot" style="background:{col}"></span>'
            f'<div class="main"><div class="name">{esc(name)}{badge}</div>'
            f'<div class="bar"><span style="width:{width:.1f}%;background:{col}"></span>'
            f'</div></div><div class="amt{neg}">{amt}</div></div>')
    foot = "".join(
        f'<div class="acc-total"><span class="t">Total ({esc(r.symbol)})</span>'
        f'<span class="v">{MASK if hide else money(r.balance, r.symbol)}</span></div>'
        for _, r in currency_totals.iterrows())
    return (f'<div class="acc-card" style="height:{height}px">'
            f'<div class="acc-wrap">{"".join(rows)}</div>'
            f'<div class="acc-foot">{foot}</div></div>')


def legend_html(df, label, value, height) -> str:
    total = df[value].sum()
    cmap = color_map(df[label])
    rows = "".join(
        f'<div class="lg"><span class="dot" style="background:{cmap[n]}"></span>'
        f'<span class="nm" title="{esc(n)}">{esc(n)}</span>'
        f'<span class="pc">{(v / total * 100 if total else 0):.2f}%</span>'
        f'<span class="am">{money(v)}</span></div>'
        for n, v in zip(df[label], df[value]))
    return (f'<div class="lg-wrap" style="min-height:{height}px;max-height:{height}px">'
            f'{rows}</div>')


def segments_html(items, money_values: bool = False) -> str:
    """Segmented bar + legend. items: (label, value, color). Counts by default, € if money_values."""
    total = sum(v for _, v, _ in items) or 1
    spans = "".join(f'<span style="width:{v / total * 100:.2f}%;background:{c}" '
                    f'title="{esc(l)}"></span>' for l, v, c in items if v > 0)
    leg = "".join(f'<div><i style="background:{c}"></i><span>{esc(l)}</span>'
                  f'<b>{money(v) if money_values else f"{v:,}"} <small style="color:#8B95A1;font-weight:500">'
                  f'{v / total * 100:.1f}%</small></b></div>' for l, v, c in items if v > 0)
    return f'<div class="segbar">{spans}</div><div class="seg-leg">{leg}</div>'


def rank_html(items, color=C_NW, total=None) -> str:
    """Ranked list with proportional bars. items: (name, count)."""
    if not items:
        return '<div style="color:#8B95A1;font-size:.85rem">Nothing to show yet.</div>'
    top = max(v for _, v in items) or 1
    rows = []
    for n, v in items:
        share = (f' <small style="color:#8B95A1;font-weight:500">{v / total * 100:.1f}%</small>'
                 if total else "")
        rows.append(
            f'<div class="acc"><span class="dot" style="background:{color}"></span>'
            f'<div class="main"><div class="name" title="{esc(n)}">{esc(n)}</div>'
            f'<div class="bar"><span style="width:{v / top * 100:.1f}%;background:{color}"></span></div></div>'
            f'<div class="amt">{v:,}{share}</div></div>')
    return "".join(rows)


def totals_bar_html(big_label, big_value, minis) -> str:
    mini = "".join(f'<div><span class="t">{esc(l)}</span><span class="v">{esc(v)}</span></div>'
                   for l, v in minis)
    return (f'<div class="totbar"><div class="big"><div class="t">{esc(big_label)}</div>'
            f'<div class="v">{esc(big_value)}</div></div><div class="mini">{mini}</div></div>')


def receipt_html(title, subtitle, res, hide=False, qr=None) -> str:
    def a(x):
        return MASK if hide else money(x)

    def row(name, amount, share, cls=""):
        p = f'<span class="p">{share:.1f}%</span>' if share is not None else ""
        return (f'<div class="rc-row {cls}"><span class="n" title="{esc(name)}">{esc(name)}</span>'
                f'<span class="d"></span>{p}<span class="a">{a(amount)}</span></div>')

    out = [f'<div class="rc-head"><div class="rc-brand">{esc(title)}</div>'
           f'<div class="rc-sub">{esc(subtitle)}</div></div><div class="rc-hr"></div>']
    for acct_type, label in (("EXPENSE", "EXPENSES"), ("INCOME", "INCOME")):
        sec = res[acct_type]
        out.append(f'<div class="rc-sec">{label}</div>')
        if not sec["items"]:
            out.append('<div class="rc-empty">— nothing in this selection —</div>')
        for it in sec["items"]:
            share = it["amount"] / sec["total"] * 100 if sec["total"] else 0.0
            out.append(row(it["name"], it["amount"], share))
            for cn, ca in it["children"]:
                out.append(row(cn, ca, ca / sec["total"] * 100 if sec["total"] else 0.0, "child"))
        out.append(row(f"TOTAL {label}", sec["total"], None, "total"))
        out.append('<div class="rc-hr"></div>')
    net = res["net"]
    cls = "" if hide else ("pos" if net >= 0 else "neg")
    out.append(f'<div class="rc-net {cls}"><span>NET CASH FLOW</span>'
               f'<span>{MASK if hide else money(net, sign=True)}</span></div>')
    out.append(f'<div class="rc-meta"><span>Savings rate</span><span>{fmt(res["rate"], "pct")}</span></div>')
    if qr:
        out.append(f'<div class="rc-qr">{qr}</div><div class="rc-qr-cap">SCAN FOR A TEXT SUMMARY</div>')
    return f'<div class="receipt">{"".join(out)}</div>'


def zone_color(v: float) -> str:
    for _, b, c in GAUGE_STEPS:
        if v < b:
            return c
    return GAUGE_STEPS[-1][2]


def gauge_svg(value: float, max_v: float = 24.0, uid: str = "g") -> str:
    """Thin semi-circular gauge: dim zones as the track, the filled part in the zone colours."""
    W, H, cx, cy, R, sw = 320, 188, 160, 158, 112, 10

    def pt(v, r):
        th = math.pi * (1 - min(max(v, 0.0), max_v) / max_v)
        return cx + r * math.cos(th), cy - r * math.sin(th)

    def arc(v0, v1, r):
        x0, y0 = pt(v0, r)
        x1, y1 = pt(v1, r)
        return f"M {x0:.2f} {y0:.2f} A {r} {r} 0 0 1 {x1:.2f} {y1:.2f}"

    val = min(max(value, 0.0), max_v)
    g = 0.18   # small gap between zones (in months)
    parts = []
    for a, b, c in GAUGE_STEPS:                                   # dim track
        parts.append(f'<path d="{arc(a + (g if a > 0 else 0.0), b - (g if b < max_v else 0.0), R)}" '
                     f'fill="none" stroke="{c}" stroke-opacity="0.22" stroke-width="{sw}"/>')
    for a, b, c in GAUGE_STEPS:                                   # filled part
        if val > a:
            parts.append(f'<path d="{arc(a + (g if a > 0 else 0.0), min(val, b - (g if b < max_v else 0.0)), R)}" '
                         f'fill="none" stroke="{c}" stroke-width="{sw}"/>')
    kx, ky = pt(val, R)
    parts.append(f'<circle cx="{kx:.2f}" cy="{ky:.2f}" r="7" fill="{TEXT}" stroke="{SURFACE}" stroke-width="3"/>')
    for v in (0, 6, 12, max_v):                                   # tick labels
        x, y = pt(v, R + 24)
        parts.append(f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle" font-size="11" '
                     f'font-weight="500" fill="{MUTED}" font-family="Inter,sans-serif">{v:g}</text>')
    parts.append(f'<text x="{cx}" y="{cy - 22}" text-anchor="middle" font-size="38" font-weight="600" '
                 f'fill="{TEXT}" font-family="Inter,sans-serif" letter-spacing="-1">{value:,.2f}</text>')
    parts.append(f'<text x="{cx}" y="{cy - 2}" text-anchor="middle" font-size="10" font-weight="600" '
                 f'fill="{MUTED}" font-family="Inter,sans-serif" letter-spacing="2.4">MONTHS</text>')
    return (f'<div class="gauge-wrap"><svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">'
            f'{"".join(parts)}</svg></div>')


# ============================================================ charts
def _layout(fig, height=H_LINE, legend_top=False, unified=True):
    fig.update_layout(
        template="plotly_dark", paper_bgcolor=TRANSP, plot_bgcolor=TRANSP,
        font=dict(family=FONT, color=TEXT, size=12), height=height,
        margin=dict(l=8, r=8, t=44 if legend_top else 8, b=8),
        hovermode="x unified" if unified else "closest",
        hoverlabel=dict(bgcolor=HOVER_BG, bordercolor="rgba(255,255,255,0.16)",
                        font=dict(family=FONT, color=TEXT, size=12)))
    if legend_top:
        fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left",
                                      x=0, bgcolor=TRANSP, font=dict(size=12, color=MUTED)))
    fig.update_xaxes(showgrid=False, zeroline=False, showline=True, linecolor=GRID,
                     tickfont=dict(color=MUTED, size=11), title_font=dict(color=MUTED, size=11))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickformat="~s", tickprefix=CUR,
                     tickfont=dict(color=MUTED, size=11), title_font=dict(color=MUTED, size=11),
                     automargin=True)
    return fig


def _time_axis(fig, periods, step: str):
    fmt_ = {"Day": "%d %b %Y", "Week": "%d %b %Y", "Month": "%B %Y", "Year": "%Y"}[step]
    ticks = pd.Series(periods).drop_duplicates().sort_values()
    if len(ticks) <= 14:  # only show periods that actually have data
        fig.update_xaxes(tickvals=list(ticks), tickformat=fmt_)
    else:
        fig.update_xaxes(tickformat=fmt_)
    fig.update_xaxes(hoverformat=fmt_)


def balances_over_time(df: pd.DataFrame, step: str, height=H_LINE):
    fig = go.Figure()
    few = df["Period"].nunique() <= 24
    order = (df.sort_values("Period").groupby("Account")["Balance"].last()
             .sort_values(ascending=False).index)
    for i, acc in enumerate(order):
        d = df[df["Account"] == acc].sort_values("Period")
        col = PALETTE[i % len(PALETTE)]
        fig.add_trace(go.Scatter(
            x=d["Period"], y=d["Balance"], name=acc, mode="lines+markers" if few else "lines",
            line=dict(color=col, width=2), marker=dict(size=5, color=col),
            fill="tozeroy", fillcolor=_rgba(col, 0.06),
            hovertemplate=f"<b>{CUR}%{{y:,.2f}}</b>"))
    _layout(fig, height, legend_top=True)
    fig.update_yaxes(rangemode="tozero")
    _time_axis(fig, df["Period"], step)
    return fig


def net_worth(df: pd.DataFrame, step: str, reserve=0.0, height=H_LINE):
    few = df["Period"].nunique() <= 24
    fig = go.Figure(go.Scatter(
        x=df["Period"], y=df["Balance"], mode="lines+markers" if few else "lines",
        name="Net worth", line=dict(color=C_NW, width=2.2), marker=dict(size=6, color=C_NW),
        fill="tozeroy", fillcolor=_rgba(C_NW, 0.12),
        hovertemplate=f"<b>{CUR}%{{y:,.2f}}</b>"))
    if reserve and reserve > 0:
        fig.add_hline(y=reserve, line_dash="dot", line_color=MUTED, line_width=1.2,
                      annotation_text="Reserve", annotation_position="top right",
                      annotation_font=dict(color=MUTED, size=11))
    _layout(fig, height)
    fig.update_layout(showlegend=False)
    fig.update_yaxes(rangemode="tozero")
    _time_axis(fig, df["Period"], step)
    return fig


def income_vs_expense(df: pd.DataFrame, step: str, net: pd.DataFrame = None, height=H_LINE):
    g = df.groupby(["Period", "Type"], as_index=False)["Amount"].sum()
    fig = go.Figure()
    for acct_type, col in (("Income", C_INCOME), ("Expense", C_EXPENSE)):
        d = g[g["Type"] == acct_type]
        fig.add_trace(go.Bar(x=d["Period"], y=d["Amount"], name=acct_type, marker_color=col,
                             opacity=0.88, hovertemplate=f"<b>{CUR}%{{y:,.2f}}</b>"))
    periods = g["Period"]
    if net is not None and len(net):
        fig.add_trace(go.Scatter(
            x=net["Period"], y=net["Net"], name="Net", mode="lines+markers",
            line=dict(color=TEXT, width=1.8), marker=dict(size=6, color=TEXT),
            hovertemplate=f"<b>{CUR}%{{y:,.2f}}</b>"))
        periods = pd.concat([periods, net["Period"]])
    _layout(fig, height, legend_top=True)
    fig.update_layout(barmode="group", bargap=0.4, bargroupgap=0.08)
    _time_axis(fig, periods, step)
    return fig


def donut_figure(df, label, value, height=H_DONUT):
    total = df[value].sum()
    cmap = color_map(df[label])
    fig = go.Figure(go.Pie(
        labels=df[label], values=df[value], hole=0.74, sort=False, direction="clockwise",
        textinfo="none", showlegend=False,
        marker=dict(colors=[cmap[n] for n in df[label]], line=dict(color=SURFACE, width=2)),
        title=dict(text=(f"<b>{money(total)}</b><br><span style='font-size:12px;"
                         f"color:{MUTED}'>Total</span>"),
                   position="middle center", font=dict(size=21, color=TEXT)),
        hovertemplate=("<b>%{label}</b><br>" + CUR + "%{value:,.2f}"
                       "<br><span style='color:" + MUTED + "'>%{percent:.2%}</span><extra></extra>"),
        hoverlabel=dict(bgcolor=HOVER_BG, bordercolor="rgba(255,255,255,0.16)",
                        font=dict(family=FONT, color=TEXT, size=12))))
    _layout(fig, height, unified=False)
    return fig


def donut_block(df, label, value, key, hide=False, height=H_DONUT):
    """Donut (left, large) + HTML legend (right), vertically centered."""
    if hide:
        private_note()
        return
    if df.empty:
        st.caption("No data in the selected period.")
        return
    c1, c2 = st.columns([6, 5], vertical_alignment="center")
    c1.plotly_chart(donut_figure(df, label, value, height), key=key,
                    config={"displayModeBar": False})
    md(legend_html(df, label, value, height), c2)


def monthly_band_chart(series: pd.Series, median: float, std: float, color: str, height=300):
    """Monthly bars with the median line and a ±1σ band."""
    x = series.index.to_timestamp()
    fig = go.Figure(go.Bar(x=x, y=series.values, marker_color=color, opacity=0.85,
                           name="Monthly", hovertemplate=f"<b>{CUR}%{{y:,.2f}}</b>"))
    ok_m = median is not None and not math.isnan(median)
    if ok_m and std is not None and not math.isnan(std):
        fig.add_hrect(y0=max(0.0, median - std), y1=median + std,
                      fillcolor=_rgba(color, 0.10), line_width=0, layer="below",
                      annotation_text="±1σ", annotation_position="top left",
                      annotation_font=dict(color=MUTED, size=11))
    if ok_m:
        fig.add_hline(y=median, line_dash="dot", line_color=MUTED, line_width=1.2,
                      annotation_text=f"Median {money(median)}", annotation_position="top right",
                      annotation_font=dict(color=TEXT, size=11))
    _layout(fig, height)
    fig.update_layout(showlegend=False, bargap=0.4)
    _time_axis(fig, pd.Series(x), "Month")
    return fig


def count_bars(x, y, color=C_NW, height=300, highlight=False, dates=False):
    """Vertical count bars; optionally emphasise the maximum."""
    cols = [color] * len(y)
    if highlight and len(y):
        m = max(y)
        cols = [color if v == m else _rgba(color, 0.40) for v in y]
    fig = go.Figure(go.Bar(x=x, y=y, marker_color=cols,
                           hovertemplate="<b>%{y:,} transactions</b>"))
    _layout(fig, height)
    fig.update_layout(showlegend=False, bargap=0.35)
    fig.update_yaxes(tickprefix="")
    if dates:
        _time_axis(fig, pd.Series(x), "Month")
    return fig


def activity_heatmap(counts: pd.Series, height=235):
    """Calendar of transactions per day (last 53 weeks)."""
    end = pd.Timestamp(counts.index.max()).normalize()
    start = end - pd.Timedelta(weeks=52)
    start = start - pd.Timedelta(days=start.weekday())
    n_weeks = (end - start).days // 7 + 1
    z = [[None] * n_weeks for _ in range(7)]
    cd = [[""] * n_weeks for _ in range(7)]
    for d in pd.date_range(start, end):
        w, r = (d - start).days // 7, d.weekday()
        z[r][w] = int(counts.get(d, 0))
        cd[r][w] = d.strftime("%a %d %b %Y")
    x = [start + pd.Timedelta(weeks=i) for i in range(n_weeks)]
    fig = go.Figure(go.Heatmap(
        z=z, x=x, y=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], customdata=cd,
        xgap=3, ygap=3, showscale=False, hoverongaps=False, zmin=0,
        colorscale=[[0, "rgba(255,255,255,0.05)"], [0.001, "#24384B"],
                    [0.5, "#4F7396"], [1, "#9DBBD9"]],
        hovertemplate="<b>%{customdata}</b><br>%{z} transaction(s)<extra></extra>"))
    _layout(fig, height, unified=False)
    fig.update_layout(showlegend=False)
    fig.update_yaxes(autorange="reversed", tickprefix="", tickformat="", gridcolor=TRANSP,
                     showline=False)
    fig.update_xaxes(tickformat="%b", dtick="M1", showline=False)
    return fig


def wallet_bricks(labels, counts, shares, height=380):
    """Treemap of 'bricks': one per wallet; together they make up all transactions."""
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(labels))]
    fig = go.Figure(go.Treemap(
        labels=labels, parents=[""] * len(labels), values=counts,
        text=[f"{c:,} · {s * 100:.1f}%" for c, s in zip(counts, shares)],
        customdata=[f"{s * 100:.2f}% of all transactions" for s in shares],
        texttemplate="<b>%{label}</b><br>%{text}",
        hovertemplate="<b>%{label}</b><br>%{value:,} transactions<br>%{customdata}<extra></extra>",
        marker=dict(colors=colors, line=dict(color=SURFACE, width=3)),
        textfont=dict(size=13, color="#0D1117", family=FONT),
        textposition="middle center", pathbar=dict(visible=False), sort=True))
    fig.update_layout(paper_bgcolor=TRANSP, plot_bgcolor=TRANSP, height=height,
                      font=dict(family=FONT, color=TEXT), margin=dict(l=0, r=0, t=0, b=0),
                      hoverlabel=dict(bgcolor=HOVER_BG, bordercolor="rgba(255,255,255,0.16)",
                                      font=dict(family=FONT, color=TEXT, size=12)))
    return fig



# ============================================================ printing, tables, QR
def table_html(df: pd.DataFrame, num_cols=(), max_rows: int = 1500, cls: str = "dtable",
               total_last: bool = False, signed_cols=()) -> str:
    """Static on-screen table. Numeric cells get 2 decimals; strings are shown as they are
    (format them first for €)."""
    cols = list(df.columns)
    head = "".join(f'<th class="{"num" if c in num_cols else ""}">{esc(c)}</th>' for c in cols)
    shown = df.head(max_rows)
    rows = []
    for i, rec in enumerate(shown.itertuples(index=False)):
        tds = []
        for c, v in zip(cols, rec):
            isnum = c in num_cols
            numeric = isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v))
            txt = f"{v:,.2f}" if isnum and numeric else ("" if v is None else str(v))
            klass = ["num"] if isnum else []
            if c in signed_cols and numeric and v != 0:
                klass.append("pos" if v > 0 else "neg")
            tds.append(f'<td class="{" ".join(klass)}">{esc(txt)}</td>')
        tr = ' class="tot"' if total_last and i == len(shown) - 1 else ""
        rows.append(f"<tr{tr}>" + "".join(tds) + "</tr>")
    note = (f'<div class="rp-note" style="color:#8B95A1;font-size:.78rem;margin-top:6px">Showing the first {max_rows:,} of {len(df):,} rows.</div>'
            if len(df) > max_rows else "")
    table = f'<table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table>{note}'
    return f'<div class="dwrap">{table}</div>' if cls == "dtable" else table


def qr_svg(text: str, dark: str = "#1C1C1C") -> str:
    import qr
    return qr.svg(text, dark=dark)



# ============================================================ planning & simulation
def goal_rows_html(rows, hide=False) -> str:
    """Goals with progress. rows: dict(name, target, saved, required, sub, note, color)."""
    out = []
    for g in rows:
        pct = min(max(g["saved"] / g["target"], 0.0), 1.0) * 100 if g["target"] > 0 else 0.0
        if g.get("done"):
            req = g["note"]
        elif g.get("due"):
            req = MASK if hide else f"{money(max(g['target'] - g['saved'], 0.0))} now"
        else:
            req = MASK if hide else f"{money(g['required'])} / month"
        small = "" if g.get("done") else f"<small>{esc(g['note'])}</small>"
        amounts = MASK if hide else f"{money(g['saved'])} of {money(g['target'])}"
        out.append(f'<div class="goal"><div class="goal-top"><div><div class="goal-name">{esc(g["name"])}</div>'
                   f'<div class="goal-sub">{esc(g["sub"])} · {amounts} · {pct:.0f}%</div></div>'
                   f'<div class="goal-req">{esc(req)}{small}</div></div>'
                   f'<div class="bar"><span style="width:{pct:.1f}%;background:{g.get("color", C_NW)}"></span></div></div>')
    return "".join(out) or '<div style="color:#8B95A1;font-size:.85rem">No goals yet: add one in the table.</div>'


def bridge_chart(steps, height=340):
    """From baseline surplus to planned surplus. steps: (label, value, 'absolute'|'relative'|'total')."""
    labels, bases, heights, colors, texts = [], [], [], [], []
    run = 0.0
    for label, v, kind in steps:
        if kind == "relative":
            bases.append(run)
            heights.append(v)
            colors.append(C_INCOME if v >= 0 else C_EXPENSE)
            run += v
        else:
            bases.append(0.0)
            heights.append(v)
            colors.append(C_NW)
            run = v
        labels.append(label)
        texts.append(money(v, sign=(kind == "relative")))
    fig = go.Figure(go.Bar(x=labels, y=heights, base=bases, marker_color=colors, text=texts,
                           textposition="outside", cliponaxis=False, textfont=dict(color=TEXT, size=12),
                           hovertemplate="<b>%{x}</b><br>" + CUR + "%{y:,.2f}<extra></extra>"))
    _layout(fig, height, unified=False)
    fig.update_layout(showlegend=False, bargap=0.45, margin=dict(l=8, r=8, t=26, b=8))
    fig.update_xaxes(tickfont=dict(color=TEXT, size=12))
    fig.add_hline(y=0, line_color=GRID, line_width=1)
    return fig


def category_compare(df: pd.DataFrame, color: str, height=None):
    """Baseline vs plan per category (df: name, annual, planned)."""
    d = df.assign(_m=df[["annual", "planned"]].max(axis=1)).sort_values("_m", ascending=False).head(12)
    fig = go.Figure([
        go.Bar(y=d["name"], x=d["annual"], orientation="h", name="Baseline",
               marker_color=_rgba(MUTED, 0.50), hovertemplate=f"<b>{CUR}%{{x:,.2f}}</b>"),
        go.Bar(y=d["name"], x=d["planned"], orientation="h", name="Plan", marker_color=color,
               hovertemplate=f"<b>{CUR}%{{x:,.2f}}</b>")])
    _layout(fig, height or max(220, 44 * len(d) + 70), legend_top=True)
    fig.update_layout(barmode="group", bargap=0.35, bargroupgap=0.08)
    fig.update_yaxes(autorange="reversed", tickprefix="", tickformat="", gridcolor=TRANSP,
                     tickfont=dict(color=TEXT, size=12))
    fig.update_xaxes(showgrid=True, gridcolor=GRID, showline=False, tickprefix=CUR, tickformat="~s")
    return fig


def month_chart(monthly: pd.DataFrame, cash, height=H_LINE):
    """Planned income and expenses per month (bars) and the cash balance (line, right axis)."""
    x = monthly.index.to_timestamp()
    fig = go.Figure([
        go.Bar(x=x, y=monthly["income"], name="Income", marker_color=C_INCOME, opacity=0.88,
               hovertemplate=f"<b>{CUR}%{{y:,.2f}}</b>"),
        go.Bar(x=x, y=monthly["expense"], name="Expenses", marker_color=C_EXPENSE, opacity=0.88,
               hovertemplate=f"<b>{CUR}%{{y:,.2f}}</b>"),
        go.Scatter(x=x, y=cash, name="Cash after allocation", yaxis="y2", mode="lines+markers",
                   line=dict(color=TEXT, width=1.8), marker=dict(size=5, color=TEXT),
                   hovertemplate=f"<b>{CUR}%{{y:,.2f}}</b>")])
    _layout(fig, height, legend_top=True)
    fig.update_layout(barmode="group", bargap=0.4, bargroupgap=0.08,
                      yaxis2=dict(overlaying="y", side="right", showgrid=False, zeroline=False,
                                  tickprefix=CUR, tickformat="~s", tickfont=dict(color=MUTED, size=11)))
    _time_axis(fig, pd.Series(x), "Month")
    return fig


def fan_chart(mc: dict, target=None, height=430):
    """Wealth projection: 10-90% and 25-75% bands, median, and the no-volatility plan."""
    n = len(mc["p50"])
    x = ["Now"] + [f"Year {i}" for i in range(1, n)]
    hover = "<b>%{fullData.name}</b><br>%{x}<br>" + CUR + "%{y:,.0f}<extra></extra>"
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=mc["p90"], name="Optimistic (P90)", mode="lines", line=dict(width=0),
                             hovertemplate=hover))
    fig.add_trace(go.Scatter(x=x, y=mc["p10"], name="Cautious (P10)", mode="lines", line=dict(width=0),
                             fill="tonexty", fillcolor=_rgba(C_NW, 0.10), hovertemplate=hover))
    fig.add_trace(go.Scatter(x=x, y=mc["p75"], name="P75", mode="lines", line=dict(width=0),
                             hovertemplate=hover))
    fig.add_trace(go.Scatter(x=x, y=mc["p25"], name="P25", mode="lines", line=dict(width=0),
                             fill="tonexty", fillcolor=_rgba(C_NW, 0.18), hovertemplate=hover))
    fig.add_trace(go.Scatter(x=x, y=mc["p50"], name="Median", mode="lines", line=dict(color=C_NW, width=2.4),
                             hovertemplate=hover))
    fig.add_trace(go.Scatter(x=x, y=mc["det"], name="Plan without volatility", mode="lines",
                             line=dict(color=TEXT, width=1.4, dash="dot"), hovertemplate=hover))
    fig.add_trace(go.Scatter(x=x, y=mc["contributed"], name="Contributed", mode="lines",
                             line=dict(color=MUTED, width=1.2, dash="dash"), hovertemplate=hover))
    if target is not None and np.ndim(target) == 1:        # one value per year (inflation-adjusted)
        fig.add_trace(go.Scatter(x=x, y=list(target), name="Target", mode="lines",
                                 line=dict(color=C_GOLD, width=1.4, dash="dot"), hovertemplate=hover))
    elif target:
        fig.add_hline(y=target, line_dash="dot", line_color=C_GOLD, line_width=1.4,
                      annotation_text="Target", annotation_position="top left",
                      annotation_font=dict(color=C_GOLD, size=11))
    _layout(fig, height, legend_top=True)
    fig.update_xaxes(title_text="Year", hoverformat=None)
    return fig


SCENARIO_COLORS = (C_NW, C_GOLD, C_EXPENSE, C_PURPLE, C_TEAL)
_HOVER = "<b>%{fullData.name}</b><br>" + CUR + "%{y:,.0f}<extra></extra>"


def _axis_labels(labels, length):
    return list(labels) if labels is not None else list(range(length))


def scenario_lines_chart(lines: dict, labels=None, height=360):
    """Deterministic comparison: one availability line per plan, no randomness."""
    fig = go.Figure()
    for i, (name, values) in enumerate(lines.items()):
        color = SCENARIO_COLORS[i % len(SCENARIO_COLORS)]
        x = _axis_labels(labels, len(values))
        fig.add_trace(go.Scatter(x=x, y=values, name=name, mode="lines",
                                 line=dict(color=color, width=2.6), hovertemplate=_HOVER))
    _layout(fig, height, legend_top=True)
    fig.update_xaxes(title_text="Month", hoverformat=None)
    fig.update_yaxes(title_text="Availability", tickprefix=CUR, hoverformat=",.2f")
    return fig


def scenario_fan_chart(fan: dict, name: str, labels=None, height=430):
    """Volatility of ONE plan with a logical hover: no shocks, median, then the percentile range."""
    fig = go.Figure()
    x = _axis_labels(labels, len(fan["p50"]))
    xr = x + x[::-1]
    for low, high, alpha in (("p10", "p90", 0.10), ("p25", "p75", 0.18)):
        fig.add_trace(go.Scatter(
            x=xr, y=list(fan[high]) + list(fan[low])[::-1], mode="lines",
            line=dict(width=0), fill="toself", fillcolor=_rgba(C_NW, alpha),
            hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(x=x, y=fan[high], mode="lines",
                                 line=dict(color=_rgba(C_NW, 0.45), width=1.2),
                                 hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=x, y=fan["det"], name="No volatility", mode="lines",
                             line=dict(color=TEXT, width=1.4, dash="dot"), hovertemplate=_HOVER))
    fig.add_trace(go.Scatter(x=x, y=fan["p50"], name="Median", mode="lines",
                             line=dict(color=C_NW, width=2.6), hovertemplate=_HOVER))
    for low, high, label in (("p25", "p75", "75th percentile"),
                             ("p10", "p90", "90th percentile")):
        fig.add_trace(go.Scatter(
            x=x, y=fan[high], name=label, mode="lines",
            line=dict(color="rgba(0,0,0,0)", width=1), showlegend=False,
            customdata=np.column_stack([fan[low], fan[high]]),
            hovertemplate=(f"<b>{label}</b><br>"
                           f"min {CUR}%{{customdata[0]:,.0f}} · "
                           f"max {CUR}%{{customdata[1]:,.0f}}<extra></extra>")))
    _layout(fig, height, legend_top=True)
    fig.update_xaxes(title_text="Month", hoverformat=None)
    fig.update_yaxes(title_text="Availability", tickprefix=CUR, hoverformat=",.2f")
    return fig


def cash_paths_chart(paths, height=340):
    """Cash balance over time. paths: (name, array, color, dash)."""
    fig = go.Figure()
    for name, arr, color, dash in paths:
        fig.add_trace(go.Scatter(x=list(range(len(arr))), y=arr, name=name, mode="lines",
                                 line=dict(color=color, width=2.2, dash=dash),
                                 hovertemplate=f"<b>{CUR}%{{y:,.2f}}</b>"))
    fig.add_hline(y=0, line_color=C_EXPENSE, line_width=1.2, line_dash="dot",
                  annotation_text="Out of cash", annotation_position="bottom right",
                  annotation_font=dict(color=C_EXPENSE, size=11))
    _layout(fig, height, legend_top=True)
    fig.update_xaxes(title_text="Months from now", hoverformat="d")
    return fig


def runway_sensitivity(base: float, burn: float, height=320):
    """Runway (months) if monthly spending were 50%-200% of today's burn."""
    mult = [0.5 + 0.05 * i for i in range(31)]
    xs = [m * 100 for m in mult]
    ys = [max(0.0, base / (burn * m)) for m in mult]
    top = max(max(ys) * 1.08, 26.0)
    fig = go.Figure()
    for (a, b, c), hi in zip(GAUGE_STEPS, (6, 12, top)):
        fig.add_hrect(y0=a, y1=hi, fillcolor=_rgba(c, 0.10), line_width=0, layer="below")
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name="Runway", line=dict(color=C_NW, width=2.6),
                             hovertemplate="<b>%{y:,.2f} months</b>"))
    fig.add_trace(go.Scatter(x=[100], y=[base / burn], mode="markers", name="Today",
                             marker=dict(size=11, color=TEXT, line=dict(color=C_NW, width=3)),
                             hovertemplate="<b>%{y:,.2f} months</b>"))
    _layout(fig, height)
    fig.update_layout(showlegend=False)
    fig.update_yaxes(tickprefix="", ticksuffix=" mo", tickformat=".0f", range=[0, top], title_text="Runway")
    fig.update_xaxes(ticksuffix="%", hoverformat=".0f", title_text="Monthly spending vs. today")
    return fig
