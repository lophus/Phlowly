"""Accounting and planning invariants. Run from the project folder:

    python -m unittest discover -s tests -v

Pure modules are always tested. The database tests need Streamlit (db.py uses its cache) and skip
themselves without it. They check the app against an independent SQL computation in whole cents.
"""
import math
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
import uuid

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
SAMPLE = os.path.join(BASE, "sample.gnucash")

import kpis  # noqa: E402
import logic  # noqa: E402
import planning as P  # noqa: E402
import qr  # noqa: E402
import sim  # noqa: E402

try:
    import streamlit  # noqa: F401
    HAVE_ST = True
except ImportError:
    HAVE_ST = False


def deltas_frame(rows):
    df = pd.DataFrame(rows, columns=["guid", "account", "acct_type", "currency", "day", "delta"])
    df["closed"], df["day"] = 0, pd.to_datetime(df["day"])
    return df


# ------------------------------------------------------------------ logic
class Balances(unittest.TestCase):
    def setUp(self):
        self.d = deltas_frame([
            ("a", "Bank", "BANK", "EUR", "2024-01-01", 1000.0), ("a", "Bank", "BANK", "EUR", "2024-02-01", -250.5),
            ("a", "Bank", "BANK", "EUR", "2999-01-01", 5000.0),          # post-dated: not in today's balance
            ("c", "Card", "CREDIT", "EUR", "2024-02-02", -100.0),
            ("l", "Loan", "LIABILITY", "EUR", "2024-01-01", -400.0),
            ("r", "Owed to me", "RECEIVABLE", "EUR", "2024-01-05", 50.0),
        ])

    def test_future_entries_are_not_in_current_balances(self):
        b = logic.account_balances(self.d)
        self.assertAlmostEqual(b.set_index("account").loc["Bank", "balance"], 749.5)
        self.assertAlmostEqual(logic.position(self.d)["availability"], 649.5)

    def test_net_worth_counts_debts_and_receivables(self):
        self.assertAlmostEqual(logic.net_worth_now(self.d), 749.5 - 100 - 400 + 50)

    def test_liquid_funds_need_the_flag_for_assets(self):
        d = deltas_frame([("a", "Bank", "BANK", "EUR", "2024-01-01", 100.0),
                          ("h", "Gold", "ASSET", "EUR", "2024-01-01", 900.0)])
        b = logic.account_balances(d)
        self.assertEqual(logic.liquid_funds(b), 100.0)
        self.assertEqual(logic.liquid_funds(b, ["Gold"]), 1000.0)

    def test_no_float_noise(self):
        d = deltas_frame([("a", "Bank", "BANK", "EUR", "2024-01-01", 0.1), ("a", "Bank", "BANK", "EUR", "2024-01-02", 0.2),
                          ("a", "Bank", "BANK", "EUR", "2024-01-03", -0.3)])
        self.assertEqual(logic.account_balances(d)["balance"].iloc[0], 0.0)


class Monthly(unittest.TestCase):
    def test_future_and_current_months(self):
        rows = [("2026-09-10", "EXPENSE", "Food", "Food", 100.0), ("2026-10-10", "EXPENSE", "Food", "Food", 200.0),
                ("2026-10-11", "INCOME", "Pay", "Pay", -500.0), ("2026-11-02", "EXPENSE", "Food", "Food", 10.0),
                ("2027-03-01", "INCOME", "Pay", "Pay", -999.0)]
        f = pd.DataFrame(rows, columns=["day", "acct_type", "macro", "exact", "value"])
        f["day"] = pd.to_datetime(f["day"])
        now = "2026-11-21"
        m = logic.monthly_series(f, now=now)
        self.assertEqual(str(m.index.max()), "2026-11")            # the post-dated month is ignored
        self.assertEqual(m["income"].sum(), 500.0)                  # income is positive
        m2 = logic.monthly_series(f, exclude_current=True, now=now)
        self.assertEqual(str(m2.index.max()), "2026-10")
        self.assertEqual(m2["expense"].tolist(), [100.0, 200.0])


class Money(unittest.TestCase):
    def test_short_names_are_unique(self):
        n = logic.short_names(["A:Cash", "B:Cash", "A:Bank"])
        self.assertEqual(len(set(n.values())), 3)
        self.assertEqual(n["A:Bank"], "Bank")


