# Transactions

The Transactions page is the search engine for your ledger.

## Filters

- **Date range**: the period to search.
- **Search**: searches description, notes, memo and number. Several values can be separated by commas.
- **GUID**: a transaction or split GUID, or several comma-separated GUIDs.
- **Min amount / Max amount**: filter by amount. `0` means no limit.
- **Accounts**: pick one or more accounts.
- **Account types**: pick one or more account types.
- **Tags**: pick one or more tags. A transaction matches if it has any of them.
- **Direction**: All, In (+) or Out (−).
- **View**: Transactions, Wallets or Categories.
- **Sort by**: date or amount.

## Views

### Transactions

One row per transaction. Amount is the effect on your money:

- expenses are negative;
- income is positive;
- transfers between your own accounts are 0.

**Moved** is how much the transaction shifted around.

### Wallets

Movements on your cash, bank, asset and card accounts, as in a GnuCash register:

- money in is positive;
- money out is negative.

### Categories

Income and expense accounts only:

- income is positive;
- expenses are negative.

## Totals

The totals bar always shows:

- rows;
- money in;
- money out;
- average;
- largest;
- mix (expenses, income, transfers, other).

Totals add up one side of each transaction only, so nothing is counted twice.

## Export

- **Download CSV**: exports the filtered table. Disabled in privacy mode.
- **Print / save as PDF**: prints the filtered table as an A4 report. Disabled in privacy mode.

## Tips

- Copy a **Transaction GUID** from this table and paste it into the Receipt page to exclude that transaction from a receipt.
- Tags come from `#tags` in the description, notes, number, memo or action. Add them in GnuCash.