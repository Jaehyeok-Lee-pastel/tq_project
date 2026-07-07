# TQQQ 200-Day Strategy Coach Final Philosophy

Date: 2026-07-07

This app is not a stock picker. It is a rules-based coaching tool for managing a TQQQ-centered strategy around the QQQ 200-day moving average.

## Final Principles

1. QQQ is the signal asset.
   - The main trend filter is QQQ versus its 200-day moving average.
   - TQQQ's own moving average can be monitored, but it is not the primary signal.

2. Above the 200-day line, participate first and then control leverage.
   - The app should avoid excessive idle cash in normal uptrends.
   - Risk is reduced mainly by shifting from TQQQ into a 1x equity buffer, not by staying fully in cash.

3. QQQ/MA200 distance caps effective leverage.
   - Below MA200: TQQQ 0%, SGOV/CASH defense.
   - 0-10% above MA200: up to roughly 2.5x effective leverage.
   - 10-20% above MA200: up to roughly 2.0x effective leverage.
   - 20-30% above MA200: up to roughly 1.5x effective leverage.
   - 30%+ above MA200: sharply reduce new TQQQ execution.
   - 40-50%+ above MA200: move close to 1x or defensive exposure.

4. Use one 1x buffer by default.
   - Base structure: TQQQ + one 1x buffer + SGOV/CASH.
   - QQQM is preferred when the user wants to keep Nasdaq-100 direction while lowering leverage.
   - SPYM is preferred when reducing Nasdaq/technology concentration matters more.
   - Holding both QQQM and SPYM is allowed only when there is a clear reason; it is not the default.

5. Split buying is execution discipline, not an alpha engine.
   - Keep 2-3 TQQQ tranches.
   - Do not create many small curve-fit rules.
   - Do not wait indefinitely in cash for perfect pullbacks.
   - If a TQQQ tranche is not executable, keep participation through QQQM/SPYM when the market is above MA200.

6. SGOV/CASH has a specific role.
   - Primary use: below MA200 defense, extreme overheat, and near-term TQQQ execution reserve.
   - It should not become the default destination for all unexecuted capital in a healthy uptrend.

7. Backtests compare philosophy, not predictions.
   - Compare pure TQQQ 200-day, disparity-capped TQQQ+1x, and user custom versions with the same initial capital.
   - Evaluate CAGR, MDD, recovery period, trade count, and rule simplicity.
   - Prefer robust, repeatable rules over impressive-looking custom rules.

## Product Implications

- Strategy Studio should recommend a simple target allocation, not a complex trading recipe.
- Strategy Management should show whether each TQQQ execution is allowed, waiting, blocked, or already done.
- If TQQQ is waiting, the coach should explain where the capital participates or waits: QQQM/SPYM, SGOV, or CASH.
- Latest philosophy upgrades should be versioned, so the user can see how old strategies differ from the current rules.
- Rules & Trust should make the hierarchy clear: MA200 filter, leverage cap, 1x buffer, split execution, defense.

