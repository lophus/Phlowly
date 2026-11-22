"""Pure pandas transformations (no Streamlit dependency).

Sign convention (GnuCash double entry): every transaction sums to zero. Wallet accounts keep
the raw value (money in +, money out -); income and expense accounts are flipped so income
is positive and expenses are positive amounts of spending. All money is in the book's currency.
"""
import re
from collections import Counter

import pandas as pd

# --- account type groups: the single source of truth (the SQL queries use them too) -----------
ACCOUNT_TYPES = ["BANK", "CASH", "ASSET", "CREDIT"]          # "availability": where your money sits
SECURITY_TYPES = ["STOCK", "MUTUAL"]
# Balance sheet ("wallet") accounts: everything that counts towards net worth.
# Income, expense and equity accounts are *not* wallets.
BS_TYPES = ACCOUNT_TYPES + ["LIABILITY", "MUTUAL", "STOCK", "RECEIVABLE", "PAYABLE"]
NET_WORTH_TYPES = BS_TYPES
LIQUID_TYPES = ["BANK", "CASH", "CREDIT"]                    # ASSET accounts count only if flagged
FLOW_TYPES = ["INCOME", "EXPENSE"]
SYMBOLS = {"EUR": "€", "USD": "$", "GBP": "£", "JPY": "¥"}

EPS = 0.005   # half a cent: below this an amount is zero


def today() -> pd.Timestamp:
    return pd.Timestamp.now().normalize()


def _period_start(day: pd.Series, step: str) -> pd.Series:
    d = pd.to_datetime(day)
    if step == "Day":
        return d.dt.normalize()
    if step == "Week":  # Monday of the week
        return (d - pd.to_timedelta(d.dt.weekday, unit="D")).dt.normalize()
    if step == "Year":
        return pd.to_datetime(d.dt.year.astype(str) + "-01-01")
    return d.dt.to_period("M").dt.to_timestamp()


def _filter_range(df, col, start, end):
    """Rows with start <= col <= end (either bound optional). Always returns an independent copy."""
    if start is not None:
        df = df[df[col] >= pd.Timestamp(start)]
    if end is not None:
        df = df[df[col] <= pd.Timestamp(end)]
    return df.copy()


def _until(df: pd.DataFrame, as_of=None) -> pd.DataFrame:
    """Rows dated up to `as_of` (default today): a balance 'now' never includes future entries."""
    cutoff = pd.Timestamp(as_of).normalize() if as_of is not None else today()
    return df[pd.to_datetime(df["day"]) <= cutoff]


# ---------------------------------------------------------------- balances and net worth
def account_balances(deltas: pd.DataFrame, as_of=None) -> pd.DataFrame:
    """Current balance of every cash, bank, asset and card account (entries after `as_of` excluded)."""
    d = _until(deltas[deltas["acct_type"].isin(ACCOUNT_TYPES)], as_of)
    out = d.groupby(["guid", "account", "currency"], as_index=False).agg(
        delta=("delta", "sum"), acct_type=("acct_type", "first"), closed=("closed", "max"))
    out["symbol"] = out["currency"].map(SYMBOLS).fillna(out["currency"])
    out["delta"] = out["delta"].round(6)
    return out.rename(columns={"delta": "balance"}).sort_values(
        ["balance", "account"], ascending=[False, True])


def currency_totals(balances: pd.DataFrame) -> pd.DataFrame:
    return balances.groupby("symbol", as_index=False)["balance"].sum()


def net_worth_now(deltas: pd.DataFrame, as_of=None) -> float:
    """Net worth today: every balance-sheet account, liabilities included, future entries excluded."""
    d = _until(deltas[deltas["acct_type"].isin(NET_WORTH_TYPES)], as_of)
    return round(float(d["delta"].sum()), 6)


def liquid_funds(balances: pd.DataFrame, liquid_assets=()) -> float:
    """Liquid money: bank, cash and card accounts, plus the asset accounts you flag as liquid."""
    is_liquid = (balances["acct_type"].isin(LIQUID_TYPES)
                 | (balances["acct_type"].eq("ASSET") & balances["account"].isin(list(liquid_assets))))
    return round(float(balances.loc[is_liquid, "balance"].sum()), 6)


def position(deltas: pd.DataFrame, liquid_assets=(), runway_basis: str = "Availability", as_of=None) -> dict:
    """Where you stand today: the starting point of the KPIs, the Plan and the Simulator."""
    balances = account_balances(deltas, as_of)
    return {"availability": round(float(balances["balance"].sum()), 6),
            "liquid": liquid_funds(balances, liquid_assets),
            "net_worth": net_worth_now(deltas, as_of),
            "runway_basis": runway_basis}


def account_balance_series(deltas, step, start=None, end=None) -> pd.DataFrame:
    """Cumulative balance per account (cash, bank, asset, card accounts)."""
    d = deltas[deltas["acct_type"].isin(ACCOUNT_TYPES)].copy()
    d["Period"] = _period_start(d["day"], step)
    piv = (d.pivot_table(index="Period", columns="account", values="delta",
                         aggfunc="sum", fill_value=0).sort_index().cumsum())
    out = piv.reset_index().melt(id_vars="Period", var_name="Account", value_name="Balance")
    return _filter_range(out, "Period", start, end)


