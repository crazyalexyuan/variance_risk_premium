# Test A2 — Findings: Simulated Bull Put Spread

*Analysis: Alex, August 2026. Simulated from Black–Scholes pricing at VIX; not a true backtest.*
*Criteria G1–G3 pre-registered in `02_preregistration_spread.md` §0.*

---

## Method

Every trading day 1990–2026 (n = 9,201), open a $1-wide bull put spread on a SPY-scaled S&P 500: short strike at −0.30 delta, 21 trading days to expiry, held to expiry. Both legs priced with Black–Scholes using VIX as implied volatility and `^IRX` as the risk-free rate. P&L computed from where the index actually finished.

**Validation passed:** realised short delta −0.300 against a −0.30 target, strikes 2.50% below spot, zero bounds violations across all 9,201 trades.

---

## Results

Mean credit $28.70 per contract; maximum loss therefore ~$71.

| Cost assumption | Mean P&L | HAC t | Subsample t | Win rate | Worst |
|---|---|---|---|---|---|
| Gross | **$11.85** | 9.74 | 5.98 – 8.11 | 82.2% | −$85.41 |
| Net of $2.00 | $9.85 | 8.09 | 4.85 – 6.91 | 82.0% | −$87.41 |
| **Net of $3.50 (base case)** | **$8.35** | 6.86 | 4.00 – 6.02 | 82.0% | −$88.91 |
| Net of $6.00 | $5.85 | 4.80 | 2.59 – 4.52 | 81.9% | −$91.41 |

Standard deviation $36.25 throughout.

### Where the edge sits

Decomposing the base case: mean win ≈ +$28.70 (full credit), mean loss ≈ **−$66**, win rate 82.2%.

The **breakeven win rate** for that payoff ratio is `66 / (66 + 28.70) = 69.7%`. A fairly priced spread should have won about 70% of the time. It won **82.2%**. That 12.5-percentage-point gap *is* the edge, expressed as probability rather than dollars — and it is the same variance risk premium measured in Test A, now visible through a tradeable instrument.

Note also that losses cluster near maximum. A $1-wide spread on a ~$780 underlying spans 0.128% of spot, so outcomes are nearly binary: either the full credit or close to the full loss.

### Out-of-sample

Splitting at the midpoint and evaluating on 2008 onwards (n = 4,600, net $3.50): mean **$9.72**, HAC t = 5.46, win rate 82.5%. **Stronger than the full sample.** No evidence of decay.

### VIX filtering — comprehensively rejected

Nine filter configurations tested on both the full sample and the out-of-sample half. `annual_est` = `12 × mean × share`, i.e. expected annual profit running one position at a time, accounting for days the filter blocks trading.

**Full sample (net of $3.50):**

| Filter | n | Share | Mean | sub_t_min | Win % | **annual_est** |
|---|---|---|---|---|---|---|
| **No filter** | 9,201 | 1.00 | $8.35 | 4.00 | 82.0 | **100.14** |
| VIX ≤ 35 | 8,848 | 0.96 | $8.17 | 3.43 | 81.9 | 94.28 |
| VIX ≤ 30 | 8,467 | 0.92 | $7.63 | 2.60 | 81.5 | 84.22 |
| VIX ≤ 25 | 7,603 | 0.83 | $7.30 | 2.48 | 81.4 | 72.36 |
| VIX ≤ 20 | 5,778 | 0.63 | $8.39 | 2.54 | 82.9 | 63.22 |
| VIX 15–30 | 5,520 | 0.60 | $6.86 | 1.30 | 80.1 | 49.41 |
| VIX ≥ 20 | 3,427 | 0.37 | $8.29 | 0.54 | 80.4 | 37.06 |
| VIX ≥ 25 | 1,601 | 0.17 | $13.36 | 2.04 | 84.8 | 27.90 |
| VIX ≥ 30 | 736 | 0.08 | **$16.53** | 1.28 | **87.8** | 15.87 |

Out-of-sample (2008 onwards) reproduces the pattern: unfiltered 116.59, VIX ≤ 30 100.93, VIX ≥ 30 15.67.

Three conclusions:

