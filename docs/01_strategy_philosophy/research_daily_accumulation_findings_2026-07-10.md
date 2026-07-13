# Daily Accumulation Research Findings (2026-07-10)

## ✅ FINAL: adopted strategy and operating charter

**Adopted (managed strategy, running via the 오늘의 판단 tab):**
매일 적립 감속 **80:20** · 조기 방어 밴드 **+2%** · 이탈 시 **현금/SGOV 100% 방어** ·
월 100만원 적립. Full-period (1999~) evidence: CAGR 17.15%, MDD -57.9%,
worst year -42%, ~2.4 decisions/yr, robustness 80+.

**Operating charter (user-confirmed 2026-07-10): the rules win in every
tested deviation — follow them mechanically.**
1. Exchange the monthly 1M KRW every month regardless of disparity; park
   idle USD in SGOV (the model assumes ~4.5% cash yield).
2. Buy daily at the app's computed split; deceleration is dot-com insurance
   whose recent cost is ~zero (study 8-9). Do not "just keep buying 8:2"
   (decel-off ranked 19th/46, MDD -79%).
3. Idle cash is not idle — it is reserved for the post-defense 21-day
   redeploy at the recovery. Do not deploy it early (study 11-13) and do not
   dip-buy above the MA (study 14: loses on every metric including final
   capital).
4. Defense: 2 consecutive closes below MA200 x 1.02 → sell TQQQ and QQQM,
   hold cash/SGOV; re-enter over 21 trading days after the line is reclaimed.
5. Log every action in the journal (the today panel does it in one click);
   revisit reserve-redeploy (N>=42) only if carried cash exceeds ~6 months of
   contributions with no MA break.

Full-period (1999-12 ~ 2026-07, synthetic-extended, adjusted close) matrix run:
3 research presets x 5 strategies, same holdings (TQQQ 1.6M / QQQM 0.5M /
cash 0.4M KRW) + 1M KRW monthly. TWR metrics.

## Key findings

1. **"Conservative" 6:4 is NOT safer.** Under current rules only TQQQ is
   defended below the MA200; the 1x sleeve rides every crash. So a larger 1x
   ratio means a larger UNDEFENDED pocket: 6:4 MDD -67.7% vs 8:2 MDD -64.0%.
   Lowering the accumulation ratio is not defense.
2. **A +2% early-defense band improves every configuration.** Daily 7:3/6:4/
   8:2 all gain ~+0.3-0.4%p CAGR and ~2-3%p shallower MDD; the staged
   strategy gains even more (MDD -54.4% -> -39.5%, CAGR 12.47%). Consistency
   across configs argues against curve-fitting, but note the band came out of
   the robustness probes (mild selection risk).
3. **Execution burden is measurable and very different.** Decision events
   (where the user must act on a signal): daily accumulation ~2.4/yr
   (defensive sells only; buys are mechanical), staged ~15.8/yr (dip sells,
   staged rebuys, trims, recoveries). Buy-and-hold: 0.
4. **Money-weighted outcomes favor daily accumulation.** Contributions deploy
   into the market immediately, so final capital is ~6-9억 higher than the
   staged strategy at equal contributions, even at similar CAGR.

## Best-practice conclusion (as of this research)

**Daily accumulation 7:3~8:2 + ma_exit_band_pct=+2** — CAGR 11.9~12.3%,
MDD -61~-63%, ~2.4 decisions/yr, robustness 80-95. The staged strategy has
better risk-adjusted numbers (esp. with the band: 12.47% / -39.5%) but
demands ~16 flawless signal responses per year for decades; its edge only
exists if that discipline holds.

Reflected in the product:
- `execution_score` (17% of total) in `/compare/strategies` rankings —
  decision-event frequency + rule-complexity penalty; mechanical accumulation
  buys don't count.
- `ma_exit_band_pct` exposed on StrategyCompareRequest and the Compare UI.
- "베스트 프랙티스 8:2 + 조기방어 2%" preset added; 6:4 preset carries the
  finding-1 warning.

## Defense-mode study (same day, follow-up)

