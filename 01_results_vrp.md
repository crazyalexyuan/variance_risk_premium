# Test A — Findings: Does the Variance Risk Premium Exist?

*Analysis: Alex, August 2026.*
*Falsification criteria pre-registered in `01_preregistration_vrp.md` §0 before analysis began.*

---

## Method

Daily closes for `^VIX` and `^GSPC`, 2 January 1990 to 14 August 2026, from Yahoo Finance (n = 9,178 after cleaning). For each date *t*, realised volatility over the **following** 21 trading days was computed from log returns as `RV = 100 × √((252/21) × Σr²)`, aligned strictly to returns after *t*. The variance risk premium is `VRP = VIX_t − RV(t→t+21)`, in annualised volatility points.

Window alignment was verified by manually reconstructing a single observation and comparing it against the vectorised column. This check caught one genuine error during development — a backward-looking window that would have produced a plausible but meaningless result.

---

## Results

**Headline:** mean VRP = **+4.10 volatility points**, median +4.71, standard deviation 6.63. The premium was positive in **85.8%** of observations. Mean VIX over the period was 19.44 against mean subsequent realised volatility of 15.36.

### Inference

Daily observations of a 21-day forward window overlap heavily, so ordinary standard errors are invalid. Four approaches:

| Method | t / z | 95% CI | Notes |
|---|---|---|---|
| Naive one-sample t-test | **59.2** | — | Invalid — assumes independence |
| Non-overlapping subsamples (21 offsets) | **12.0 – 13.8** | — | ~437 obs each; assumption-free |
| Newey–West HAC (maxlags = 21) | **15.3** | **[3.57, 4.62]** | Full sample, corrected SE |
| Bootstrap (10,000 draws, non-overlapping sample) | — | **[3.31, 4.55]** | No distributional assumption |

The naive method overstated the evidence by roughly a factor of four — close to the √21 ≈ 4.6 predicted from the overlap structure. The regression's Durbin–Watson statistic of **0.094** (2.0 indicates no autocorrelation) independently confirms severe serial dependence. All three valid methods agree closely, and the bootstrap interval — which assumes nothing about the shape of the distribution — brackets the HAC interval. The conclusion is not an artefact of any single method's assumptions.

### Distribution

| Statistic | Value |
|---|---|
| Minimum | −71.96 |
| 1st percentile | −19.95 |
| 5th percentile | −4.87 |
| 25th percentile | +2.21 |
| Median | +4.71 |
| 75th percentile | +7.23 |
| 95th percentile | +11.71 |
| 99th percentile | +16.65 |
| Maximum | +30.77 |
| Skewness | −3.65 |
| Excess kurtosis | 29.27 |

The middle 50% of observations lies between **+2.21 and +7.23** — reliably, unremarkably positive. The asymmetry is entirely in the tails: the worst single observation (−71.96) is more than twice the magnitude of the best (+30.77), and the 1st percentile (−19.95) is worse than the 99th percentile (+16.65) is good.

This is the payoff profile of an insurance seller: a steady, modest premium in the overwhelming majority of periods, punctuated by rare losses several times larger than any gain. It is the economic content of the result — the premium is compensation for bearing those episodes, not a market inefficiency.

### Ten worst episodes

Monthly minima, six of ten shown (output truncated):

| Date | VIX | Realised vol | VRP | Event |
|---|---|---|---|---|
| 2020-02-20 | 15.56 | 87.52 | **−71.96** | COVID crash begins |
| 2020-03-04 | 31.99 | 93.43 | −61.44 | COVID crash |
| 2008-09-16 | 30.30 | 80.21 | −49.91 | Lehman Brothers collapse |
| 2008-11-04 | 47.73 | 74.80 | −27.07 | Post-Lehman crisis |
| 2025-04-02 | 21.51 | 47.90 | −26.39 | Tariff shock |
| 2011-08-01 | 23.66 | 48.43 | −24.77 | US debt downgrade |

**The 20 February 2020 row is the single most instructive number in this analysis.** VIX stood at 15.56 — an unremarkable, complacent level implying a calm month ahead. Realised volatility over the following 21 days was 87.52. The market's own forecast was wrong by a factor of five, with no advance warning priced in whatsoever. Any position short volatility without a defined floor faced an unbounded loss from a starting point that looked entirely benign.

### Sub-period stability

