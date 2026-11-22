# Phlowly

**Phlowly** is a read-only Streamlit dashboard for your **GnuCash** book. It turns your ledger into a
clear, private, printable picture of where your money is, how long it lasts, and what
happens next.

> **Read-only by design.** The app opens the GnuCash SQLite database in `mode=ro`.
> It never writes, updates, or changes your schema. Your book stays exactly as it is.

## What it does

- Reads accounts, transactions, tags and balances directly from GnuCash.
- Shows net worth, cash flow, runway, volatility and savings rate.
- Builds a yearly budget from your history and allocates the surplus to buckets.
- Simulates long-term wealth with 1,000 random futures.
- Stress-tests your cash against income loss and spending shocks.
- Produces a printable A4 receipt/report for any page.
- Hides every amount in one click for screen-sharing or screenshots.

No data is uploaded anywhere. Everything runs locally.

## Pages

| Page | What you get |
|---|---|
| **Home** | Book overview: transactions, accounts, activity heatmap, weekday patterns, tags, wallet ranking, data-quality checks |
| **Dashboard** | Balances by account, net worth over time, income vs. expenses, category donuts |
| **KPIs** | Runway, worst-case runway, savings rate, volatility, liquidity; export a CSV summary |
| **Transactions** | Search and total any slice of the ledger, by date, text, GUID, tag, account, amount and direction |
| **Receipt** | Cash flow itemised like a receipt, with QR code, text export and print/PDF |
| **Plan** | A 12-month budget from your history, buckets for the surplus, emergency-fund target, scenario comparison |
| **Simulator** | Wealth projections, goals, stress tests and a financial-independence number |

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate          # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
GNUCASH_DB=/path/to/your.gnucash streamlit run Home.py
```

Then open `http://localhost:8501`.

### Requirements

- Python 3.10 or newer
- A GnuCash SQLite book (`.gnucash` file)
- `streamlit>=1.40,<2`, `pandas`, `plotly`

## Configuration

### Database location

Set `GNUCASH_DB` to the path of your GnuCash file. If it is not set, Phlowly looks for
`gnucash.sqlite` in the current directory.

### Settings

Persistent settings live in `settings.json` next to Phlowly:

- accounts counted as liquid;
- runway basis: **Availability** or **Liquid funds**;
- whether to exclude the current month from statistics;
- reserve line;
- savings goals used by the Simulator.

Saved planning scenarios live in `plans.json`.

## Privacy and export

- **Hide amounts (privacy)** masks every value on the page.
- Printing and downloading reports are disabled while privacy mode is on.
- Each page has a **Print / save as PDF** button and a **Download report (.html)** button.
- The Receipt page also offers **Download .txt** and a scannable QR summary.

## Read-only safety

The database is opened with:

```python
sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
```

There are no `INSERT`, `UPDATE`, `DELETE` or schema changes anywhere in the code.
The file hash of the GnuCash book is unchanged after running Phlowly.

## Documentation

The `wiki/` folder contains a friendly guide:

- [Home and navigation](wiki/Home.md)
- [Dashboard](wiki/Dashboard.md)
- [KPIs](wiki/KPIs.md)
- [Transactions](wiki/Transactions.md)
- [Receipt](wiki/Receipt.md)
- [Plan](wiki/Plan.md)
- [Simulator](wiki/Simulator.md)
- [Concepts](wiki/Concepts.md)
- [Recipes](wiki/Recipes.md)
- [Privacy and export](wiki/Privacy-and-export.md)
- [FAQ](wiki/FAQ.md)

## License

Personal project. Use it freely for your own GnuCash book.
