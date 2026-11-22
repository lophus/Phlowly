# Receipt

The Receipt page turns your cash flow into a receipt: expenses first, then income, itemised.

## Filters

- **Date range**: the period to include.
- **Detail level**:
  - **Macro**: one line per category.
  - **Detailed**: sub-categories listed under each category.
- **Exclude categories**: remove whole categories, or single sub-categories in Detailed mode.
- **Exclude transactions by GUID**: paste one or more transaction GUIDs. Those transactions are left out of the totals, the QR summary and the printable report.

## What you see

- the receipt itself, with totals and percentages;
- a **Download .txt** button;
- a QR code that encodes a short summary readable by any phone camera.

The QR code is not drawn in privacy mode, because it would reveal the amounts.

## Excluding by GUID

Paste one or more GUIDs, separated by spaces, commas, semicolons or new lines.

- income and expenses are shown as positive amounts;
- transfers are shown with their sign;
- if a GUID is not found among income/expense transactions, you get a warning;
- the list of excluded transactions appears in an expander, with a **Clear GUID exclusions** button.

## Export

- **Download .txt**: the plain-text receipt.
- **Download report (.html)**: a self-contained A4 report.
- **Print / save as PDF**: prints the receipt page. Disabled in privacy mode.