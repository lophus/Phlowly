"""Cash-flow receipt: build the line items and a plain-text version."""
import math
import re

import pandas as pd

import logic


def frame(tx: pd.DataFrame) -> pd.DataFrame:
    """All income/expense splits as (day, tx_guid, tag_list, acct_type, macro, exact, Amount).

    macro = 2nd level of the account path (or the account itself if top-level);
    exact = the account's own name. Amount is positive for normal flows."""
    f = tx[tx["acct_type"].isin(["INCOME", "EXPENSE"])]
    cols = ["day", "tx_guid", "tag_list", "acct_type", "macro", "exact", "Amount"]
    if f.empty:
        return pd.DataFrame(columns=cols)
    parts = f["account"].str.split(":")
    return pd.DataFrame({
        "day": f["day"].values,
        "tx_guid": f["tx_guid"].values,
        "tag_list": f["tag_list"].values,
        "acct_type": f["acct_type"].values,
        "macro": parts.apply(lambda p: p[1] if len(p) > 1 else p[0]).values,
        "exact": parts.str[-1].values,
        "Amount": f["value"].where(f["acct_type"] != "INCOME", -f["value"]).values,
    })


def select(fr: pd.DataFrame, start=None, end=None, tag=None) -> pd.DataFrame:
    f = logic._filter_range(fr, "day", start, end)
    if tag:
        t = tag.lower().lstrip("#")
        f = f[f["tag_list"].apply(lambda L: t in L)]
    return f


def parse_guids(text: str) -> frozenset[str]:
    """Exact transaction GUIDs from free text (spaces, commas, semicolons or newlines)."""
    if not text:
        return frozenset()
    return frozenset(
        token.strip().strip("\"'").lower()
        for token in re.split(r"[\s,;]+", text)
        if token.strip().strip("\"'")
    )


def exclude_guids(df: pd.DataFrame, guids) -> pd.DataFrame:
    """Drop rows whose transaction GUID is in ``guids`` (case-insensitive, exact match)."""
    wanted = {str(g).strip().lower() for g in guids if str(g).strip()}
    if df.empty or not wanted:
        return df
    return df[~df["tx_guid"].astype(str).str.lower().isin(wanted)]


def exclusion_options(all_frame: pd.DataFrame, detail: str):
    """Keys 'TIPO|macro' (and 'TIPO|macro|exact' in Detailed mode)."""
    if all_frame.empty:
        return []
    d = all_frame[["acct_type", "macro", "exact"]].drop_duplicates()
    opts = []
    for (acct_type, macro), g in d.groupby(["acct_type", "macro"]):
        opts.append(f"{acct_type}|{macro}")
        if detail == "Detailed":
            opts += [f"{acct_type}|{macro}|{e}" for e in sorted(g["exact"].unique()) if e != macro]
    labels = option_labels(opts)
    return sorted(opts, key=lambda k: labels[k])


def option_labels(options) -> dict:
    """key -> readable label, using plain names only. The macro is added in brackets
    only when a sub-category name would otherwise be ambiguous."""
    from collections import Counter
    base = {k: f"{'Expense' if k.split('|')[0] == 'EXPENSE' else 'Income'} · {k.split('|')[-1]}"
            for k in options}
    cnt = Counter(base.values())
    return {k: (b if cnt[b] == 1 else f"{b} ({k.split('|')[1]})") for k, b in base.items()}


def build(df: pd.DataFrame, detail: str, excluded=frozenset()) -> dict:
    res = {}
    for acct_type in ("EXPENSE", "INCOME"):
        d = df[df["acct_type"] == acct_type]
        items = []
        for macro, g in d.groupby("macro"):
            if f"{acct_type}|{macro}" in excluded:
                continue
            if detail == "Detailed":
                kids = g.groupby("exact")["Amount"].sum().to_dict()
                kids = {e: a for e, a in kids.items()
                        if f"{acct_type}|{macro}|{e}" not in excluded or e == macro}
                total = float(sum(kids.values()))
                children = [("(direct)" if e == macro else e, float(a)) for e, a in kids.items()
                            if abs(a) >= 0.005]
                if len(kids) == 1 and macro in kids:
                    children = []                      # leaf category: no sub-lines
                children.sort(key=lambda c: -c[1])
            else:
                total, children = float(g["Amount"].sum()), []
            if abs(total) >= 0.005:
                items.append({"name": macro, "amount": total, "children": children})
        items.sort(key=lambda i: -i["amount"])
        res[acct_type] = {"items": items, "total": float(sum(i["amount"] for i in items))}
    inc, exp = res["INCOME"]["total"], res["EXPENSE"]["total"]
    res["net"] = inc - exp
    res["rate"] = (inc - exp) / inc if inc > 0 else math.nan
    return res


def text(title: str, subtitle: str, res: dict, width: int = 46, cur: str = "€") -> str:
    def row(name, amount, indent=0):
        amt = f"{cur}{amount:,.2f}"
        name = (" " * indent + name)[: width - len(amt) - 3]
        return f"{name} {'.' * (width - len(name) - len(amt) - 2)} {amt}"

    L = [title.upper().center(width), subtitle.center(width), "=" * width]
    for acct_type, label in (("EXPENSE", "EXPENSES"), ("INCOME", "INCOME")):
        L += [label, "-" * width]
        for it in res[acct_type]["items"]:
            L.append(row(it["name"], it["amount"]))
            L += [row(n, a, 2) for n, a in it["children"]]
        L += ["-" * width, row(f"TOTAL {label}", res[acct_type]["total"]), ""]
    L += ["=" * width, row("NET CASH FLOW", res["net"])]
    if not math.isnan(res["rate"]):
        L.append(f"Savings rate: {res['rate'] * 100:.2f}%")
    L.append("THANK YOU - KEEP SAVING".center(width))
    return "\n".join(L)


def qr_text(title: str, period: str, res: dict, top: int = 3, top_income: int = 2,
            cur: str = "EUR") -> str:
    """Compact plain-text summary for the QR code. Any phone shows it when scanned, ready to
    copy, share or paste. Kept short on purpose: fewer bytes = a coarser, easier-to-scan code.
    ASCII currency code so every scanner reads it correctly."""
    def m(x):
        return f"{'-' if x < 0 else ''}{cur} {abs(x):,.2f}"

    L = [f"{title.upper()} | {period.replace('–', '-').replace('→', '-')}"]
    for acct_type, label, k in (("EXPENSE", "EXPENSES", top), ("INCOME", "INCOME", top_income)):
        sec = res[acct_type]
        L.append(f"{label} {m(sec['total'])}")
        L += [f" {it['name']} {it['amount']:,.2f}" for it in sec["items"][:k]]
        if len(sec["items"]) > k:
            L.append(f" +{len(sec['items']) - k} more")
    net = f"NET {m(res['net'])}"
    if not math.isnan(res["rate"]):
        net += f" | SAVINGS {res['rate'] * 100:.1f}%"
    L.append(net)
    return "\n".join(L)[:600]
