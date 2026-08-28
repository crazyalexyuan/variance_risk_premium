"""
Test A2 — Simulated bull put spread on a SPY-scaled S&P 500.

Approximation, not a backtest. Options are priced with Black-Scholes using VIX as the
implied volatility for BOTH legs, which ignores volatility skew entirely. See
02_preregistration_spread.md §8 before believing any number this produces.

Design: every trading day, open a $1-wide bull put spread with the short strike at
~0.30 delta and 21 trading days to expiry. Hold to expiry. Compute P&L from where the
index actually finished.
"""

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm, ttest_1samp
import statsmodels.api as sm

# ----------------------------------------------------------------------------------
# Parameters. Kept at the top so every assumption is visible and changeable in one
# place -- burying constants inside the logic is how backtests quietly become
# unreproducible.
# ----------------------------------------------------------------------------------
START, END = '1990-01-01', '2026-08-15'
N_DAYS = 21                  # trading days held; matches the VRP window from Test A
T = N_DAYS / 252             # time to expiry in years
TARGET_DELTA = 0.30          # short strike delta
WIDTH = 1.0                  # $ distance between strikes (SPY strikes are $1 apart)
CONTRACT = 100               # shares per contract
COST_CASES = [2.0, 3.50, 6.0]   # $ per trade: commission + slippage
HAC_LAGS = N_DAYS            # autocorrelation extends as far as the holding period


# ----------------------------------------------------------------------------------
# 1. Data
# ----------------------------------------------------------------------------------
raw = yf.download(['^VIX', '^GSPC', '^IRX'], start=START, end=END,
                  auto_adjust=False, progress=False)

# yfinance returns MultiIndex columns for multiple tickers: level 0 is the field,
# level 1 is the ticker. Taking ['Close'] collapses to a ticker-columned frame.
close = raw['Close']

df = pd.DataFrame({
    'vix': close['^VIX'],
    'spx': close['^GSPC'],
    'irx': close['^IRX'],
})

# Rates move slowly and gaps are reporting artefacts rather than real missing days,
# so forward-filling is safe here. Doing the same to VIX or SPX would NOT be safe --
# it would invent market data -- so those are dropped instead.
n_before = len(df)
df['irx'] = df['irx'].ffill()
df = df.dropna()
print(f"rows: {len(df)} (dropped {n_before - len(df)} incomplete)")
print(f"range: {df.index.min().date()} to {df.index.max().date()}")


# ----------------------------------------------------------------------------------
# 2. Black-Scholes put pricer
#
# Written as a standalone function on plain arrays rather than inline on pandas
# Series. Two reasons: it can be unit-tested in isolation (see below), and mixing
# Series with numpy output risks silent index-alignment bugs.
# ----------------------------------------------------------------------------------
def bs_put(S, K, T, r, sigma):
    """Black-Scholes European put price. No dividends."""
    S = np.asarray(S, dtype=float)
    K = np.asarray(K, dtype=float)
    r = np.asarray(r, dtype=float)
    sigma = np.asarray(sigma, dtype=float)
    sqrtT = np.sqrt(T)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrtT)
    d2 = d1 - sigma * sqrtT
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


# Unit tests. If these fail, nothing downstream is meaningful, so fail loudly here
# rather than producing plausible-looking garbage 200 lines later.
_atm = bs_put(100, 100, 0.0833, 0.04, 0.20)
assert abs(_atm - 2.136) < 0.01, f"ATM put should be ~2.136, got {_atm}"
assert bs_put(100, 50, 0.0833, 0.04, 0.20) < 0.01, "deep OTM put should be ~0"
assert bs_put(100, 100, 0.0833, 0.04, 0.40) > 1.8 * _atm, "doubling vol should ~double ATM price"
print(f"pricer OK (ATM reference {_atm:.4f})")


# ----------------------------------------------------------------------------------
# 3. Strike selection
#
# Put delta = -N(-d1). Setting that to -0.30 gives N(-d1) = 0.30, so -d1 = Phi^-1(0.30)
# and therefore d1 = -Phi^-1(0.30) = +0.5244. Inverting the definition of d1 for K:
#
#     d1 = [ln(S/K) + (r + s^2/2)T] / (s*sqrt(T))
#  => ln(K/S) = (r + s^2/2)T - d1*s*sqrt(T)
#  => K = S * exp( (r + s^2/2)T - d1*s*sqrt(T) )
# ----------------------------------------------------------------------------------
d1_target = -norm.ppf(TARGET_DELTA)     # +0.5244

S = df['spx'] / 10                       # SPY proxy: index / 10
sigma = df['vix'] / 100                  # VIX is quoted in percentage points
r = df['irx'] / 100

K1_raw = S * np.exp((r + 0.5 * sigma ** 2) * T - d1_target * sigma * np.sqrt(T))
K1 = np.round(K1_raw)                    # real SPY strikes are whole dollars
K2 = K1 - WIDTH

