# Backtest Engine Overhaul (2026-07-10)

Independent review and overhaul of the Codex-built backtest stack. Goal:
keep the strategy philosophy unchanged, make the numbers trustworthy, and
compare every strategy under identical conditions.

## Why results changed

Backtests previously covered only ~10 recent years of raw (dividend-excluded)
closes and contained calculation defects. After this overhaul the default
window is 1999-12 to present, so all conclusions now include the 2000-2002
and 2008 crashes.

## Data layer (new: `app/services/market_data.py`)

1. Full daily history from Yahoo (explicit epoch bounds; `range=max` silently
   downgrades to monthly bars) with dividend-adjusted closes. Stooq fallback.
2. Daily on-disk snapshots per (provider, symbol) under `data/market_cache/`:
   reproducible runs within a day, stale-snapshot fallback on outages.
3. Synthetic pre-inception TQQQ/QLD: `L x QQQ daily return - expense/252 -
   (L-1) x financing/252`, anchored backwards at the first real price.
   Validation vs real ETF overlap (`python -m scripts.validate_synthetic`):
   TQQQ 4,125 overlap days, mean daily error -0.04bp, synthetic CAGR 42.66%
   vs real 43.55% (slightly conservative). QLD: -0.06bp, 25.26% vs 25.54%.
4. SPY history added; SPYM/VOO/SPLG/VTI now use real S&P returns instead of
   being silently mapped to QQQ.

## Engine fixes (`app/services/backtest_engine.py`)

- **Cash-destruction bug (daily accumulation)**: the full daily buy budget was
  deducted from cash while only `budget x buy_ratio` was invested; in
  deceleration tiers up to 70% of each day's budget vanished.
- **Stranded defensive cash (daily accumulation)**: proceeds of the MA200
  defensive sell re-entered only at the monthly-contribution pace (i.e. almost
  never). Now redeployed over 21 trading days after the MA is reclaimed.
- **First-day return dropped**: equity curves started at day 1, so metrics
  ignored the first day's return. Curves now start with a day-0 anchor.
- **MDD/underwater on the TWR index**: with large contributions the raw equity
  curve is deposit-cushioned; risk metrics now use the cash-flow-adjusted
  return index. (QQQ buy-and-hold MDD now reads -83%, matching history.)
- **Sortino**: standard downside deviation over all days (was: sample stdev of
  negative days only).
- **Staged strategy ratchets**: 50MA dip reduction and overheat trim are now
  recoverable (restore on 50MA reclaim / disparity cooling); a backtest that
  starts with disparity >= +15% enters with a reduced tranche instead of
  waiting in cash indefinitely.
- **Projection** includes monthly contributions (FV of annuity); profit is
  net of deposits.
- **Trade log**: routine daily/monthly contribution buys are cash flows, not
  trades; the daily strategy logs tier changes only, so `trade_count` is
  meaningful in scoring.

Reference run (initial 10M KRW, +1M KRW/month, 1999-12..2026-07, TWR):

| strategy          | CAGR    | MDD     | notes                          |
|-------------------|---------|---------|--------------------------------|
| tqqq_200ma        | ~12.2%  | ~-68%   | staged, defaults               |
| tqqq_daily_200ma  | ~11.6%  | ~-58%   | was 4.1%/-91% before bug fixes |
| qld_200ma         | ~10.3%  | ~-58%   |                                |
| qqq_buy_hold      | ~8.9%   | ~-83%   | benchmark, dividends included  |
| tqqq_buy_hold     | ~-2.0%  | ~-100%  | dot-com wipeout                |

## Robustness (philosophy principle 7)

`/compare/strategies` now returns `rule_robustness`: the winning strategy is
re-run with perturbed rules (disparity bands x0.8/x1.2, deceleration factors,
MA-exit hysteresis +/-2%, overheat-trim threshold). Daily accumulation scored
~88-95 ("robust"): CAGR spread under 0.5%p across perturbations, i.e. the
rules are not curve-fit. Experiment knobs live on `BacktestRunRequest`
(`disparity_band_scale`, `daily_decel_mid/high`, `ma_exit_band_pct`,
`overheat_trim_distance_pct`).

## Guardrails

- Golden tests (`app/tests/test_backtest_engine_golden.py`) pin exact values:
  TWR vs contributions, MDD de-cushioning, Sortino, synthetic extension math,
  money conservation, redeploy-after-defense, ratchet recovery.
- Deployed environments refuse shared-JSON reads/writes for anonymous users
  (403 via `UserFacingPermissionError`); local dev keeps the JSON fallback.
- `strategy_engine.py` split into `strategy_allocation.py` (pure scoring) and
  `strategy_report.py` (plan/report builders); public API unchanged.

## Scoring redesign (same day, follow-up)

The old ranking formulas were calibrated for a 10-year window and broke on
full history: profit saturated at 100 (cumulative-return term), defense
collapsed to ~0 (any MDD beyond -71% scored zero), so rankings were decided
almost entirely by the hardcoded risk priors. `score_backtest` is now
window-invariant and benchmark-relative:

- profit = 50 + (CAGR - benchmark CAGR) x 9  (50 = matches QQQ buy-and-hold)
- defense = 0.6 x (50 + MDD-edge x 1.8) + 0.4 x (100 + MDD x 1.2)
- strategy risk = 0.5 structural prior + 0.5 measured-MDD component
- consistency uses trades PER YEAR, not cumulative trade count
- weights 0.30/0.30/0.25/0.15; reasons quote the benchmark edge explicitly

`StrategyCompareRequest` also gained `start_date`/`end_date` so sub-period
research (e.g. 2010+ bull only) is a first-class comparison. Pinned by
`app/tests/test_compare_scoring.py`.

Follow-up: `execution_score` (17% weight) added to the ranking — counts only
decision events (daily strategy: defensive sells; staged: every transition;
buy-and-hold: none) plus a rule-complexity penalty, with the trade penalty
removed from consistency to avoid double counting. `ma_exit_band_pct` is now
a first-class compare/UI parameter. See
docs/01_strategy_philosophy/research_daily_accumulation_findings_2026-07-10.md.

## Execution layer (2026-07-10~11 follow-ups)

Research→execution pipeline shipped: adopt-research endpoint stores the
verbatim rule set (`research_config`); `/managed-strategies/{id}/today`
(services/today_engine.py) computes the daily instruction with the SAME rule
helpers as the backtest engine. Management UI overhauled for research
strategies: today-decision panel (KRW+USD amounts, one-click journal log with
duplicate guard, month execution progress), salary deposit endpoint
(`POST /{id}/deposit` — cash+total grow, deposit journal, version bump),
strategy deletion, SGOV parking rule aligned with the philosophy (liquid
buffer = one month's buy budget; park only the excess; >=100k threshold to
avoid churn; defense regime = full parking) with one-click logging. Legacy
coaches (philosophy upgrade / cash-ratio adjustment / contribution advice)
hidden for research strategies — they belong to the old allocation model.

## Known limitations (documented in every response's `data_notes`)

- Returns are USD-based; KRW FX swings and Korean capital-gains tax (22%
  after the 2.5M KRW annual deduction) are not modeled — frequent-trading
  strategies overstate after-tax results.
- Financing costs for the synthetic era use rounded annual average short
  rates; second-order impact (validated above).
- Cash yield is a user-set assumption, not realized SGOV returns.
