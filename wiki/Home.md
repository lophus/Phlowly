# Home

Home is the landing page of the dashboard. It answers one question quickly:

> **What is happening in my book right now?**

## What you see

### Welcome hero

- total transactions in the book;
- first and last transaction date;
- number of accounts, including closed ones.

### Navigation

Six cards open the other pages:

- Dashboard
- KPIs
- Transactions
- Receipt
- Plan
- Simulator

### Your book in numbers

Tiles about volume and rhythm:

- transactions, splits, splits per transaction;
- expense, income and transfer transactions;
- accounts active and closed;
- active days and percentage of days with activity;
- average transactions per month;
- longest streak of active days;
- busiest day and busiest weekday;
- reconciled percentage;
- distinct descriptions, tags and tagged percentage.

### Activity

- a daily activity heatmap for the last 12 months;
- transactions per month;
- transactions by weekday.

### Distribution

- transactions by wallet (bricks and ranking);
- transaction mix: expenses, income, transfers, mixed, opening/equity;
- accounts by type;
- most frequent descriptions;
- tags.

### Data quality

Read-only checks at the bottom of the page:

- **Unbalanced transactions**: transactions whose splits do not sum to zero;
- **Uncategorised splits**: splits with an unknown account type;
- **Large amounts**: splits above the 99th percentile;
- **Currencies**: how many currencies are present.

Each tab shows a table and a **Download CSV** button.

### Glossary

The **Understand the numbers — glossary** expander explains every term used in Phlowly:
runway, cover, baseline surplus, availability, liquid funds, burn rate, volatility and more.

## Tips

- Add `#tags` to a transaction's description, notes or split memo in GnuCash. They appear on Home and on the Receipt page.
- If your book uses more than one currency, Home warns you because amounts are summed as if they were one currency.
- The database is opened read-only; the page validates it before rendering.