# KPIs

The KPI page turns your history into a few numbers that answer the practical questions:
how long can I last, how much do I usually spend, and how bumpy is my money?

## Filters and settings

- **Date range**: the period used for the statistics.
- **Asset accounts counted as liquid**: bank, cash and card accounts are always liquid; asset-type accounts count only if you select them.
- **Runway based on**: **Availability** or **Liquid funds**.
- **Exclude current month from statistics**: the month in progress is incomplete and can skew medians and standard deviations.
- **Reload data**: clears the cache and re-reads the database.

## Hero: availability vs. liquid funds

Two numbers side by side:

- **Availability**: bank, cash, card and asset accounts.
- **Liquid funds**: bank, cash, card accounts plus the asset accounts you flagged as liquid.

## Runway

**Runway = money base ÷ median monthly spending**

Two gauges:

- **Runway (months)**: how many months your money lasts at the typical burn rate.
- **Worst-case runway (months)**: same calculation using the worst-case burn, which is median spending plus one standard deviation.

## Headline tiles

- **Savings rate**: `(income − expenses) ÷ income`.
- **Net runway**: median income minus median spending, per month, as a percentage of median income.
- **Worst-case net runway**: even if income and spending move against you, how long the money lasts.
- **Liquidity**: liquid funds as a percentage of availability.

## Monthly behaviour

For both expenses and income:

- median;
- standard deviation;
- volatility = standard deviation ÷ median;
- a band chart showing the monthly series, the median and the ±1σ band.

## Data quality note

The caption at the bottom tells you how many months were used and whether the current month was excluded.

## Export

- **Download CSV**: exports the KPI summary as CSV. Disabled in privacy mode.
- **Print / save as PDF**: prints the page as an A4 report. Disabled in privacy mode.