def net_worth_series(deltas, step, start=None, end=None) -> pd.DataFrame:
    d = deltas[deltas["acct_type"].isin(NET_WORTH_TYPES)].copy()
    d["Period"] = _period_start(d["day"], step)
    s = d.groupby("Period")["delta"].sum().sort_index().cumsum()
    out = s.rename("Balance").reset_index()
    return _filter_range(out, "Period", start, end)


# ---------------------------------------------------------------- income and expenses
def _prepare_flows(flows, detail, start, end):
    f = flows.copy()
    f["day"] = pd.to_datetime(f["day"])
    f["Category"] = f["exact"] if detail == "Detailed" else f["macro"]
    f["Amount"] = f["value"].where(f["acct_type"] != "INCOME", -f["value"])   # income +, expense +
    return _filter_range(f, "day", start, end)


def category_totals(flows, acct_type, detail, start=None, end=None) -> pd.DataFrame:
    """Total per category; acct_type is 'EXPENSE' or 'INCOME'. Net refunds are netted off."""
    f = _prepare_flows(flows, detail, start, end)
    f = f[f["acct_type"] == acct_type]
    out = f.groupby("Category", as_index=False)["Amount"].sum()
    return out[out["Amount"] > 0].sort_values("Amount", ascending=False)


def flows_by_period(flows, step, detail, start=None, end=None) -> pd.DataFrame:
    """Income and expenses per period and category."""
    f = _prepare_flows(flows, detail, start, end)
    f["Period"] = _period_start(f["day"], step)
    f["Type"] = f["acct_type"].map({"INCOME": "Income", "EXPENSE": "Expense"})
    out = f.groupby(["Period", "Type", "Category"], as_index=False)["Amount"].sum()
    return out[out["Amount"] > 0].sort_values(["Period", "Type", "Amount"],
                                              ascending=[True, False, False])


def monthly_series(flows, start=None, end=None, exclude_current=False, now=None) -> pd.DataFrame:
    """Monthly income/expense totals, one row per month (gaps filled with 0).

    Months after the current one (post-dated entries) are never counted; the month in progress
    is incomplete and is dropped when `exclude_current` is set."""
    f = _prepare_flows(flows, "Macro", start, end)
    f["m"] = f["day"].dt.to_period("M")
    now_m = (pd.Timestamp(now) if now is not None else pd.Timestamp.now()).to_period("M")
    f = f[f["m"] <= now_m]
    if f.empty:
        return pd.DataFrame(columns=["income", "expense"], dtype=float)
    piv = f.pivot_table(index="m", columns="acct_type", values="Amount",
                        aggfunc="sum", fill_value=0.0)
    for c in ("INCOME", "EXPENSE"):
        if c not in piv.columns:
            piv[c] = 0.0
    piv = piv.rename(columns={"INCOME": "income", "EXPENSE": "expense"})[["income", "expense"]]
    piv = piv.reindex(pd.period_range(piv.index.min(), piv.index.max(), freq="M"), fill_value=0.0)
    if exclude_current:
        piv = piv[piv.index < now_m]
    return piv


def net_by_period(flows, step, start=None, end=None) -> pd.DataFrame:
    """Income minus expenses per period (no per-category filtering)."""
    f = _prepare_flows(flows, "Macro", start, end)
    if f.empty:
        return pd.DataFrame(columns=["Period", "Net"])
    f["Period"] = _period_start(f["day"], step)
    g = f.groupby(["Period", "acct_type"])["Amount"].sum().unstack(fill_value=0.0)
    for c in ("INCOME", "EXPENSE"):
        if c not in g.columns:
            g[c] = 0.0
    return (g["INCOME"] - g["EXPENSE"]).rename("Net").reset_index()


# ---------------------------------------------------------------- transactions page
def short_names(paths) -> dict:
    """Map account paths to plain names (no hierarchy).

    Only when two accounts share the same name is the parent added, e.g. 'Other (Housing)',
    so that lists stay unambiguous."""
    paths = list(dict.fromkeys(paths))
    leaf = {p: p.split(":")[-1] for p in paths}
    cnt = Counter(leaf.values())
    out = {}
    for p in paths:
        parts = p.split(":")
        out[p] = f"{leaf[p]} ({parts[-2]})" if cnt[leaf[p]] > 1 and len(parts) > 1 else leaf[p]
    cnt2 = Counter(out.values())
    return {p: (n if cnt2[n] == 1 else p.replace(":", " › ")) for p, n in out.items()}


def _join(s):
    return " · ".join(dict.fromkeys(s))


def _multi(value):
    """Accept a string (comma/semicolon/newline separated) or a sequence of values."""
    if value is None:
        return []
    if isinstance(value, str):
        return [v.strip() for v in re.split(r"[\n,;]+", value) if v.strip()]
    return [str(v).strip() for v in value if str(v).strip()]