# ------------------------------------------------------------------ kpis
class Kpis(unittest.TestCase):
    def test_runway_and_rates(self):
        m = pd.DataFrame({"income": [1000.0] * 4, "expense": [500.0] * 4})
        k = kpis.compute(m, 6000.0, 3000.0, 6000.0)
        self.assertAlmostEqual(k["runway"], 12.0)
        self.assertAlmostEqual(k["savings_rate"], 0.5)
        self.assertAlmostEqual(k["liquidity_pct"], 0.5)

    def test_no_burn_is_infinite_and_negative_balance_is_zero(self):
        self.assertTrue(math.isinf(kpis._runway(1000, 0)))
        self.assertEqual(kpis._runway(-50, 100), 0.0)

    def test_status_bands(self):
        self.assertEqual(kpis.runway_status(5.99)[0], "Critical")
        self.assertEqual(kpis.runway_status(6)[0], "Caution")
        self.assertEqual(kpis.runway_status(12)[0], "Healthy")


# ------------------------------------------------------------------ simulation
class Sim(unittest.TestCase):
    def test_required_monthly_reaches_the_target(self):
        for ret in (0.0, 3.0, -2.0):
            need = sim.required_monthly(10_000, 1_000, 24, ret)
            self.assertAlmostEqual(sim.fv(1_000, need, ret, 24), 10_000, places=6)

    def test_months_to_target_matches_required_monthly(self):
        need = sim.required_monthly(5_000, 0, 20, 0.0)
        self.assertEqual(sim.months_to_target(5_000, 0, need, 0.0), 20.0)

    def test_inflation_makes_independence_later(self):
        flat = sim.years_to_target(500_000, 50_000, 20_000, 5.0)
        infl = sim.years_to_target(500_000, 50_000, 20_000, 5.0, 0.0, 3.0)
        self.assertGreater(infl, flat)

    def test_monte_carlo_mean_matches_deterministic(self):
        mc = sim.monte_carlo(10_000, 1_000, 0, 5.0, 15.0, 20, n=20000)
        self.assertAlmostEqual(mc["final"].mean() / mc["det"][-1], 1.0, delta=0.02)
        self.assertLess(mc["p50"][-1], mc["det"][-1])               # volatility drag

    def test_real_money_is_smaller_and_contributions_deflated(self):
        nom = sim.monte_carlo(1_000, 100, 0, 4.0, 0.0, 10, 2.0, False, n=10)
        real = sim.monte_carlo(1_000, 100, 0, 4.0, 0.0, 10, 2.0, True, n=10)
        self.assertLess(real["det"][-1], nom["det"][-1])
        self.assertLess(real["contributed"][-1], nom["contributed"][-1])

    def test_cash_lasts(self):
        p = sim.cash_path(1_000, 24, 0, 100)
        self.assertAlmostEqual(sim.cash_lasts(p), 10.0)
        self.assertTrue(math.isinf(sim.cash_lasts(sim.cash_path(1_000, 24, 100, 100))))


# ------------------------------------------------------------------ planning
def make_base(months=12, income=3000.0, expense=2000.0):
    idx = pd.period_range("2025-01", periods=months, freq="M")
    tab = pd.DataFrame({"acct_type": ["INCOME", "EXPENSE"], "key": ["INCOME|Pay", "EXPENSE|Life"],
                        "name": ["Pay", "Life"], "group": ["Pay", "Life"],
                        "monthly": [income, expense], "annual": [income * 12, expense * 12]})
    return {"table": tab, "monthly": pd.DataFrame({"income": income, "expense": expense}, index=idx), "months": idx}


POS = {"availability": 20_000.0, "liquid": 15_000.0, "net_worth": 50_000.0, "runway_basis": "Availability"}


def plan(alloc, **kw):
    p = P.default_params("2027-01")
    p["alloc"] = alloc
    p.update(kw)
    base = make_base()
    return P.evaluate(p, base, POS), base


def bucket(kind, value, ret=0.0, mode="%", current=0.0, name=None):
    return {"name": name or kind, "kind": kind, "mode": mode, "value": value, "ret": ret, "current": current}


