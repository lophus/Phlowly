# Privacy and export

## Privacy mode

Every page has a **Hide amounts (privacy)** toggle in the sidebar.

When it is on:

- every amount becomes bullets;
- printing and downloading are disabled;
- the Receipt page does not draw the QR code, because the QR would reveal the amounts;
- the data-quality and KPI summaries are masked too.

Turn it off when you are ready to print or share.

## Printing

Each page has a **Print / save as PDF** button. It opens the browser print dialog. Choose *Save as PDF* as the destination to get a PDF file.

The printed page is a clean A4 report with the page title, subtitle and period at the top.

## Downloading

- **Download report (.html)**: a self-contained HTML file. Open it anywhere and print it.
- **Download .txt** (Receipt page): the plain-text receipt.
- **Download CSV** (Transactions, KPIs, Home data quality): the filtered table.

Downloads are disabled while privacy mode is on.

## QR code

The Receipt page draws a QR code that encodes a short summary of the receipt. Any phone camera can read it, ready to copy or share. It is not drawn in privacy mode.

## Read-only safety

The GnuCash database is opened in read-only mode. The app never writes, updates or changes the schema. Safe to run on your real book.