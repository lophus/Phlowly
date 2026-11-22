"""Read-only access to the GnuCash SQLite book. Every query returns a pandas DataFrame."""
import os
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

import logic

HERE = Path(__file__).resolve().parent
DB_PATH = os.environ.get("GNUCASH_DB") or str(HERE / "sample.gnucash")
SQLITE_MAGIC = b"SQLite format 3\x00"


def _sql_list(types) -> str:
    """Quote a list of account-type constants for an IN (...) clause (never user input)."""
    return ", ".join(f"'{t}'" for t in types)


def check_file() -> str | None:
    """Explain why the book cannot be opened, or return None if it looks fine."""
    path = Path(DB_PATH).expanduser()
    if not path.is_file():
        return f"File not found: {path}"
    with path.open("rb") as fh:
        header = fh.read(len(SQLITE_MAGIC))
    if header != SQLITE_MAGIC:
        return ("This is not a SQLite book (it looks like a compressed XML file). In GnuCash use "
                "File → Save As… and choose the “sqlite3” data format.")
    return None


def query(sql: str, params: tuple = ()) -> pd.DataFrame:
    # read only: never touches the GnuCash file. as_uri() escapes spaces and special characters.
    uri = Path(DB_PATH).expanduser().resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        return pd.read_sql(sql, con, params=params)
    finally:
        con.close()


# Accounts hang under the book root. GnuCash also stores a hidden "Template Root" for
# scheduled transactions: it is not part of the real chart of accounts.
TREE_CTE = """
WITH RECURSIVE tree(guid, path, account_type) AS (
  SELECT guid, '', account_type FROM accounts WHERE account_type = 'ROOT' AND name <> 'Template Root'
  UNION ALL
  SELECT a.guid,
         CASE WHEN t.path = '' THEN a.name ELSE t.path || ':' || a.name END,
         a.account_type
  FROM accounts a JOIN tree t ON a.parent_guid = t.guid
)
"""


@st.cache_data(ttl=300)
def balance_deltas() -> pd.DataFrame:
    """Daily changes of the balance-sheet accounts (liquidity, investments, debts, receivables).

    Ordinary accounts are measured in their own commodity (the split *quantity*); securities
    (stocks, funds) are measured by the *value* of their splits in the transaction currency,
    i.e. what you paid, since the book has no market price for every day."""
    df = query(TREE_CTE + f"""
        SELECT a.guid AS guid,
               tree.path AS path,
               COALESCE(a.hidden, 0) AS closed,
               a.account_type AS acct_type,
               COALESCE(CASE WHEN a.account_type IN ({_sql_list(logic.SECURITY_TYPES)})
                             THEN tc.mnemonic ELSE c.mnemonic END, c.mnemonic, '') AS currency,
               date(substr(t.post_date, 1, 10)) AS day,
               SUM(CASE WHEN a.account_type IN ({_sql_list(logic.SECURITY_TYPES)})
                        THEN CAST(s.value_num AS FLOAT) / s.value_denom
                        ELSE CAST(s.quantity_num AS FLOAT) / s.quantity_denom END) AS delta
        FROM accounts a
        JOIN tree                ON tree.guid = a.guid
        JOIN splits s            ON a.guid = s.account_guid
        JOIN transactions t      ON t.guid = s.tx_guid
        LEFT JOIN commodities c  ON c.guid = a.commodity_guid
        LEFT JOIN commodities tc ON tc.guid = t.currency_guid
        WHERE a.account_type IN ({_sql_list(logic.NET_WORTH_TYPES)})
        GROUP BY a.guid, tree.path, closed, a.account_type, currency, day
    """)
    # Display name: the plain account name, with the parent added only when two accounts share it.
    names = logic.short_names(df["path"])
    df["account"] = df["path"].map(names) + np.where(df["closed"] == 1, " (Closed)", "")
    df["day"] = pd.to_datetime(df["day"])
    df["delta"] = df["delta"].round(6)      # sums of floats: drop the 1e-12 noise
    return df


@st.cache_data(ttl=300)
def daily_flows() -> pd.DataFrame:
    """Income/expenses per day, with the macro category (level 2) and the exact account."""
    df = query(f"""
        WITH RECURSIVE AccountTree AS (
            SELECT guid, account_type, name AS macro_name, name AS exact_name, 1 AS level
            FROM accounts
            WHERE parent_guid IN (SELECT guid FROM accounts
                                  WHERE account_type = 'ROOT' AND name <> 'Template Root')
            UNION ALL
            SELECT a.guid, a.account_type,
                   CASE WHEN at.level = 1 THEN a.name ELSE at.macro_name END,
                   a.name, at.level + 1
            FROM accounts a JOIN AccountTree at ON a.parent_guid = at.guid
        )
        SELECT date(substr(t.post_date, 1, 10)) AS day,
               at.account_type AS acct_type,
               at.macro_name AS macro,
               at.exact_name AS exact,
               SUM(CAST(s.value_num AS FLOAT) / s.value_denom) AS value
        FROM AccountTree at
        JOIN splits s       ON at.guid = s.account_guid
        JOIN transactions t ON t.guid = s.tx_guid
        WHERE at.account_type IN ({_sql_list(logic.FLOW_TYPES)})
        GROUP BY day, acct_type, macro, exact
    """)
    df["day"] = pd.to_datetime(df["day"])
    df["value"] = df["value"].round(6)
    return df