| Period | n | Mean | Std | % positive | Mean/Std | HAC 95% CI |
|---|---|---|---|---|---|---|
| 1990s | 2,527 | 5.45 | 4.31 | 92.5% | **1.26** | [4.84, 6.06] |
| 2000s | 2,515 | 3.35 | 7.08 | 81.5% | 0.47 | [2.23, 4.48] |
| 2010s | 2,516 | 3.68 | 5.44 | 84.3% | 0.68 | [2.92, 4.44] |
| 2020s | 1,620 | 3.79 | 9.61 | 84.4% | **0.39** | [1.97, 5.60] |

Every decade's interval excludes zero. The premium has **not** decayed in magnitude — the 2020s mean exceeds both the 2000s and 2010s.

Two observations qualify that. First, the 1990s interval [4.84, 6.06] barely fails to overlap the 2000s [2.23, 4.48], suggesting a genuine one-time downward level shift after the 1990s rather than continuous decay; the three subsequent decades are statistically indistinguishable from one another. Second, dispersion has more than doubled since the 1990s, so the ratio of premium to variability has fallen by roughly two-thirds (1.26 → 0.39). The 2020s confidence interval is about three times wider than the full-sample interval. The premium is the same size; the risk borne to collect it, and the uncertainty about its magnitude, are both substantially greater.

*(Note: comparing confidence intervals for overlap is an informal heuristic, not a formal test of difference between periods.)*

---

## Verdicts against pre-registered criteria

**F1 — "Mean VRP not significantly > 0 after autocorrelation correction." DOES NOT TRIGGER.** Mean +4.10, HAC CI [3.57, 4.62], bootstrap CI [3.31, 4.55], z = 15.3. The premium is real and robustly measured under three independent inference methods.

**F2 — "2015–2025 sub-period mean ≤ 0 or not significant." DOES NOT TRIGGER.** The 2020s mean of 3.79 has a HAC interval of [1.97, 5.60], excluding zero. The premium persists in the most recent period, including COVID.

**F3 — "Implied per-trade edge < measured transaction costs." UNRESOLVED.** Implied volatility exceeds realised by ~21% of its level (4.08/19.44). Applied naively to a $35 credit that suggests ~$7 of gross edge, against $3–7 of round-trip costs. But three corrections push the true figure lower — VIX is constructed from the full strike range and so sits structurally above at-the-money implied volatility; a $1-wide spread's two legs have nearly offsetting vega, so it harvests only a fraction of the premium a naked short put would; and the volatility-to-P&L mapping is nonlinear. One correction pushes the other way: out-of-the-money puts, where the strategy sells, typically carry a richer premium than at-the-money options. The plausible range of $2–7 straddles the cost line. **This criterion cannot be settled with index data and requires Test B (measured execution costs).**

---

## Limitations

1. **This is not a backtest.** No options were priced or traded in this analysis. It establishes that the *source* of the edge exists; it does not demonstrate that the bull put spread captures it.
2. **VIX is not the implied volatility of the options actually traded.** It is a variance-swap-style construction spanning many strikes, while the strategy sells specific out-of-the-money puts on the skew.
3. ~~Normality is violated~~ **Addressed.** Skew −3.65 and excess kurtosis 29.27 do violate normality, but the bootstrap interval [3.31, 4.55] — which makes no distributional assumption — agrees closely with the HAC interval [3.57, 4.62]. The conclusion does not depend on normality.
4. **Single data source, unaudited.** Yahoo Finance data has not been cross-checked against CBOE's published VIX history.
5. **Sub-period boundaries are arbitrary** calendar decades, not volatility regimes.
6. **The premium is not a forecast.** February 2020 demonstrates that the historical average carries no information about any individual period.

---

## Conclusion

The variance risk premium exists, is large, is statistically robust across four inference methods, and has not decayed in magnitude over 36 years. It is compensation for bearing crash risk rather than a market inefficiency — a conclusion the −3.65 skew and the February 2020 episode make unambiguous.

Two qualifications matter more than the headline. The risk-adjusted premium has deteriorated markedly since the 1990s: the same expected return now carries roughly two and a half times the variability. And the premium's existence says nothing about its *harvestability* at a £100–500 account through $1-wide defined-risk spreads after commissions and slippage. The prior estimate of $1–2 edge per trade recorded in the playbook appears too pessimistic, but the honest range remains wide enough to include both "worth trading" and "not worth trading."

**Test A succeeded in what it set out to do: it established that the strategy's premise is sound, and identified precisely which question remains open.** Test B — measuring actual execution costs against real fills — is required to answer it.
