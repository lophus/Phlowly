# Simulator

The Simulator answers long-term questions: *what happens if I keep going? what if things go wrong? when can I stop working?*

## Starting point

Choose the source of your numbers:

- **Historical data only**: last 12 months, average, Macro level.
- **A saved plan**: income, spending, surplus and invested returns from that plan.

Changing the source resets the default assumptions.

## Wealth projection

A Monte Carlo simulation with **1,000 random futures**. Each year applies a random return around your expected return, with the volatility you set.

Inputs:

- **Start from**: net worth, invested accounts or a custom amount.
- **Yearly contribution**: what you add over a whole year.
- **Contribution growth (%/yr)**: how much the contribution rises every year.
- **Expected return (%/yr)**.
- **Volatility (%/yr)**: how bumpy returns are.
- **Horizon (years)**.
- **Inflation (%/yr)**.
- **Show in today’s money**: removes inflation.
- **Target (€)**: drawn as a line on the chart.

The fan chart shows:

- a light band for the 10th–90th percentile;
- a dark band for the 25th–75th percentile;
- a solid median line;
- a dotted line for the plan with no volatility.

Tiles show the median outcome, the likely range, how much you contributed, market growth and the chance of reaching the target.

## Goals

Track savings goals such as a trip, a car or a deposit.

For each goal you enter:

- name;
- target amount;
- date;
- saved so far;
- return %/yr.

The Simulator computes how much you need to save per month and compares it with your monthly surplus:

- **Within reach**: your surplus covers every goal;
- **Short by X**: you need to save more, adjust a date or change the plan.

Goals are saved in `settings.json`.

## Stress test

Starts from your liquid funds and draws three cash paths over a chosen horizon:

- **Typical month**: median income and spending.
- **Your scenario**: income drops by a percentage for some months, spending changes permanently.
- **Worst case**: income and spending one standard deviation against you.

Tiles show how long the cash lasts and the lowest point.

A sensitivity chart shows how your runway changes if monthly spending were 50% to 200% of today’s.

## Financial independence

- **Independence number**: annual spending ÷ withdrawal rate. With 4%, it is 25 × annual spending.
- **Reached so far**: your current pot as a percentage of the number.
- **Time to get there**: with no volatility, using your yearly contribution.
- **Chance by year N**: probability from the simulation above.

## Report

The Simulator page can be printed or downloaded as a self-contained HTML report, including the fan chart, goals, stress test and financial-independence tiles.