def load_all():
    """Return (deltas, flows, all_days); stop the page with a clear message on error."""
    problem = check_file()
    if problem:
        st.error(f"Could not open the GnuCash book at '{DB_PATH}'.\n\n{problem}")
        st.stop()
    try:
        deltas = balance_deltas()
        flows = daily_flows()
    except Exception as e:  # noqa: BLE001
        st.error(f"Could not read the GnuCash database at '{DB_PATH}'.\n\n{e}")
        st.stop()
    if deltas.empty and flows.empty:
        st.warning("The database contains no transactions.")
        st.stop()
    all_days = pd.concat([deltas["day"], flows["day"]])
    return deltas, flows, all_days


def book_currencies(*frames: pd.DataFrame) -> list[str]:
    """Distinct currency codes found in the given frames (each needs a 'currency' column)."""
    found = set()
    for f in frames:
        found |= set(f["currency"].dropna()) - {""}
    return sorted(found)


@st.cache_data(ttl=300)
def transactions() -> pd.DataFrame:
    """One row per split, with its transaction, account path, notes and #tags."""
    df = query(TREE_CTE + """
        SELECT t.guid AS tx_guid, s.guid AS split_guid,
               date(substr(t.post_date, 1, 10)) AS day,
               COALESCE(t.num, '')         AS num,
               COALESCE(t.description, '') AS description,
               COALESCE((SELECT n.string_val FROM slots n
                         WHERE n.obj_guid = t.guid AND n.name = 'notes' LIMIT 1), '') AS notes,
               COALESCE(s.memo, '')        AS memo,
               COALESCE(s.action, '')      AS action,
               tree.path AS account, tree.account_type AS acct_type,
               COALESCE(c.mnemonic, '')    AS currency,
               CAST(s.value_num AS FLOAT) / s.value_denom AS value,
               s.reconcile_state AS rec
        FROM splits s
        JOIN transactions t ON t.guid = s.tx_guid
        JOIN tree           ON tree.guid = s.account_guid
        LEFT JOIN commodities c ON c.guid = t.currency_guid
    """)
    df["day"] = pd.to_datetime(df["day"])
    df["value"] = df["value"].round(6)
    # Where a #tag is written decides what it covers:
    #   description / notes / number -> the whole transaction (every split)
    #   memo / action of a split     -> that split only (e.g. one part of a split transaction)
    def _tags(s):
        found = s.str.findall(r"#(\w[\w\-]*)")
        return found.apply(lambda L: [t.lower() for t in L if not t.isdigit()])  # "#123" is a number

    tx_level = _tags(df["description"] + " " + df["notes"] + " " + df["num"])
    sp_level = _tags(df["memo"] + " " + df["action"])
    df["tag_list"] = [sorted(set(a) | set(b)) for a, b in zip(tx_level, sp_level)]
    df["tags"] = df["tag_list"].apply(lambda L: " ".join("#" + t for t in L))
    # all the tags present anywhere in the transaction (counts, pick-lists, display)
    ex = df["tag_list"].explode().dropna()
    per_tx = ex.groupby(df.loc[ex.index, "tx_guid"].to_numpy()).agg(lambda s: sorted(set(s)))
    df["tx_tag_list"] = df["tx_guid"].map(per_tx).apply(lambda v: v if isinstance(v, list) else [])
    df["tx_tags"] = df["tx_tag_list"].apply(lambda L: " ".join("#" + t for t in L))

    # ---- double-entry helpers (GnuCash logic) ----
    key = df["tx_guid"]
    is_bs = df["acct_type"].isin(logic.BS_TYPES)       # wallet side (cash, bank, assets, cards, debts)
    df["is_wallet"] = is_bs
    # cash-flow sign from the account's own perspective: wallets keep the raw value,
    # income/expense/equity are flipped (income +, expense -)
    df["signed"] = df["value"].where(is_bs, -df["value"])
    # effect of the whole transaction on net worth = sum of its wallet-side splits
    df["tx_effect"] = df["value"].where(is_bs, 0.0).groupby(key).transform("sum")
    df["tx_moved"] = df["value"].clip(lower=0).groupby(key).transform("sum")
    has_exp = (df["acct_type"] == "EXPENSE").groupby(key).transform("any")
    has_inc = (df["acct_type"] == "INCOME").groupby(key).transform("any")
    has_eq = (df["acct_type"] == "EQUITY").groupby(key).transform("any")
    df["tx_kind"] = np.select([has_exp & has_inc, has_exp, has_inc, has_eq],
                              ["Mixed", "Expense", "Income", "Equity"], default="Transfer")
    # primary account of each transaction: among the real accounts (cash, bank, assets, cards)
    # the split with the largest amount (ties -> the one money left from), so every
    # transaction is counted exactly once
    is_acc = df["acct_type"].isin(logic.ACCOUNT_TYPES)
    w = df[is_acc].assign(_a=df.loc[is_acc, "value"].abs()).sort_values(
        ["tx_guid", "_a", "value"], ascending=[True, False, True])
    df["is_primary"] = df["split_guid"].isin(set(w.drop_duplicates("tx_guid")["split_guid"]))
    return df


@st.cache_data(ttl=300)
def accounts_info() -> pd.DataFrame:
    return query(TREE_CTE + """
        SELECT tree.path AS path, tree.account_type AS acct_type,
               a.hidden AS hidden, a.placeholder AS placeholder,
               CASE WHEN EXISTS (SELECT 1 FROM accounts c WHERE c.parent_guid = a.guid)
                    THEN 0 ELSE 1 END AS is_leaf
        FROM tree JOIN accounts a ON a.guid = tree.guid
        WHERE tree.path <> ''
    """)


@st.cache_data(ttl=300)
def receipt_base() -> pd.DataFrame:
    import receipt  # local import: receipt depends only on logic
    return receipt.frame(transactions())
