# Test A — Methodology Spec: Does the Variance Risk Premium Exist?

*Implementation spec for Alex. Approved scope per mini-PRD, 14 Aug 2026.*
*You write the code; I review. This document gives you the method and the traps, not the solution.*

---

## 0. Pre-registration (do this first, before writing any code)

Write your falsification criteria down **now**, before you see any results. This is the difference between analysis and rationalisation — once you've seen a chart, you will unconsciously find reasons to believe it.

The strategy's rationale **fails** if any of these hold:

| # | Criterion | Interpretation if triggered |
|---|---|---|
| F1 | Mean VRP not significantly > 0 at the 5% level **after** autocorrelation correction | The premium is not demonstrated in the data |
| F2 | 2015–2025 sub-period mean ≤ 0, or not significant | The premium may have decayed; the long-run average is irrelevant to trading it today |
| F3 | Implied per-trade edge < your measured transaction costs | The premium exists but is not harvestable at your account size |

Note F3 is the one I expect to trigger. Predicting that in advance is itself part of the test — if it triggers, my §5 analysis is corroborated; if it doesn't, I was wrong and you should tell me so.

---

## 1. Data

- **Source:** `yfinance`, tickers `^VIX` and `^GSPC`, daily close, from `1990-01-02` to present.
- **Why 1990:** CBOE back-computed the current VIX methodology to 1990. Earlier data uses the older VXO definition and isn't comparable.
- **Validation before proceeding:** row counts (expect ~9,000 trading days), no duplicate dates, both series share the same trading calendar, no zero or negative prices.

Known gotchas: `yfinance` returns MultiIndex columns when you request multiple tickers; auto-adjustment behaviour has changed across versions, so be explicit about which price column you're using and stay consistent.

---

## 2. Realised volatility

Log returns on the S&P:

```
r_t = ln(P_t / P_{t−1})
```

