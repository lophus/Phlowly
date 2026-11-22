"""Non-monetary statistics about the book (counts and distributions)."""
import pandas as pd

import logic

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
ASSET_TYPES = logic.BS_TYPES   # wallets only


def _longest_streak(days: pd.Series) -> int:
    o = sorted(set(days.dt.normalize().map(pd.Timestamp.toordinal)))
    best = cur = 1 if o else 0
    for a, b in zip(o, o[1:]):
        cur = cur + 1 if b == a + 1 else 1
        best = max(best, cur)
    return best


def overview(tx: pd.DataFrame, balances: pd.DataFrame) -> dict:
    txs = tx.drop_duplicates("tx_guid")
    days = txs["day"]
    first, last = days.min(), days.max()
    span = (last - first).days + 1
    per_day = days.dt.normalize().value_counts()
    per_month = days.dt.to_period("M").value_counts().sort_index()
    per_month = per_month.reindex(pd.period_range(per_month.index.min(),
                                                  per_month.index.max(), freq="M"), fill_value=0)
    wd = days.dt.weekday.value_counts().reindex(range(7), fill_value=0)
    # "accounts" = the real ones (cash, bank, assets, cards): exactly the rows of the Dashboard
    # balances list, so both pages always agree. "Closed" = hidden in GnuCash.
    real = balances
    kinds = txs["tx_kind"].value_counts()
    tag_counts = txs["tx_tag_list"].explode().dropna().value_counts()
    rec = tx["rec"].value_counts()
    descs = txs["description"].str.strip()
    return {
        "n_tx": len(txs), "n_splits": len(tx), "splits_per_tx": len(tx) / max(len(txs), 1),
        "first": first, "last": last, "span_days": span,
        "active_days": int(days.dt.normalize().nunique()),
        "active_pct": days.dt.normalize().nunique() / span,
        "avg_per_month": len(txs) / max(span / 30.4375, 1.0),
        "longest_streak": _longest_streak(days),
        "n_accounts": len(real), "n_hidden": int((real["closed"] == 1).sum()),
        "n_active": int((real["closed"] != 1).sum()),
                "n_expense_tx": int(kinds.get("Expense", 0)), "n_income_tx": int(kinds.get("Income", 0)),
        "n_transfer_tx": int(kinds.get("Transfer", 0)), "n_mixed_tx": int(kinds.get("Mixed", 0)),
        "n_equity_tx": int(kinds.get("Equity", 0)),
        "busiest_weekday": WEEKDAYS[int(wd.idxmax())], "weekday_counts": wd,
        "busiest_day": per_day.idxmax(), "busiest_day_n": int(per_day.max()),
        "busiest_month": per_month.idxmax(), "busiest_month_n": int(per_month.max()),
        "per_month": per_month, "per_day": per_day,
        "reconciled_pct": rec.get("y", 0) / len(tx), "cleared_n": int(rec.get("c", 0)),
        "distinct_desc": int(descs[descs != ""].nunique()),
        "top_desc": descs[descs != ""].value_counts().head(8),
        "tag_counts": tag_counts, "n_tags": int(len(tag_counts)),
        "tagged_pct": txs["tx_tag_list"].map(len).gt(0).mean(),
        "acc_by_type": real.groupby("acct_type").size().sort_values(ascending=False),
        "split_tx": int((tx.groupby("tx_guid").size() > 2).sum()),
    }


def tx_by_wallet(tx: pd.DataFrame, acc: pd.DataFrame) -> pd.DataFrame:
    """Transactions per account (cash, bank, assets, cards). Each transaction is counted once,
    under its primary account, so the counts add up to the total number of transactions."""
    n_total = tx["tx_guid"].nunique()
    counts = tx[tx["is_primary"]].groupby("account").size().rename("count")
    closed = dict(zip(acc["path"], acc["hidden"] == 1))
    out = counts.reset_index().sort_values("count", ascending=False)
    out["closed"] = out["account"].map(closed).fillna(False)
    rest = n_total - int(counts.sum())            # transactions touching none of those accounts
    if rest > 0:
        out = pd.concat([out, pd.DataFrame([{"account": "(other accounts)", "count": rest,
                                             "closed": False}])], ignore_index=True)
    out["share"] = out["count"] / max(n_total, 1)
    return out
