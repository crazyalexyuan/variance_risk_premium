# Test A2 — Simulated Bull Put Spread: Reference

*Scope agreed August 2026: SPY-scaled, $1-wide, −0.30 delta short strike, 21-day hold to expiry, 1990–2026.*
*This is an approximation, not a backtest. See Limitations before believing any number it produces.*

---

## 0. Pre-registration

Before running anything, commit to these:

| # | Criterion | If triggered |
|---|---|---|
| G1 | Mean gross P&L per trade ≤ 0 after HAC correction | The spread does not capture the premium at all — strategy rationale fails outright |
| G2 | Mean **net** P&L (after $3.50 costs) ≤ 0 | Premium is captured but consumed by costs — confirms F3 triggers |
| G3 | Worst trade exceeds theoretical max loss | Bug, not a finding — stop and debug |

Also commit now: **the unfiltered result is the headline.** The VIX 15–30 filter was chosen after inspecting the bucket table, so any result using it is in-sample and must be reported as secondary.

---

## 1. Inputs per date *t*

| Symbol | Value | Source |
|---|---|---|
| `S` | SPX close ÷ 10 | SPY proxy |
| `σ` | VIX ÷ 100 | Implied vol for both legs |
| `T` | 21 / 252 | Time to expiry in years |
| `r` | `^IRX` ÷ 100 | 13-week T-bill, annualised |

Add `^IRX` to your `yfinance` download. Its history is shorter than VIX's in places — forward-fill small gaps, and note how many dates you lose.

---

## 2. Finding the −0.30 delta short strike

Black–Scholes put delta is `−N(−d₁)`. Setting that to −0.30:

```
N(−d₁) = 0.30   →   d₁ = −Φ⁻¹(0.30) = 0.5244
```

Invert the d₁ definition to solve for the strike:

```
K₁ = S · exp( (r + σ²/2)·T − d₁·σ√T )
```

Then round `K₁` to the nearest whole dollar (SPY strikes are $1 apart) and set `K₂ = K₁ − 1`.

Sanity check: `K₁` should land roughly **2–3% below spot** in normal conditions, further out when VIX is high.

---

## 3. Pricing both legs

Standard Black–Scholes put, no dividends:

```
d₁ = [ ln(S/K) + (r + σ²/2)·T ] / (σ√T)
d₂ = d₁ − σ√T

P  = K·e^(−rT)·N(−d₂) − S·N(−d₁)
```

Use `scipy.stats.norm.cdf` for N and `norm.ppf` for Φ⁻¹. Write it as a function taking `(S, K, T, r, sigma)` so you can test it in isolation.

**Credit = P(K₁) − P(K₂)**, expected to land around **$0.30–0.40** per share.

*Test your pricer before using it.* A put with `S=100, K=100, T=0.0833, r=0.04, σ=0.20` should come out near **$2.15**. If it doesn't, fix that before going further.

---

## 4. Payoff at expiry

`S_T` = SPX ÷ 10, twenty-one trading days later.

```
spread_value_at_expiry = max(K₁ − S_T, 0) − max(K₂ − S_T, 0)     # bounded [0, 1]
pnl_per_share          = credit − spread_value_at_expiry
pnl_dollars            = pnl_per_share × 100
```

---

## 5. Costs

Subtract per trade, then test sensitivity:

| Component | Base case |
|---|---|
| Commission (open; no close if expires worthless) | $2.00 |
| Slippage (half the bid–ask on entry) | $1.50 |
| **Total** | **$3.50** |

Report results at $2, $3.50 and $6 so the conclusion's sensitivity to cost assumptions is visible.

---

## 6. Validation — do this before interpreting anything

| Check | Expected |
|---|---|
| Credit distribution | Mostly $0.30–0.40 |
| `pnl_dollars` maximum | ≈ credit × 100, never more |
| `pnl_dollars` minimum | ≈ −(100 − credit×100), never worse |
| **Any P&L outside those bounds** | **Bug — stop and debug** |
| Win rate | ~70–75% |
| Strike distance from spot | 2–3% typical |

That bounds check is the important one. A bull put spread's P&L is mathematically confined to `[−(100−credit), +credit]`. Anything outside means a misaligned expiry lookup or a units error, and it's the single most likely bug in this build.

---

## 7. Inference

Daily entries with 21-day holds overlap exactly as the VRP series did. Reuse the same machinery: HAC standard errors with `maxlags=21`, plus non-overlapping subsamples across all 21 offsets as the assumption-free cross-check. Report gross and net separately.

---

## 8. Limitations — state these in any writeup

1. **Skew is ignored.** Both legs are priced at VIX, but real out-of-the-money puts trade at different implied vols. This is the largest error source and it hits precisely the strikes being traded. Direction of bias is unclear.
2. **No management.** Real playbook exits at 50% profit or 21 DTE; this holds to expiry, which is a different — and riskier — strategy.
3. **Overlapping positions.** 21 concurrent trades is unfundable at £100 and makes observations statistically dependent.
4. **No dividends.** SPY yields ~1.5%; over 21 days the effect is small but nonzero.
5. **Rounding to whole-dollar strikes** shifts the true delta away from exactly 0.30.
6. **Black–Scholes assumes lognormal returns.** Equity returns have fat tails, so tail outcomes are understated.
7. **The VIX filter, if applied, was selected in-sample.**

---

## 9. What this can and cannot conclude

**Can:** whether a defined-risk spread mechanically captures a positive share of the variance risk premium, and roughly how much of that survives realistic costs.

**Cannot:** settle F3. The skew assumption alone could move the answer by more than the cost figures being tested. Only real option chain data — or Test B's measured fills — resolves it.