Forward realised variance over the next `n = 21` trading days (≈ 30 calendar days, matching VIX's horizon):

```
RV²(t→t+n) = (252 / n) × Σ_{i=1..n} r²_{t+i}
```

Annualised realised volatility in percentage points:

```
RV(t→t+n) = 100 × √( RV²(t→t+n) )
```

Three things to get right:

1. **The sum runs from `t+1` to `t+n`, strictly after `t`.** Including `r_t` is look-ahead bias — the single most common bug in this analysis, and it will inflate your result.
2. **Use the zero-mean convention** (don't subtract the sample mean of returns). This is standard in the realised-volatility literature; drift over 21 days is negligible relative to volatility.
3. **The final 21 observations have no forward window.** They must be dropped, never filled or forward-padded.

---

## 3. The VRP series

Compute both framings:

```
VRP_vol(t) = VIX_t − RV(t→t+n)                    # volatility points
VRP_var(t) = VIX_t² − RV²(t→t+n)                  # variance, %² annualised
```

The **variance** framing is the theoretically correct object — VIX approximates a 30-day variance swap rate, so `VIX² − RV²` is literally the payoff to selling one. Use it for the significance testing. The **volatility-point** framing is far more intuitive to interpret, so use it for reporting and charts. Report both; if they disagree in sign or significance, that's a finding worth investigating.

---

## 4. Inference — the part that matters

**The problem.** Consecutive daily VRP observations share 20 of their 21 forward returns. The series is therefore massively autocorrelated, with dependence out to roughly lag 21. A naive `t = mean / (s/√n)` treats ~9,000 overlapping observations as independent and will overstate significance by a large factor. Almost every retail blog post on this topic makes exactly this error.

Do **both** corrections and compare all three numbers side by side:

**(a) Naive t-test on the full daily series.** Compute it deliberately, as the wrong answer — you want to see the size of the error.

**(b) Non-overlapping subsamples.** Take every 21st observation, giving ~420 near-independent observations, then run a standard one-sample t-test. The result depends slightly on which of the 21 possible starting offsets you choose — so **run all 21 offsets and report the range of t-statistics**. If the conclusion flips depending on offset, it isn't robust.

**(c) Newey–West (HAC) standard errors on the full daily series.** Regress the VRP series on a constant and use a heteroskedasticity- and autocorrelation-consistent covariance estimator with `maxlags = 21`. The t-statistic on the intercept is your test of mean ≠ 0. Check sensitivity by re-running at `maxlags = 42`; the estimate shouldn't move much.

`statsmodels`' OLS accepts `cov_type='HAC'` with `cov_kwds={'maxlags': 21}`. Look up the API rather than guessing at it.

**What to expect:** the naive t-statistic will likely be enormous (25+), the corrected ones substantially smaller (single digits to low teens). Both may still reject the null. The lesson isn't which conclusion you reach — it's how much the correction moved it.

---

## 5. Distribution and tails

The mean alone is misleading here, because the whole economic story is in the shape.

Report: mean, median, standard deviation, skewness, excess kurtosis; percentiles at 1/5/25/50/75/95/99; and the **percentage of observations that are positive**.

Then tabulate the **10 worst episodes** with their dates. You should recognise the names — late 2008, February 2018, March 2020. Write one sentence on what happened in each.

**Interpret the shape explicitly.** You should find many small positive values and a few very large negative ones. That negative skew is not a nuisance — it *is* the finding. It's the payoff profile of an insurance seller, and it's the same shape as your bull put spread. The premium is compensation for those tail events, not a free lunch. If you can articulate why that means a high win rate doesn't imply an edge, you've understood the whole project.

---

## 6. Sub-period stability

Split by decade: 1990–99, 2000–09, 2010–19, 2020–present. For each, report mean VRP, % positive, and a corrected confidence interval.

The question you're answering: **is this decaying?** A premium that existed in the 1990s but has been arbitraged away since is of no use to you. Pay particular attention to the most recent period — that's criterion F2.

---

## 7. Translating to your trade economics

Rough first-order reasoning, to be labelled clearly as an order-of-magnitude estimate:

If mean VIX ≈ *V* and mean RV ≈ *R*, the average overpricing is `(V − R)/V` as a fraction of implied volatility. Near-the-money option premium is approximately linear in volatility, so as a crude first cut, sold premium is overpriced by roughly that same fraction. Apply it to a $35 credit to get a theoretical dollar edge per trade, then compare against the $3–$7 of costs in playbook §5.

**Caveats you must state:** this is a first-order approximation; your short strikes are out-of-the-money and sit on the volatility skew, where pricing dynamics differ from the ATM-weighted VIX blend; and index VRP is not identical to the premium in any specific spread. This step is a sanity check on order of magnitude, not a precise edge estimate.

---

## 8. Self-verification checkpoints

Ground truth to check your implementation against. If you're materially off any of these, you have a bug:

| Quantity | Expected range |
|---|---|
| Mean VIX, full sample | ~19–20 |
| Mean realised vol, full sample | ~15–18% |
| Mean VRP (volatility points) | ~+2 to +4 |
| % of observations positive | ~80–88% |
| Skewness of VRP | Strongly negative |

If your numbers are wildly wrong, check in this order: **(1)** window alignment / off-by-one, **(2)** annualisation factor (252, and the `252/n` scaling), **(3)** log vs. arithmetic returns, **(4)** percentage vs. decimal units — VIX is quoted in percentage points, so your RV must be too.

---

## 9. Deliverables

1. `vrp_analysis.py` — clean, commented, reproducible from a fresh environment
2. One or two charts: the VRP time series with zero line, and its distribution
3. `vrp_findings.md` — 400–600 words: what you found, the three inference results side by side, the sub-period picture, and an explicit verdict against F1/F2/F3 from §0

Then send it to me and I'll review both the code and the reasoning — including looking for the bugs listed in §8, so check them yourself first.

---

## 10. Scope reminder

**Out of scope:** backtesting actual spread P/L, single-stock options, skew analysis, any timing signal, anything involving live money. If you find yourself building a "trade when VRP is high" rule, stop — that's a different project with different traps, and we'd need a fresh PRD.