`defense_mode` added to both engines: `cash` (everything to SGOV/cash below
the line — final philosophy doc), `spym_sgov_half` (50% SPYM + 50% SGOV —
community-rule variant the user recalled), `hold_one_x` (keep 1x invested —
previous daily-strategy behavior). Same conditions as above, exit band +2%:

Full period (1999~), daily 8:2:
| defense      | CAGR   | MDD    | longest DD | final (KRW) |
|--------------|--------|--------|-----------|-------------|
| hold_one_x   | 12.33% | -61.3% | 2716 days | 4.9B        |
| cash         | 17.15% | -57.9% | 1777 days | 14.5B       |
| spym_sgov_half | 17.17% | -59.2% | 1777 days | 15.4B     |

Findings:
5. **Defending the 1x sleeve dominates everything else.** Selling QQQM too on
   MA break (cash/half modes) adds ~+4.8%p CAGR and triples final capital vs
   holding it. Mechanism: each defense/re-entry cycle re-forms the core at
   the accumulation split (8:2), so the portfolio converges to a TQQQ-heavy
   MA-timed book, and the QQQM leg itself gets MA timing instead of riding
   -83% crashes. The defense-mode choice is really a choice of what the core
   becomes.
6. **Half vs cash is secondary and regime-dependent.** Half is slightly
   better on returns and underwater time (esp. 2010+ whipsaw era: 28.3% vs
   27.6% CAGR, 490 vs 676 underwater days) because SPYM keeps rebound
   participation; cash is clearly safer in mega-bears (staged 45%:
   MDD -39.5% cash vs -51.8% half — SPY fell with everything in 2000-02).
7. Recent-era caveat: 2010+ MDD for cash/half daily is -53~-56% vs -33~-36%
   for hold_one_x, because the book is now mostly TQQQ. Full-period cash/half
   still dominates on every metric.

## Current best practice (updated after the defense-mode sweep)

Full 23-case sweep (defense x band x ratio x strategy, risk 80, same
holdings/contributions) ranked by the app's total score:

1. daily 7:3 + band 2% + defense cash — 83 (CAGR 16.43%, MDD -55.2%, 122억)
2. daily 8:2 + band 2% + defense cash — 82 (CAGR 17.15%, MDD -57.9%, 145억)
3. daily 8:2 + band 2% + defense half — 79 (CAGR 17.17%, MDD -59.2%, 154억 max)
4. staged45 + band 2% + defense cash — 79 (MDD -39.5% best among leveraged)
5. staged45+1x30 + band 2% + defense cash — 79

The "베스트 프랙티스" preset in ComparePage now encodes case 1 (7:3, band 2,
defense cash); its summary points to cases 2-3 as one-knob variations. The
old hold_one_x behavior ranks 11th at best — defending the whole book on the
MA break is the single most impactful rule choice found so far. Caveat:
profit scores saturate at 100 for the top daily cases (benchmark edge > +5.6%p),
so ordering inside the top tier is decided by defense/execution; and this is
one in-sample period — check the rule-robustness panel before acting.

## Deceleration on/off study (user question: "why not just keep buying 8:2?")

daily 8:2 + band 2% + cash defense, deceleration ON vs OFF
(`daily_decel_mid/high/stop` = 1.0 disables it; stop-only relaxation = 0.30):

| period | variant | CAGR | MDD | worst yr | underwater | final |
|---|---|---|---|---|---|---|
| 1999~ | decel ON (base) | 17.15% | -57.9% | -42% | 1777d | 145.0억 |
| 1999~ | decel OFF | 15.34% | **-79.1%** | **-67%** | **3456d** | 161.5억 |
| 1999~ | stop→30% only | 16.63% | -62.9% | -49% | 2737d | 144.5억 |
| 2010~ | ON vs OFF | 27.6 vs 28.0% | -56.2 vs -56.8% | ~same | 676 vs 504d | 41.2 vs 44.2억 |
| 2016~ | ON vs OFF | 37.3 vs 38.6% | ~same | ~same | same | 11.6 vs 12.5억 |

