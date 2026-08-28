https://doi.org/10.5281/zenodo.22114646
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

Files are numbered in reading order. Each study has a pre-registration document written before the data was examined, and a results document reporting against it.

| File | Description |
|---|---|
| `VRP_working_paper.pdf` | The paper (8pp) |
| `VRP_working_paper.tex` | LaTeX source |
| **Study 1 — measuring the premium** | |
| `01_preregistration_vrp.md` | Methodology and falsification criteria, written before analysis |
| `measure_vrp.py` | Analysis code |
| `01_results_vrp.md` | Full results and verdicts against criteria F1–F3 |
| **Study 2 — simulated bull put spread** | |
| `02_preregistration_spread.md` | Methodology and falsification criteria, written before analysis |
| `simulate_spread.py` | Simulation code |
| `02_results_spread.md` | Full results and verdicts against criteria G1–G3 |
| `data/vrp_raw.csv` | Frozen data snapshot, so published figures reproduce exactly |

### A note on the pre-registration files

The two `*_preregistration_*.md` documents are the record of what was committed to before any data was examined, and their contents are preserved **byte-identical** to how they were written. Files elsewhere in this repository were renamed in a later tidying pass; the pre-registration documents were deliberately excluded from that pass, so their internal references still use the original filenames (`vrp_analysis.py`, `vrp_findings.md`). Those refer to what are now `measure_vrp.py` and `01_results_vrp.md`. The alternative — editing them for consistency — would have compromised the only thing that makes a pre-registration meaningful.

## Reproducing

```bash
pip install -r requirements.txt
python measure_vrp.py        # uses the committed data snapshot
python simulate_spread.py
```

`measure_vrp.py` runs against `data/vrp_raw.csv`, a frozen snapshot, so the figures reproduce those in the paper exactly. Pass `--refresh` to pull current data from Yahoo Finance instead (`^VIX`, `^GSPC`, `^IRX`); results will then extend beyond the paper's sample and will not match it.

## Method

Realised volatility over the 21 trading days *following* each date is computed from log returns as `RV = 100 × √((252/21) × Σr²)`, and the premium is `VIX − RV`. Because consecutive daily observations share 20 of their 21 forward returns, inference uses three corrections: non-overlapping subsampling across all 21 starting offsets, Newey–West HAC standard errors with `maxlags=21`, and a distribution-free bootstrap.

Falsification criteria were committed to in writing before the data was examined, and are reported against explicitly.

## Limitations

The study does not model volatility skew (both legs are priced at VIX rather than at each strike's own implied volatility) and assumes fills at theoretical prices. Both require option chain data rather than index data. Positions overlap, so only per-trade figures are meaningful. A material share of the simulated return appears to be equity beta rather than volatility premium — every losing year coincides with an equity bear market.

## Status

Working paper. Not peer-reviewed. Educational and research use only; nothing here is financial advice.

## Tools

Analysis code was written by the author. Methodology design, statistical review and manuscript preparation were carried out in collaboration with an AI assistant (Claude, Anthropic). All results were computed and verified by the author.

## Licence

Code released under the MIT Licence. The paper is released under CC BY 4.0.