def filter_splits(tx, start=None, end=None, search="", guid="", accounts=(), types=(),
                  tag=None) -> pd.DataFrame:
    """Row-level filters (date, text, GUID, accounts, types, tags).

    ``search``, ``guid`` and ``tag`` accept one value or several (comma-separated text or a
    list). Several values are combined with OR, so any match is enough."""
    f = _filter_range(tx, "day", start, end)
    searches = [v.lower() for v in _multi(search)]
    if searches:
        mask = pd.Series(False, index=f.index)
        for q in searches:
            mask |= (f["description"].str.lower().str.contains(q, regex=False)
                     | f["notes"].str.lower().str.contains(q, regex=False)
                     | f["memo"].str.lower().str.contains(q, regex=False)
                     | f["num"].str.lower().str.contains(q, regex=False)
                     | f["action"].str.lower().str.contains(q, regex=False))
        f = f[mask]
    guids = [v.lower() for v in _multi(guid)]
    if guids:
        mask = pd.Series(False, index=f.index)
        for g in guids:
            mask |= (f["tx_guid"].str.lower().str.contains(g, regex=False)
                     | f["split_guid"].str.lower().str.contains(g, regex=False))
        f = f[mask]
    if accounts:
        f = f[f["account"].isin(accounts)]
    if types:
        f = f[f["acct_type"].isin(types)]
    tags = [v.lower().lstrip("#") for v in _multi(tag)]
    if tags:
        mask = pd.Series(False, index=f.index)
        for t in tags:
            mask |= f["tag_list"].apply(lambda L: t in L)
        f = f[mask]
    return f


def build_view(tx: pd.DataFrame, f: pd.DataFrame, view: str, tag_active: bool = False) -> pd.DataFrame:
    """Build the table to show, following GnuCash's double-entry logic.

    Every transaction has two (or more) sides that sum to zero, so listing both sides and
    adding them up is meaningless. Each view therefore shows ONE side, with a sign that
    reflects what happens to your money:

    * Transactions: one row per transaction, Amount = effect on net worth
      (expense -, income +, transfer between your own accounts 0).
    * Wallets: splits on cash/bank/asset/card accounts as in a GnuCash register
      (deposit +, withdrawal -).
    * Categories: splits on income/expense accounts, Amount = -(raw value)
      so income is + and expenses are - .

    With a tag filter, a split transaction counts only the part that carries the tag: a tag
    written in the memo/action of one split must not tag the whole transaction.
    """
    names = short_names(tx["account"].unique())
    if view == "Wallets":
        d = f[f["is_wallet"]]
        out = d[["day", "description", "account", "acct_type", "notes", "tags", "tx_guid", "split_guid"]].copy()
        out["Amount"] = d["value"].values
        out["account"] = out["account"].map(names)
        return out
    if view == "Categories":
        d = f[f["acct_type"].isin(FLOW_TYPES)]
        out = d[["day", "description", "account", "acct_type", "notes", "tags", "tx_guid", "split_guid"]].copy()
        out["Amount"] = (-d["value"]).values
        out["account"] = out["account"].map(names)
        return out
    cols = ["tx_guid", "day", "description", "notes", "tags", "kind", "Amount", "Moved",
            "splits", "wallets", "categories"]
    if f.empty:
        empty = pd.DataFrame(columns=cols)
        empty["day"] = pd.to_datetime(empty["day"])
        for c in ("Amount", "Moved"):
            empty[c] = empty[c].astype(float)
        return empty
    d = tx[tx["tx_guid"].isin(f["tx_guid"].unique())]
    g = d.groupby("tx_guid", sort=False)
    out = g.agg(day=("day", "first"), description=("description", "first"),
                notes=("notes", "first"), tags=("tx_tags", "first"), kind=("tx_kind", "first"),
                Amount=("tx_effect", "first"), Moved=("tx_moved", "first"),
                splits=("split_guid", "count"))
    if tag_active:
        # only the tagged splits (f): income/expense side if tagged, else the wallet side
        pl = (-f.loc[f["acct_type"].isin(FLOW_TYPES), "value"]).groupby(f["tx_guid"]).sum()
        wl = f.loc[f["is_wallet"], "value"].groupby(f["tx_guid"]).sum()
        mv = f["value"].clip(lower=0).groupby(f["tx_guid"]).sum()
        amt = pl.reindex(out.index)
        out["Amount"] = amt.where(amt.notna(), wl.reindex(out.index)).fillna(0.0)
        out["Moved"] = mv.reindex(out.index).fillna(0.0)
    nm = d["account"].map(names)
    out["wallets"] = nm[d["is_wallet"]].groupby(d["tx_guid"]).agg(_join).reindex(out.index).fillna("")
    out["categories"] = nm[~d["is_wallet"]].groupby(d["tx_guid"]).agg(_join).reindex(out.index).fillna("")
    return out.reset_index()[cols]
