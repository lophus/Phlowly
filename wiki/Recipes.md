# Recipes

Short, practical answers to common questions.

## Will I run out of cash if I lose my job?

1. Open **Simulator → Stress test**.
2. Set **Income drops by** to `100%`.
3. Set **…for how many months** to `6`.
4. Set **Spending changes by** to `+10%`.
5. Read **Your scenario: cash lasts** and the **Lowest point**.

If the cash lasts longer than your unemployment risk, you are safe. If not, raise the emergency fund target in the Plan page.

## Can I save for a car in 18 months?

1. Open **Simulator → Goals**.
2. Add a goal: *Car*, target amount, date 18 months from now, saved so far, expected return.
3. Look at **Needed per month** and the **Verdict**.

If the verdict is *Within reach*, your surplus covers it. Otherwise adjust the date, the amount or the plan.

## Compare a cautious plan with an optimistic one

1. In **Plan**, build a cautious plan: lower income growth, higher expenses.
2. Save it as *Cautious*.
3. Build an optimistic plan and save it as *Optimistic*.
4. Open **Scenarios**. The table compares all KPIs; the chart shows the expected cash path and the volatility bands of one selected plan.

## Exclude a transaction from a receipt

1. Open **Transactions** and find the transaction.
2. Copy its **Transaction GUID**.
3. Open **Receipt**, paste the GUID into **Exclude transactions by GUID**.
4. The receipt, the QR summary, the .txt export and the printable report all exclude it.

You can paste several GUIDs at once, separated by commas, spaces or new lines.

## Hide amounts and print a report

1. Turn on **Hide amounts (privacy)** in the sidebar.
2. All values become bullets.
3. Printing and downloading are disabled while privacy is on, so turn it off when you are ready to print.
4. Use **Print / save as PDF** and choose *Save as PDF* as the destination.

## Set up liquid assets and the runway basis

1. Open **KPIs**.
2. In the sidebar, select the asset accounts that should count as liquid.
3. Choose **Runway based on**: Availability or Liquid funds.
4. Toggle **Exclude current month from statistics** if the month in progress is incomplete.

These settings are saved in `settings.json`.