Findings:
8. **Deceleration is dot-com-mania insurance, not a return enhancer.** Since
   2010 it makes almost no difference (OFF is even slightly ahead). All of its
   value is concentrated in 1999-2000 (+30~45% disparity era): it cuts MDD
   -79% -> -58%, worst year -67% -> -42%, halves underwater time.
9. **The ">30% stop" is the load-bearing part.** Relaxing only the stop
   (keep 30% buys above +30%) gives back most of the protection (-63% MDD).
   The 65%/30% mid tiers matter far less.
10. Money-weighted caveat: OFF ends richer over the full period (161 vs 145억)
   because DCA money stays fully invested through long bulls — the price is
   the -79%/13.7y-underwater path. Keep deceleration; treat it as the premium
   for surviving a mania.

`daily_decel_stop` knob added to BacktestRunRequest; "감속 해제" variation
added to the rule-robustness panel. Strategy deletion (DELETE
/managed-strategies/{id}) added the same day.

## Reserve-redeploy study (user idea: re-enter carried cash when disparity normalizes)

`reserve_redeploy_days` (N) added: deceleration leftovers are tracked as a
reserve and re-enter at 1/N per day once disparity drops below +10%
(N=0 = base rule: reserve waits for a defense-recovery cycle).
daily 8:2 + band2 + cash defense:

| period | N=0 (base) | N=10 | N=21 | N=42 |
|---|---|---|---|---|
| 1999~ CAGR | 17.15% | 16.71% | 16.90% | 17.01% |
| 1999~ MDD / worst yr | -57.9 / -42% | -62.4 / -51% | -59.7 / -47% | -58.2 / -45% |
| 1999~ final | 145.0억 | 152.7억 | 150.0억 | 147.9억 |
| 2010~ CAGR / underwater | 27.64% / 676d | 27.93% / 504d | 27.86% / 504d | 27.79% / 504d |

Findings:
11. The idea works in normal regimes: since 2010 every N improves CAGR, final
    capital, and shortens underwater time (676 -> 504 days) with ~no MDD cost.
12. In mania regimes it partially refunds the deceleration insurance: reserve
    built during 1999-2000 re-entered on brief normalizations near the top,
    worsening worst-year (-42 -> -45~-51%) and full-period TWR.
13. Speed is the knob: fast (N=10) is harmful full-period; slow (N=42) is
    near-free (score tie with base, final +2.9억, MDD +0.3%p deeper).
    If adopted, use N>=42. Base rule remains the default.

Note: reserve_redeploy_days is a research/backtest knob (Compare UI exposed);
the today-decision engine does not track a live reserve yet — extending it
requires journal-derived reserve state.

## Dip-buy boost study (user idea: buy extra when disparity drops sharply, e.g. +15% -> +8%)

`dip_buy_multiple` (M) added: when the disparity falls >= 3%p in one day while
still above the MA, buy an EXTRA M x daily budget from cash. daily 8:2 +
band2 + cash defense:

| period | M=0 (base) | M=1 | M=2 | M=4 |
|---|---|---|---|---|
| 1999~ CAGR | 17.15% | 16.94% | 16.72% | 16.25% |
| 1999~ MDD / worst yr | -57.9 / -42% | -58.1 / -45% | -60.4 / -48% | -65.1 / -53% |
| 1999~ final | 145.0억 | 144.8억 | 144.6억 | 144.2억 |
| 2010~/2016~ | ~identical across M (CAGR +0.0~0.1%p, MDD slightly worse) |

Findings:
14. **Dip-buying above the MA loses on every metric, at every size, including
    money-weighted final capital.** Sharp one-day disparity drops cluster at
    topping processes and crash onsets (2000, 2008, 2020-02, 2022-01) — the
    boost buys right before the defense sell and realizes the loss. In
    healthy uptrends the 3%p trigger barely fires, so there is no upside to
    collect.
15. Pattern across studies 11-14: every "do something extra with the idle
    cash" variant (faster reserve redeploy, dip boosts) gives back crash
    insurance without compensation. The base rule's implicit design — idle
    cash waits for the post-defense recovery redeploy — keeps winning; it is
    a strong local optimum.