class Planning(unittest.TestCase):
    def test_bridge_adds_up(self):
        p = P.default_params("2027-01")
        p["levers"] = {"income_pct": 5.0, "expense_pct": -3.0}
        p["oneoffs"] = [{"name": "x", "type": "Expense", "amount": 700.0, "when": P.EVERY},
                        {"name": "y", "type": "Income", "amount": 900.0, "when": "Mar 2027"}]
        b = P.budget(p, make_base())
        steps = b["bridge"]
        self.assertAlmostEqual(sum(v for _, v, k in steps[:-1]), steps[-1][1])
        self.assertAlmostEqual(b["monthly"]["net"].sum(), b["totals"]["surplus"])

    def test_paths_end_on_the_year_end_figures(self):
        ev, _ = plan([bucket("Cash", 20, 2.0), bucket("Invested", 40, 6.0), bucket("Debt", 10, 4.0)])
        al = ev["allocation"]
        self.assertAlmostEqual(al["cash_path"][-1], al["liquid_end"])
        self.assertAlmostEqual(al["availability_path"][-1], al["availability_end"])

    def test_cash_bucket_stays_liquid(self):
        ev, _ = plan([bucket("Cash", 100)])
        al, s = ev["allocation"], ev["budget"]["totals"]["surplus"]
        self.assertAlmostEqual(al["liquid_end"], POS["liquid"] + s)
        self.assertAlmostEqual(al["net_worth_end"], POS["net_worth"] + s)

    def test_invested_leaves_liquid_but_not_availability(self):
        ev, _ = plan([bucket("Invested", 50, 5.0)])
        al, s = ev["allocation"], ev["budget"]["totals"]["surplus"]
        self.assertLess(al["liquid_end"], POS["liquid"] + s)
        self.assertAlmostEqual(al["availability_end"], POS["availability"] + s + al["growth"])

    def test_debt_repayment_leaves_cash_but_net_worth_only_gains_the_interest(self):
        ev, _ = plan([bucket("Debt", 50, 0.0)])
        al, s = ev["allocation"], ev["budget"]["totals"]["surplus"]
        self.assertAlmostEqual(al["debt_paid"], s * 0.5)
        self.assertAlmostEqual(al["liquid_end"], POS["liquid"] + s * 0.5)
        self.assertAlmostEqual(al["availability_end"], POS["availability"] + s * 0.5)
        self.assertAlmostEqual(al["net_worth_end"], POS["net_worth"] + s)     # 0% loan: no interest saved

    def test_debt_ignores_already_there(self):
        a, _ = plan([bucket("Debt", 50, 4.0, current=9_999.0)])
        b, _ = plan([bucket("Debt", 50, 4.0, current=0.0)])
        self.assertAlmostEqual(a["allocation"]["net_worth_end"], b["allocation"]["net_worth_end"])

    def test_deficit_is_not_called_over_allocation(self):
        p = P.default_params("2027-01")
        p["levers"] = {"income_pct": -50.0, "expense_pct": 0.0}
        p["alloc"] = [bucket("Invested", 50)]
        base = make_base()
        bud = P.budget(p, base)
        self.assertLess(bud["totals"]["surplus"], 0)
        al = P.allocation(bud, p["alloc"], POS)
        self.assertFalse(al["over"])
        self.assertEqual(al["total"], 0.0)

    def test_fixed_amounts_above_the_surplus_are_over_allocated(self):
        ev, _ = plan([bucket("Invested", 5_000, mode="€/mo")])
        self.assertTrue(ev["allocation"]["over"])

    def test_fan_median_follows_the_plan(self):
        _, base = plan([bucket("Cash", 50)])
        p = P.default_params("2027-01")
        p["alloc"] = [bucket("Invested", 50, 5.0), bucket("Debt", 10, 3.0)]
        ev = P.evaluate(p, base, POS)
        fan = P.scenario_fan(p, base, POS, n=100)
        self.assertAlmostEqual(fan["det"][-1], ev["allocation"]["availability_end"])
        self.assertEqual(fan["det"][0], POS["availability"])

    def test_seeded_fan_is_repeatable(self):
        _, base = plan([bucket("Cash", 50)])
        p = P.default_params("2027-01")
        base["monthly"]["expense"] += np.arange(12) * 50
        a, b = P.scenario_fan(p, base, POS, n=50, seed=3), P.scenario_fan(p, base, POS, n=50, seed=3)
        np.testing.assert_array_equal(a["p50"], b["p50"])

    def test_baseline_months_skip_current_and_future(self):
        f = pd.DataFrame({"day": pd.to_datetime(["2026-08-03", "2026-10-03", "2026-11-03", "2027-02-01"])})
        m = P.base_months(f, "All history", True, now="2026-11-21")
        self.assertEqual((str(m[0]), str(m[-1])), ("2026-08", "2026-10"))
        m = P.base_months(f, "All history", False, now="2026-11-21")
        self.assertEqual(str(m[-1]), "2026-11")


# ------------------------------------------------------------------ QR
class Qr(unittest.TestCase):
    def test_size_and_finder_pattern(self):
        m = qr.matrix("CASH FLOW | 2024")
        self.assertEqual(len(m), 25)                                 # version 2: version 1 holds 14 bytes at level M
        self.assertTrue(all(m[0][:7]) and all(m[6][:7]))
        self.assertEqual(len(qr.matrix("x" * 300)), len(qr.matrix("y" * 300)))