# Rounding to a real strike moves the true delta away from exactly 0.30. Worth
# knowing how far -- if this is large the "0.30 delta" label is misleading.
d1_actual = (np.log(S / K1) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
delta_actual = -norm.cdf(-d1_actual)


# ----------------------------------------------------------------------------------
# 4. Credit and expiry payoff
# ----------------------------------------------------------------------------------
credit = pd.Series(bs_put(S, K1, T, r, sigma) - bs_put(S, K2, T, r, sigma), index=df.index)

# shift(-N_DAYS) pulls the value from N_DAYS rows LATER into the current row, so at
# date t this is the index level at expiry. The last N_DAYS rows become NaN because
# their expiry hasn't happened -- same forward-window logic as the VRP series.
S_T = S.shift(-N_DAYS)

# At expiry the spread is worth the intrinsic value of the short put minus that of
# the long put. Bounded between 0 (both expire worthless) and WIDTH (both in the money).
value_at_expiry = np.maximum(K1 - S_T, 0) - np.maximum(K2 - S_T, 0)

pnl_gross = (credit - value_at_expiry) * CONTRACT

trades = pd.DataFrame({
    'vix': df['vix'], 'S': S, 'K1': K1, 'K2': K2,
    'delta': delta_actual, 'credit': credit, 'S_T': S_T,
    'pnl_gross': pnl_gross,
}).dropna()


# ----------------------------------------------------------------------------------
# 5. Validation. Run BEFORE interpreting anything.
#
# A bull put spread's P&L is mathematically confined to [-(WIDTH*100 - credit), +credit].
# Any value outside that range means a bug -- most likely a misaligned expiry lookup
# or a units error -- not an interesting finding.
# ----------------------------------------------------------------------------------
max_profit = trades['credit'] * CONTRACT
max_loss = -(WIDTH * CONTRACT - trades['credit'] * CONTRACT)
violations = ((trades['pnl_gross'] > max_profit + 1e-6) |
              (trades['pnl_gross'] < max_loss - 1e-6)).sum()

print("\n--- validation ---")
print(f"trades: {len(trades)}")
print(f"credit ($/share): mean {trades['credit'].mean():.3f}, "
      f"5th {trades['credit'].quantile(.05):.3f}, 95th {trades['credit'].quantile(.95):.3f}")
print(f"actual short delta: mean {trades['delta'].mean():.3f} (target -{TARGET_DELTA})")
print(f"strike distance below spot: mean {(1 - trades['K1']/trades['S']).mean()*100:.2f}%")
print(f"P&L range: {trades['pnl_gross'].min():.2f} to {trades['pnl_gross'].max():.2f}")
print(f"BOUNDS VIOLATIONS: {violations}  <-- must be 0")


# ----------------------------------------------------------------------------------
# 6. Inference helpers
#
# Daily entries with 21-day holds overlap, exactly as the VRP series did, so ordinary
# standard errors are invalid for the same reason. Reuse both corrections.
# ----------------------------------------------------------------------------------
def hac(x, lags=HAC_LAGS):
    """Mean with Newey-West corrected t-stat and 95% CI."""
    x = pd.Series(x).dropna()
    res = sm.OLS(x.values, np.ones(len(x))).fit(cov_type='HAC', cov_kwds={'maxlags': lags})
    lo, hi = np.asarray(res.conf_int())[0]
    return float(np.asarray(res.params)[0]), float(np.asarray(res.tvalues)[0]), lo, hi


def subsample_t(x, step=N_DAYS):
    """t-stats from all non-overlapping subsamples -- assumption-free cross-check."""
    x = pd.Series(x).dropna()
    return [float(ttest_1samp(x.iloc[o::step], 0).statistic) for o in range(step)]


def summarise(pnl, label):
    m, t, lo, hi = hac(pnl)
    ts = subsample_t(pnl)
    print(f"\n{label}")
    print(f"  n            {len(pnl)}")
    print(f"  mean         ${m:.2f}   HAC t={t:.2f}  95% CI [${lo:.2f}, ${hi:.2f}]")
    print(f"  subsample t  {min(ts):.2f} to {max(ts):.2f}")
    print(f"  median       ${pnl.median():.2f}")
    print(f"  win rate     {(pnl > 0).mean()*100:.1f}%")
    print(f"  std          ${pnl.std():.2f}")
    print(f"  worst        ${pnl.min():.2f}")
    print(f"  total        ${pnl.sum():,.0f}")


# ----------------------------------------------------------------------------------
# 7. Results
# ----------------------------------------------------------------------------------
print("\n=== HEADLINE: all trades, unfiltered ===")
summarise(trades['pnl_gross'], "GROSS (no costs)")
for c in COST_CASES:
    summarise(trades['pnl_gross'] - c, f"NET of ${c:.2f} costs")

# Secondary. The 15-30 VIX band was chosen AFTER inspecting the bucket table in
# Test A, so this is in-sample selection and cannot be treated as a validated rule.
print("\n=== SECONDARY (IN-SAMPLE FILTER — NOT A VALIDATED RULE) ===")
band = trades[(trades['vix'] >= 15) & (trades['vix'] <= 30)]
summarise(band['pnl_gross'] - 3.50, "VIX 15-30, net of $3.50")

# Out-of-sample check on that filter: choose on the first half, evaluate on the second.
# If the filter only works in the half used to find it, it isn't real.
mid = trades.index[len(trades) // 2]
oos = trades[trades.index > mid]
oos_band = oos[(oos['vix'] >= 15) & (oos['vix'] <= 30)]
print("\n=== OUT-OF-SAMPLE HALF (2008 onwards) ===")
summarise(oos['pnl_gross'] - 3.50, "all trades, net of $3.50")
summarise(oos_band['pnl_gross'] - 3.50, "VIX 15-30, net of $3.50")

# Yearly breakdown -- shows whether results come from a few extreme years.
print("\n=== BY YEAR (net of $3.50) ===")
yearly = (trades['pnl_gross'] - 3.50).groupby(trades.index.year).agg(
    n='count', mean='mean', total='sum', worst='min')
print(yearly.round(2).to_string())