1. **No filter beats trading unfiltered.** Every restriction costs more in forgone opportunities than it recovers in trade quality.
2. **High-VIX trades are the best, not the worst.** VIX ≥ 30 produces the highest mean ($16.53) and highest win rate (87.8%) of any subset — the exact opposite of the intuition that volatile markets are dangerous to sell into. The mechanism is that delta-targeting automatically widens the strike distance as volatility rises: the 0.30-delta 21-day put sits ~1.5% below spot at VIX 12 but ~5% below at VIX 40. Higher premium and more cushion arrive together.
3. **The differences are largely noise.** The `≤` filters are non-monotonic (≤20: 8.39, ≤25: 7.30, ≤30: 7.63, ≤35: 8.17) where a genuine effect would improve steadily as the cap tightens. And `sub_t_min` falls below significance for most filters — restricting the sample destroys the statistical power needed to detect anything.

Three separate filter hypotheses were tested across this project (VIX ≥ 25 danger zone, VIX 15–30 band, VIX ≤ 30 cap). All three were rejected. Further searching on this dataset would risk finding artefacts of the search rather than properties of the market.

### Annual pattern

Seven losing years in thirty-seven: **2000, 2001, 2002, 2007, 2008, 2018, 2022**. Every one is an equity bear market. Worst: 2002 (−$13.48/trade), 2008 (−$11.70), 2022 (−$11.31).

This is the clearest evidence that a meaningful share of the return is **equity beta rather than volatility premium**. The strategy carries positive delta and loses when the market falls.

One instructive contrast: **2020 was strongly positive (+$13.43)** despite producing the worst single VRP observation in the entire dataset (−71.96 on 20 February), while **2022 was negative (−$11.31)** in a far less dramatic year. A sharp crash damages a handful of trades and then hands rich premiums on re-entry; a slow grinding decline bleeds the strategy continuously. Duration of drawdown matters more than depth.

---

## Verdicts against pre-registered criteria

**G1 — "Mean gross P&L ≤ 0 after HAC correction." DOES NOT TRIGGER.** Gross mean $11.85, HAC t = 9.74, conservative subsample t = 5.98. The spread does capture a positive share of the premium.

**G2 — "Mean net P&L ≤ 0 after costs." DOES NOT TRIGGER.** $8.35 net of $3.50, and still $5.85 net of $6.00. Positive across every cost assumption tested.

**G3 — "Worst trade exceeds theoretical max loss." DOES NOT TRIGGER.** Zero bounds violations.

All three criteria pass. **Within the limits of this simulation, the strategy is profitable.**

---

## Limitations — why "profitable in simulation" is not "profitable"

1. **Skew is ignored.** Both legs priced at VIX; real out-of-the-money puts trade at different implied volatilities. Untested, and could move the result materially in either direction. This is the largest unquantified error.
2. **Fills assumed at theoretical prices.** Real execution is at bid/ask, not at Black–Scholes value. The cost cases approximate this but do not model it.
3. **Overlapping positions.** 9,201 trades with 21-day holds means ~21 concurrent positions. Cumulative totals are meaningless; per-trade figures are the only valid output.
4. **HAC and subsample statistics diverge** in every variant, unlike Test A where they agreed. The assumption-free subsample range is the more credible figure.
5. **Return-on-risk remains implausibly high** versus CBOE's published put-writing benchmarks. Part is explained by the structural leverage of defined-risk spreads, but the gap is not fully reconciled.
6. **Equity beta is not separated** from volatility premium. The annual pattern suggests it is a substantial component.
7. **No management.** Held to expiry, unlike the playbook's 50%-profit and 21-DTE exits.

---

## Conclusion

The simulated bull put spread is profitable across all cost assumptions tested, robust out-of-sample, and shows no decay over 36 years. The edge appears as a 12.5-percentage-point gap between the realised win rate (82.2%) and the breakeven rate implied by the payoff ratio (69.7%).

Two findings temper this. VIX-based filtering was tested across nine configurations and rejected in every one — the intuition that high volatility is dangerous to sell into is refuted, since high-VIX regimes produce both the highest per-trade profit and the highest win rate. And the annual loss pattern maps exactly onto equity bear markets, indicating that a material share of the return is ordinary market exposure rather than volatility premium.

The practical implication is unusually simple: **trade the rule mechanically and don't try to time it.** Every attempt to improve on unconditional entry made results worse.

**The unresolved question is no longer whether the premium exists, nor whether a spread captures it, but whether the assumptions bridging simulation to reality hold** — principally skew and execution. Those require real option chain data or measured fills.
