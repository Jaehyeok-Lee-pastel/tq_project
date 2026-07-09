# 10 Persona QA Report - 2026-07-09

## Scope

TQQQ 200-day strategy coach was tested with 10 simulated users. Three personas were intentionally critical professional-investor reviewers.

Primary checks:
- TQQQ 200-day philosophy is preserved.
- Risk-off state does not recommend leveraged entry.
- Very aggressive users see a higher TQQQ cap with clear warnings.
- SHY does not appear in default candidates or new recommendation plans.
- Conservative users are not pushed into leverage.
- Duplicate candidate symbols do not overwrite intended allocation weights.

## Persona Results

| ID | Persona | Market | Top Recommendation | QA Result |
| --- | --- | --- | --- | --- |
| P1 | Defensive beginner | QQQ +12.5% above 200MA | VOO + SGOV | Pass after fix. No leverage. |
| P2 | Stable-growth salary investor | QQQ +12.5% | VOO + small TQQQ/QLD + SGOV | Pass. Conservative leveraged sleeve only. |
| P3 | Current-user-like QLD + semiconductor holder | QQQ +12.5% | QQQ + TQQQ + QLD + BIL/CASH | Pass. Semiconductor not forced. |
| P4 | Very aggressive, acceptable zone | QQQ +12.5% | QQQ + TQQQ + QLD + CASH | Pass. High TQQQ cap displayed with warning. |
| P5 | Very aggressive, stretched zone | QQQ +22.6% | QQQ + reduced TQQQ/QLD + CASH | Pass. TQQQ cap reduced from 75% to 50%. |
| P6 | New entrant in risk-off | QQQ -6.25% below 200MA | CASH 100% | Pass after fix. No TQQQ/QLD exposure. |
| P7 | Critical pro A: leverage discipline | Stretched | QQQ + reduced TQQQ/QLD + CASH | Pass. Still aggressive, but below cap. |
| P8 | Critical pro B: SHY challenge | Reduced-entry | QLD + QQQ + SGOV/BIL | Pass. Existing SHY is not carried into new plan. |
| P9 | Critical pro C: small seed, high risk | Reduced-entry | QQQ + TQQQ + QLD + CASH | Pass. Needs UI guidance for share-price affordability later. |
| P10 | Near-retirement conservative | Reduced-entry | VOO + SGOV | Pass after fix. No leverage. |

## Issues Found And Fixed

### 1. Risk-off plan could still select QLD

Initial QA found that a risk-off user with QQQ below the 200-day line could receive a QLD allocation through the QLD plan. This contradicted the core rule: below QQQ 200MA, new leveraged exposure should be blocked.

Fix:
- In `risk_off`, QLD plan and mixed plan now set TQQQ/QLD/1x equity exposure to 0 and route to defensive cash-like allocation.

### 2. Duplicate symbols could overwrite allocation weights

Initial QA found that when SPYM was selected both as core and satellite, the later `SPYM: 0` entry overwrote the intended core SPYM ratio in a Python dict literal.

Fix:
- Added `ratio_map()` to aggregate repeated symbols instead of allowing dict overwrites.

### 3. Defensive users could receive tiny QLD exposure

Initial QA found 2-3% QLD exposure for defensive/near-retirement users.

Fix:
- Users with risk score <= 35 now receive no QLD in the QLD or mixed recommendation plans.

## Final QA Verdict

Overall QA score after fixes: 91 / 100.

Strengths:
- TQQQ 200MA core philosophy is materially stronger.
- SHY is no longer part of default recommendation flow.
- Very aggressive mode clearly shows higher TQQQ capacity without implying immediate all-in buying.
- Risk-off and defensive behavior is cleaner.

Remaining concerns:
- Some top-plan titles can still sound aggressive even when the actual allocation is defensive. Example: a conservative plan may be titled "QLD buffer leverage" while allocation is VOO/SGOV only.
- Critical investor P9 highlights a future UI issue: small accounts need share-price-aware guidance, especially QQQ vs QQQM and order-price entry.
- Risk-off aggressive users receive a low fit score because the app intentionally rejects their desired aggression. This is philosophically correct, but the UI should explain "fit is low because the market regime overrides your risk preference."

Recommended next fixes:
1. Dynamically rename QLD plan if QLD allocation is 0.
2. Add a short explanation when market regime overrides user risk appetite.
3. Add share-price affordability warnings for QQQ/TQQQ/QLD/QQQM recommendations.
