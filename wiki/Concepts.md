# Concepts

This page explains the words used across the dashboard, in plain language.

## Availability

Money in your bank, cash, card and asset accounts. This is the default base for the runway.

## Liquid funds

Bank, cash and card accounts, plus the asset accounts you flagged as liquid in KPI settings.
It is smaller than availability when some asset accounts are not flagged.

## Burn rate / median monthly spending

The middle month of your monthly expenses. The runway divides by this, **not** by the average.
One very expensive month does not drag the whole number up.

## Runway

How many months you can pay for with your money base, at the current or planned burn rate:

`runway = money base ÷ median monthly spending`

## Cover (emergency fund)

The same idea as runway, but for the emergency fund:

`cover = liquid money at the end of the plan ÷ planned monthly spending`

## Baseline surplus

Income minus expenses before you change anything in the plan, calculated from the chosen history period.
It is an annual figure; divide by 12 for a monthly figure.

## Surplus

Income minus expenses after your plan changes. It is annual in the budget table.

## Free cash

The part of the surplus not assigned to any bucket. It stays liquid.

## Over-allocated

The buckets ask for more than the surplus. The cash is unchanged; only the labels do not add up.

## Return %/yr

The annual growth assumed for a bucket or investment. It is a forecast, not a guarantee.
The app converts it to a monthly rate consistently: `(1 + r)^(1/12) − 1`.

## Volatility

How bumpy returns are: standard deviation ÷ median. Higher volatility widens the range of outcomes and lowers the median slightly, because losses hurt more than gains of the same size help.

## Financial-independence number

Annual spending ÷ withdrawal rate. With the classic 4%, it is 25 × annual spending.

## Withdrawal rate

How much of the pot you can spend each year in retirement. 4% is the classic rule of thumb.

## Mean vs. median

- **Mean**: the average month. Every month counts, including one-off peaks.
- **Median**: the typical month. It ignores one-off peaks.

The KPIs use the **median** for burn rate and runway. The Plan uses the **mean** month as its baseline.