## Batch-buy cadence study (whole-share constraint for Toss API automation)

Toss Open API supports only whole-share orders, so daily ~48k KRW buys are
impossible (1 TQQQ share ≈ 130k, 1 QQQM ≈ 350k KRW). `tqqq_batch_days` /
`one_x_batch_days` added: budgets are earmarked daily at that day's
deceleration ratio but executed every N trading days (pending waits in cash).
daily 8:2 + band2 + cash defense, full period:

| variant | CAGR | MDD | worst yr | final |
|---|---|---|---|---|
| A daily (idealized fractional) | 17.15% | -57.9% | -42.2% | 145.0억 |
| B whole-share approx (TQQQ 5d / QQQM 21d) | 17.02% | -57.2% | -40.3% | 135.3억 |
| C user idea (TQQQ daily / QQQM monthly) | 17.14% | -57.8% | -40.9% | 141.0억 |
| D weekly both (5/5) | 17.05% | -57.0% | -41.7% | 138.8억 |
| E monthly both (21/21) | 17.61% | -56.4% | -30.6% | 125.6억 |

Findings:
16. **Batching costs almost nothing in TWR** (-0.01~-0.13%p CAGR vs daily).
    The whole-share constraint is NOT a blocker for Toss API automation.
17. **The user's mixed cadence (C: TQQQ daily-ish, QQQM monthly) is valid** —
    statistically identical to the ideal and matches natural share-price
    cadence. Note QQQM's actual accumulation pace is ~1.5-2 months per share
    (monthly one_x budget ~200k < 350k/share); anywhere between B and E is
    fine per this study.
18. E (monthly both) looks best on the full period (17.61%, worst yr -30.6%)
    but that edge comes from 1999-2000 timing luck (monthly lag skipped
    mania-top buys); it is consistently WORST since 2010 (25.7% vs 27.6%,
    final -25%). Do not adopt; regime-dependent artifact.
19. Money-weighted cost of batching is the pending-cash drag: final capital
    145 -> 135~141억. Mitigated by the pending cash earning SGOV yield
    (modeled) — keep pending money parked.

Automation implication: implement orders as "buy 1 share when the earmarked
budget covers it" (per symbol). Robustness panel now includes the
whole-share batch variation.

## Salary-day upfront 1x buy study (user idea: buy the month's QQQM on payday)

`one_x_upfront_monthly` added: the monthly contribution arrives as a lump on
the month's first trading day and the month's 1x allocation is bought upfront
(above the MA; waits in cash below it). TQQQ keeps the daily decelerated
cadence. Redeploy/initial-deploy money still buys the 1x at normal ratios.

| period | A daily both | B payday 1x upfront | C month-end 1x batch |
|---|---|---|---|
| 1999~ CAGR / worst yr / final | 17.15% / -42.2% / 145.0억 | **17.32% / -38.5% / 145.8억** | 17.14% / -40.9% / 141.0억 |
| 2010~ CAGR | 27.64% | 27.67% | 27.39% |
| 2016~ CAGR | 37.32% | 37.14% | 37.01% |

Findings:
20. **Payday upfront 1x buying is valid — a slight win full-period**
    (+0.17%p CAGR, worst year -42 -> -38.5%), a tie since 2010. Classic
    "lump sum beats intra-month DCA on average" result. Fine to adopt for
    execution simplicity; differences are within noise.
21. Whole-share note: the monthly 1x allocation (~200k KRW at 20%) is still
    below one QQQM share (~350k), so the practical cadence is "buy 1 share
    on the first payday the accumulated allocation covers it" (~every 2
    months).
22. Engine-bug lesson recorded: the first implementation zeroed the 1x ratio
    for ALL budgets (including post-defense redeploy), silently stranding the
    redeploy's 1x share in cash (-11% final). Caught by comparing against C;
    fixed so only the regular contribution skips the daily 1x buy.

## Adopted (2026-07-13): payday upfront 1x mode + fractional execution

`one_x_upfront_monthly=True` applied to the live strategy (v36) and wired
end-to-end: ResearchStrategyConfig -> today engine (TQQQ-only daily
instruction + payday lump guidance) -> deposit card hint -> Compare UI
checkbox + robustness variation.