# ------------------------------------------------------------------ database (needs streamlit)
def add_tx(path, day, parts, currency="EUR"):
    """Insert a transaction; parts = [(account name, cents)] and must sum to zero."""
    con = sqlite3.connect(path)
    cur = con.cursor()
    cur_guid = cur.execute("select guid from commodities where mnemonic=?", (currency,)).fetchone()[0]
    tx = uuid.uuid4().hex
    cur.execute("insert into transactions(guid,currency_guid,num,post_date,enter_date,description) values(?,?,?,?,?,?)",
                (tx, cur_guid, "", day, day, "test"))
    for name, cents in parts:
        acc = cur.execute("select guid from accounts where name=?", (name,)).fetchone()[0]
        cur.execute("insert into splits(guid,tx_guid,account_guid,memo,action,reconcile_state,value_num,value_denom,"
                    "quantity_num,quantity_denom) values(?,?,?,?,?,?,?,100,?,100)",
                    (uuid.uuid4().hex, tx, acc, "", "", "n", cents, cents))
    con.commit()
    con.close()


@unittest.skipUnless(HAVE_ST and os.path.exists(SAMPLE), "needs streamlit and the sample book")
class Database(unittest.TestCase):
    def setUp(self):                      # every test works on its own copy of the book
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "my book (copy).gnucash")      # spaces on purpose
        shutil.copy(SAMPLE, self.path)
        import db
        self.db = db
        db.DB_PATH = self.path
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def clear(self):
        import streamlit as st
        st.cache_data.clear()

    def sql(self, q):
        con = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        try:
            return con.execute(q).fetchone()[0]
        finally:
            con.close()

    def test_totals_match_independent_sql_in_cents(self):
        self.clear()
        deltas, flows, _ = self.db.load_all()
        cents = self.sql("select sum(s.value_num) from splits s join accounts a on a.guid=s.account_guid "
                         "where a.account_type in ('BANK','CASH','ASSET','CREDIT')")
        self.assertAlmostEqual(logic.position(deltas)["availability"], cents / 100, places=2)
        inc = self.sql("select -sum(s.value_num) from splits s join accounts a on a.guid=s.account_guid where a.account_type='INCOME'")
        exp = self.sql("select sum(s.value_num) from splits s join accounts a on a.guid=s.account_guid where a.account_type='EXPENSE'")
        m = logic.monthly_series(flows, now="2999-01-01")
        self.assertAlmostEqual(m["income"].sum(), inc / 100, places=2)
        self.assertAlmostEqual(m["expense"].sum(), exp / 100, places=2)

    def test_every_transaction_balances_and_net_worth_equals_minus_the_rest(self):
        self.clear()
        tx = self.db.transactions()
        self.assertTrue((tx.groupby("tx_guid")["value"].sum().abs() < 0.005).all())
        deltas, _, _ = self.db.load_all()
        outside = tx[~tx["is_wallet"]]["value"].sum()
        self.assertAlmostEqual(logic.net_worth_now(deltas, "2999-01-01"), -outside, places=2)

    def test_primary_account_counts_each_transaction_once(self):
        tx = self.db.transactions()
        acc = tx[tx["acct_type"].isin(logic.ACCOUNT_TYPES)]["tx_guid"].nunique()
        self.assertEqual(int(tx["is_primary"].sum()), acc)

    def test_receivable_future_entry_and_foreign_currency(self):
        add_tx(self.path, "2024-05-05", [("Rimborsi da ricevere", 5000), ("Supporto familiare", -5000)])   # money owed to you
        add_tx(self.path, "2999-01-01", [("Conto principale", 100000), ("Supporto familiare", -100000)])   # post-dated
        self.clear()
        deltas, flows, _ = self.db.load_all()
        base = 9908.02
        self.assertAlmostEqual(logic.position(deltas)["availability"], base)             # future entry ignored
        self.assertAlmostEqual(logic.net_worth_now(deltas), base + 50.0)                   # receivable counted
        self.assertAlmostEqual(logic.net_worth_now(deltas, "2999-12-31"), base + 50.0 + 1000.0)

    def test_unreadable_files_get_a_clear_message(self):
        bad = os.path.join(self.tmp, "x.gnucash")
        with open(bad, "wb") as fh:
            fh.write(b"<?xml version='1.0'?>")
        old, self.db.DB_PATH = self.db.DB_PATH, bad
        try:
            self.assertIn("not a SQLite", self.db.check_file())
            self.db.DB_PATH = os.path.join(self.tmp, "missing.gnucash")
            self.assertIn("not found", self.db.check_file())
        finally:
            self.db.DB_PATH = old


if __name__ == "__main__":
    unittest.main()
