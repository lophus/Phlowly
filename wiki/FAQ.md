# FAQ

## Does Phlowly write to my GnuCash file?

No. The database is opened in read-only mode. The file hash is unchanged after running Phlowly.

## Why are amounts summed if I have more than one currency?

The app sums amounts as if they were one currency. Home warns you when more than one currency is present. Convert or split books if this matters.

## Why is my runway different from what I expected?

Runway = money base ÷ **median** monthly spending, not the average. One very expensive month does not drag the whole number up. Check which base you selected: Availability or Liquid funds.

## Why can the runway after the plan be lower than today?

Because the runway is a ratio. The money can grow while the planned median spending grows even more. Also, money sent to Invested or Debt buckets does not count as available cash.

## Why does the Plan use the average month, not the median?

The Plan baseline uses the **mean** month, so every month counts, including one-off peaks. The KPIs use the **median** for burn rate and runway. The two answer different questions.

## What is the difference between Availability and Liquid funds?

- **Availability**: bank, cash, card and asset accounts.
- **Liquid funds**: bank, cash, card accounts plus the asset accounts you flagged as liquid.

## Why is the emergency-fund cover different from the runway?

The emergency-fund cover counts only **liquid** money and uses the **planned** monthly spending. The runway counts the **chosen base** (availability or liquid) and uses the **historical or planned** median burn.

## Where are my settings and saved plans stored?

- Settings: `settings.json` next to Phlowly.
- Saved plans: `plans.json` next to Phlowly.

Both are plain JSON files you can back up or edit.

## Why does Phlowly stop with “no transactions”?

The database contains no transactions, or both `deltas` and `flows` are empty. Check that you pointed `GNUCASH_DB` at the right file.

## How do I report a bug?

Collect the app version, the GnuCash version, the Python version, the steps to reproduce and the full error message, then open an issue with that information. Include whether the bug happens with a specific account or transaction.