Execution note: the Toss APP supports fractional (금액) orders for US
stocks — min 1,000 KRW, 1e-6 share precision, MARKET orders only, real-time
window 23:30-05:00 KST (DST 22:30-04:00), reservation orders otherwise. So
the manual routine is: payday deposit -> buy the month's 1x allocation
(200k KRW) as ONE fractional market order. The official Open API has no
fractional orders, so future automation falls back to whole-share batching
(validated ~zero cost, studies 16-19).

## Regime-switching Monte Carlo (2026-07-13): testing many novel futures

Added a forward-looking research mode. Instead of the single historical path
(or block-bootstrap recombination), it calibrates 3 regimes (bull / bear /
sideways) on real QQQ and GENERATES novel 26y paths (endogenous regime = the
simulated price's own MA200/trend state; Student-t fat tails). It then runs
the adopted strategy + QQQ buy-hold on each and reports the DISTRIBUTION.

Backend: services/montecarlo_engine.py, schemas/montecarlo.py,
POST /research/montecarlo (threadpool; ~150 paths/25s, 300/50s). Frontend:
ComparePage split into two research sub-tabs — "전략 비교" (backward,
historical) and "미래 시뮬레이션" (forward, Monte Carlo) with a distribution
report (probability cards, percentile bars, fan chart of p5/median/p95 paths).

Reference result (adopted 8:2 config, ~150 paths): beats QQQ buy-hold in ~52%
of futures, positive CAGR in ~92%, CAGR median ~10.6%, final ~5.9x invested.

Honest caveats (shown in-app): (1) still bounded to futures whose statistical
signature resembles 1999~ QQQ; truly novel structural regimes are out of
scope by design. (2) MDD runs PESSIMISTIC (median ~-74% vs historical -57%):
the model lacks intra-regime momentum, so it over-generates MA200 whipsaw and
overstates leverage drawdown. Weight the RELATIVE metrics (beat-rate,
positive-rate) over absolute MDD. GAN-based generation was deliberately
rejected (search showed it collapses to absurd outputs; not validatable).

## 1000-path Monte Carlo strategy comparison (2026-07-13, research-only)

Ran the regime-switching MC on 6 candidate strategies over the SAME 1000
novel futures (seed 20260713, 26y). Benchmark QQQ buy-hold CAGR median 9.27%.
Recorded for awareness only — NO strategy change made; adopted daily 8:2 stays.

| strategy | CAGR med | CAGR p5 | MDD med | loss% | beat | MDD<-70 | final |
|---|---|---|---|---|---|---|---|
| A daily 8:2 cash upfront (adopted) | 10.4% | -1.5% | -73% | 7.8% | 60% | 63% | 5.9x |
| B daily 7:3 cash upfront | 10.4% | -0.9% | -70% | 6.7% | 60% | 50% | 5.7x |
| C daily 8:2 half upfront | 10.5% | -1.1% | -73% | 8.0% | 62% | 62% | 5.9x |
| D staged45 + 1x30 cash | 10.1% | +2.2% | -51% | 1.7% | 58% | 7% | 4.8x |
| E staged45 cash | 9.4% | +3.0% | -41% | 0.6% | 51% | 1% | 4.2x |
| F daily 6:4 cash upfront | 10.2% | -0.3% | -66% | 5.4% | 59% | 35% | 5.5x |

Findings (forward-looking view differs from the single historical path):
23. **D (staged45+1x30) dominates on risk-adjusted terms**: gives up only
    ~0.3%p median CAGR vs the daily leaders but cuts loss probability
    7.8%->1.7%, deep-drawdown (MDD<-70%) 63%->7%, worst-5% CAGR stays
    POSITIVE (+2.2%). Cost: lower ceiling (4.8x vs 5.9x) and ~15.5
    decisions/yr execution (6x the daily strategies) — not captured in MC.
24. **Within the daily family, the adopted 8:2 is the MOST aggressive
    (riskiest)**: 7.8% loss, 63% deep-drawdown. Shifting to 6:4 (F) or 7:3
    (B) keeps ~equal median CAGR (10.2-10.4%) while cutting loss to 5.4-6.7%
    and deep-drawdown to 35-50%. With cash defense the extra 1x sleeve is
    defended, so more 1x = safer here (reverses the earlier hold_one_x
    finding #1).
25. E (staged, no buffer) is too conservative — CAGR 9.4% ≈ benchmark 9.27%,
    beats it only 51%. Not worth the leverage.

Caveats (as always): absolute MDD is pessimistically biased (MC over-generates
whipsaw); trust the RELATIVE ordering, loss-probability, and beat-rate.
Execution burden (daily ~2.4 vs staged ~15.5 decisions/yr) is not in these
numbers. This is awareness-only research, not a recommendation to switch.

## Validation method 1/3: Walk-Forward Analysis (2026-07-13)

Rolling IS(8y)/OOS(3y), step 3y, over 1999-2026 → 6 OOS windows (incl. 2008,
2020, 2022). Each window: pick the best of 12 configs (ratio 60/70/80 x band
0/2 x defense cash/half) on IS by total_score, then score ONLY on the unseen
OOS window; also run the fixed adopted config (80:20/band2/cash) on the same
OOS. Backend services/walkforward_engine.py, POST /research/walkforward,
ComparePage "워크포워드" sub-tab.

Results:
- **Walk-Forward Efficiency 142%** (OOS ÷ IS) → NOT overfit (concern is <100%).
- **Selection stability only 33%** — the IS-best config rotates window to
  window (60:40, 80:20, various). No single config is consistently best →
  the differences between configs are largely period-dependent noise.
- **KEY: adaptive selection LOST to the fixed adopted config out-of-sample**
  — median OOS CAGR: adaptive (chase IS-best) 21.3% vs fixed 8:2 29.7%. In
  almost every window the fixed aggressive config beat the adaptively-chosen
  (often defensive 60:40) config in the following OOS period.

Interpretation: this is the classic overfitting lesson demonstrated on our
own strategy — trying to adapt the config to recent history HURT. The fixed
8:2 rule was more robust than optimization. Strong evidence that (a) the
adopted config is not overfit, and (b) "pick a sensible fixed rule and stick
with it" (what the user did) beats config-chasing. Caveat: OOS windows are
3y (noisier than 26y); recent windows are bull-heavy.

## Validation method 2/3: Parameter sensitivity heatmap (2026-07-13)

Swept ratio (50-90) x exit band (-1 to 3%), 45 cells, full-history, colored
by total_score. Backend services/heatmap_engine.py, POST /research/heatmap,
ComparePage "파라미터 지형" sub-tab (colored grid, adopted ★ / best ◆).

Result: **the entire surface is a flat plateau (scores 81-85, global spread
only 4 points).** No sharp peak anywhere. Adopted 8:2/band2 = 82, neighbor
spread 3 pts, plateau ratio 100%, verdict 고원(강건). The exact ratio/band
choice barely matters — performance is driven by the strategy STRUCTURE
(200MA + decel + defense), which all cells share. The adopted config is not a
lucky spike; it sits on a broad plateau. (Low ratios score marginally higher
on the composite, within noise — consistent with "8:2 is the aggressive end.")

## Validation method 3/3: Deflated Sharpe + PBO (2026-07-13)

40-config grid (ratio 50-90 x band 0-3 x defense cash/half); build each
config's daily TWR return series, then Bailey & Lopez de Prado stats. Backend
services/overfitting_engine.py, POST /research/overfitting, ComparePage
"과최적화 검증" sub-tab.

Results:
- **Deflated Sharpe Ratio 99.9%** (verdict 유의미/강건): observed Sharpe 0.62
  vs expected best-of-40-by-luck 0.04. The strategy's edge is REAL after
  correcting for multiple testing, non-normality (skew -0.56, kurtosis 10.6).
- **PBO 84.3%** (high) via CSCV (70 splits): the in-sample-best config lands
  below the OOS median 84% of the time.
- **The DSR-high + PBO-high combo is NOT a contradiction.** PBO measures RANK
  persistence, not magnitude. High PBO here reflects that the 40 configs are a
  flat plateau (heatmap: all 81-85) — "which specific config is best" is noise
  — while DSR confirms the strategy itself is genuinely skilled. Consistent
  with walk-forward (config-chasing hurt) and heatmap (plateau). Net message
  across all 3 methods: the STRATEGY is validated; fine-tuning the config is
  meaningless — pick a sensible one and stick with it (what the user did).

### Three-method synthesis (validation methods 1-3)
All three independently converge: (1) Walk-forward WFE 142% + fixed beats
adaptive → not overfit, don't chase config. (2) Heatmap flat plateau → choice
insensitive/robust. (3) DSR 99.9% → edge is real; PBO 84% → config ranking is
noise. The adopted daily 8:2 is a statistically validated strategy sitting on
a robust plateau; further config optimization is unproductive.

## CAPSTONE: integrated conclusion of the whole research effort (2026-07-13)

Structural decisions locked by evidence (these matter far more than the ratio):
- Signal = QQQ 200-day MA. Above: daily accumulate + disparity deceleration
  (dot-com insurance, ~free since 2010). Exit band +2% (free win, all methods).
- Defense = 2-day confirm → sell TQQQ AND the 1x → cash/SGOV; 21-day redeploy
  on recovery. Defending the 1x is the single biggest lever (+4.8%p CAGR, ~3x
  final vs holding it). Payday: buy the month's 1x upfront (fractional), TQQQ
  daily. Idle cash is reserved for the post-defense redeploy — reserve-early
  and dip-buy variants were tested and REJECTED (both hurt).
- Accumulation ratio 60:40~80:20 is a PLATEAU (heatmap 81-85, DSR/PBO: ranking
  is noise) — pick any; it barely matters.

Validation verdict (3 independent methods converge): strategy edge is
statistically real (DSR 99.9%), robust to parameters (flat plateau), not
overfit (walk-forward WFE 142%, fixed beats adaptive), survives 1000 novel
futures (92% positive, ~60% beat QQQ buy-hold). Honest caveats: MC MDD runs
pessimistic; everything is bounded to futures resembling past QQQ.

Best-5 (integrated across all lenses; risk 80, current holdings + 1M/mo):
1. daily 7:3 band2 cash upfront — best balance (plateau core, mildly safer tail)
2. daily 8:2 band2 cash upfront — ADOPTED; max-return daily, fully validated
3. daily 6:4 band2 cash upfront — safest daily (loss 5.4%, MDD<-70 35%)
4. staged45+1x30 band2 cash — most robust across futures (loss 1.7%) but ~15.5
   decisions/yr vs daily's ~2.4
5. daily 8:2 band2 half(SPYM) upfront — max final capital (5.9x, 155억) / deepest tail

Recommendation: stay on the daily-cash plateau (#1-#3). The adopted 8:2 (#2)
needs no change; 7:3/6:4 are statistically indistinguishable but marginally
safer if drawdown-averse. Config fine-tuning beyond this is unproductive
(supported conditionally by the 3 validation methods). Switch to staged+1x only if you can
sustain 6x the execution and want the shallowest tail.

## Methodology correction before production adoption (2026-07-13)

- The deployed DSR uses daily excess returns versus QQQ, not raw portfolio
  returns, and applies a conservative 100-trial correction for prior research.
- Walk-forward conclusions prioritize the compounded CAGR across
  non-overlapping OOS windows and the worst OOS-window MDD. WFE and window
  medians are secondary.
- A flat heatmap supports parameter insensitivity; it does not prove that the
  shared strategy structure will produce future alpha.
- Monte Carlo paths inherit historical QQQ regime relationships, so they are
  conditional stress tests rather than independent forecasts.
- The fixed 8:2 rule was selected with knowledge of the historical sample.
  It is the aggressive end of a 6:4-8:2 plateau, not a uniquely proven optimum.

## Open research item

Partial 1x defense (sell half the 1x on break) — middle ground between
hold_one_x and full defense; untested.
