 DOI: 10.5281/zenodo.22114647
# The Variance Risk Premium and a Defined-Risk Option Strategy

Evidence from S&P 500 options, 1990–2026.

**[📄 Read the paper (PDF)](VRP_working_paper.pdf)**

---

## Summary

This study tests whether the variance risk premium — the tendency for option-implied volatility to exceed subsequently realised volatility — exists, persists, and is captured by a defined-risk option strategy.

| Question | Finding |
|---|---|
| Does the premium exist? | Yes. **+4.10 volatility points**, HAC 95% CI [3.57, 4.62], *z* = 15.3 |
| Has it decayed since 1990? | No. Significant in every decade; 2020s mean 3.79 |
| Is it a market inefficiency? | No. Skewness −3.65 — it is compensation for crash risk |
| Does a spread capture it? | Yes in simulation. **$8.35 per trade** net of $3.50 costs |
| Does timing by VIX help? | No. **All nine filters tested underperformed** unconditional entry |
| Is it tradeable after real costs? | Not established. Volatility skew and execution untested |

Two methodological points the study emphasises:

- **Overlapping windows matter enormously.** A naive *t*-test returns 59.2; correctly handled, the same data gives 12–15. The naive method overstates the evidence by roughly √21, the overlap length.
- **A high win rate is not an edge.** The simulated strategy won 82.2% of trades, but the breakeven rate implied by its payoff ratio is 69.7%. Only the 12.5-point excess is informative.

## Contents

| File | Description |
|---|---|
| `VRP_working_paper.pdf` | The paper (8pp) |
| `VRP_working_paper.tex` | LaTeX source |
| `vrp_analysis.py` | Study 1: measuring the premium from VIX and S&P 500 data |
| `test_a2_backtest.py` | Study 2: simulated bull put spread |
| `test_a_vrp_spec.md` | Methodology spec, Study 1 — includes pre-registered falsification criteria |
| `test_a2_spec.md` | Methodology spec, Study 2 — same |
| `vrp_findings.md` | Full results, Study 1 |
| `test_a2_findings.md` | Full results, Study 2 |

## Reproducing

```bash
pip install -r requirements.txt
python vrp_analysis.py
python test_a2_backtest.py
```

Data is pulled from Yahoo Finance at runtime (`^VIX`, `^GSPC`, `^IRX`), so results will extend as new data becomes available and will not match the paper's figures exactly.

## Method

Realised volatility over the 21 trading days *following* each date is computed from log returns as `RV = 100 × √((252/21) × Σr²)`, and the premium is `VIX − RV`. Because consecutive daily observations share 20 of their 21 forward returns, inference uses three corrections: non-overlapping subsampling across all 21 starting offsets, Newey–West HAC standard errors with `maxlags=21`, and a distribution-free bootstrap.

Falsification criteria were committed to in writing before the data was examined, and are reported against explicitly. They are preserved unedited in the spec files.

## Limitations

The study does not model volatility skew (both legs are priced at VIX rather than at each strike's own implied volatility) and assumes fills at theoretical prices. Both require option chain data rather than index data. Positions overlap, so only per-trade figures are meaningful. A material share of the simulated return appears to be equity beta rather than volatility premium — every losing year coincides with an equity bear market.

## Status

Working paper. Not peer-reviewed. Educational and research use only; nothing here is financial advice.

## Tools

Analysis code was written by the author. Methodology design, statistical review and manuscript preparation were carried out in collaboration with an AI assistant (Claude, Anthropic). All results were computed and verified by the author.

## Licence

Code released under the MIT Licence. The paper is released under CC BY 4.0.
