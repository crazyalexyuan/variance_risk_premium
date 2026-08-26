import pandas as pd
import numpy as np
import yfinance as yf
data = yf.download(['^VIX', '^GSPC'], start='1990-01-01', end='2026-08-15')
datatable = {
'vix': data['Close']['^VIX'],
'spx': data['Close']['^GSPC'],
'returns': np.log(data['Close']['^GSPC'] / data['Close']['^GSPC'].shift(1))
}
df = pd.DataFrame(datatable)
returns_squared = df['returns'].pow(2)
rv_sum = returns_squared.rolling(21).sum().shift(-21)
rv_var = (252/21) * rv_sum
rv = 100 * np.sqrt(rv_var)
df['volatility'] = rv
df['vrp_vol'] = df['vix'] - df['volatility']        
df['vrp_var'] = df['vix']**2 - df['volatility']**2    
df = df.dropna()
print(df.shape)
print(df.head())
print(df.tail())
print(df.describe())
print(df.isna().sum())
print(df['returns'].mean())
print(df['returns'].std())
print(df['returns'].std()*np.sqrt(252))
print(df['volatility'].mean())
print(df['vrp_vol'].median())
print(df['vrp_vol'].mean())
print(df['vrp_vol'].std())
print((df['vrp_vol'] > 0).mean())
print(df['vrp_vol'].plot(figsize=(14,4)))


# %%
from scipy import stats
stats.ttest_1samp(df['vrp_vol'], 0)


# %%
ts = []
for offset in range(21):
    sub = df['vrp_vol'].iloc[offset::21]
    t, p = stats.ttest_1samp(sub, 0)
    ts.append(t)
print(min(ts), max(ts))

# %%
import statsmodels.api as sm
res = sm.OLS(df['vrp_vol'], np.ones(len(df))).fit(cov_type='HAC', cov_kwds={'maxlags': 21})
print(res.summary())

# %%
df['vrp_vol'].describe(percentiles=[.01, .05, .25, .5, .75, .95, .99])
df['vrp_vol'].resample('ME').min().nsmallest(10)
df.loc['2010':'2019', 'vrp_vol']

# %%
# ---- Sub-period stability with HAC intervals ----
periods = [('1990s', '1990', '1999'), ('2000s', '2000', '2009'),
           ('2010s', '2010', '2019'), ('2020s', '2020', '2026')]

rows = []
for name, start, end in periods:
    sub = df.loc[start:end, 'vrp_vol']
    res = sm.OLS(sub, np.ones(len(sub))).fit(cov_type='HAC', cov_kwds={'maxlags': 21})
    ci_low, ci_high = np.asarray(res.conf_int())[0]
    rows.append({
        'period': name,
        'n': len(sub),
        'mean': sub.mean(),
        'std': sub.std(),
        'pct_pos': (sub > 0).mean(),
        'mean_over_std': sub.mean() / sub.std(),
        'ci_low': ci_low,
        'ci_high': ci_high,
    })

subperiods = pd.DataFrame(rows).set_index('period')
print(subperiods.round(3))


# ---- Distribution percentiles ----
print(df['vrp_vol'].describe(percentiles=[.01, .05, .25, .5, .75, .95, .99]).round(3))
print('skew', df['vrp_vol'].skew().round(3), 'kurtosis', df['vrp_vol'].kurtosis().round(3))


# ---- Ten worst episodes, with context ----
monthly_worst_dates = df.groupby(df.index.to_period('M'))['vrp_vol'].idxmin()
worst = df.loc[monthly_worst_dates, ['vix', 'volatility', 'vrp_vol']].nsmallest(10, 'vrp_vol')
print(worst.round(2))


# ---- Bootstrap CI (addresses the non-normality limitation) ----
indep = df['vrp_vol'].iloc[::21].values          # near-independent sample
rng = np.random.default_rng(42)
boot = rng.choice(indep, size=(10000, len(indep)), replace=True).mean(axis=1)
print('bootstrap 95% CI:', np.percentile(boot, [2.5, 97.5]).round(3))


# %%
bins = [0, 15, 20, 25, 30, 100]
df['vix_bucket'] = pd.cut(df['vix'], bins)
summary = df.groupby('vix_bucket', observed=True)['vrp_vol'].agg(
    n='count', mean='mean', median='median', std='std',
    pct_pos=lambda x: (x > 0).mean(), worst='min')
summary['mean_ratio'] = df.groupby('vix_bucket', observed=True).apply(
    lambda g: (g['vrp_vol'] / g['vix']).mean(), include_groups=False)
print(summary.round(3))

# %%

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm, ttest_1samp
import statsmodels.api as sm

START, END = '1990-01-01', '2026-08-15'
N_DAYS = 21                  # trading days held; matches the VRP window from Test A
T = N_DAYS / 252             # time to expiry in years
TARGET_DELTA = 0.30          # short strike delta
WIDTH = 1.0                  # $ distance between strikes (SPY strikes are $1 apart)
CONTRACT = 100               # shares per contract
COST_CASES = [2.0, 3.50, 6.0]   # $ per trade: commission + slippage
HAC_LAGS = N_DAYS            # autocorrelation extends as far as the holding period



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



d1_target = -norm.ppf(TARGET_DELTA)     

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



credit = pd.Series(bs_put(S, K1, T, r, sigma) - bs_put(S, K2, T, r, sigma), index=df.index)


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

# %%
CONFIGS = [('no filter', 0, 999), ('VIX <= 20', 0, 20), ('VIX <= 25', 0, 25),
           ('VIX <= 30', 0, 30), ('VIX <= 35', 0, 35), ('VIX 15-30', 15, 30),
           ('VIX >= 20', 20, 999), ('VIX >= 25', 25, 999), ('VIX >= 30', 30, 999)]

def sweep(tr, cost=3.50):
    out = []
    for name, lo, hi in CONFIGS:
        sel = tr[(tr['vix'] >= lo) & (tr['vix'] <= hi)]
        if len(sel) < 200:
            continue
        pnl = sel['pnl_gross'] - cost
        m, t, _, _ = hac(pnl)
        out.append({'filter': name, 'n': len(sel),
                    'share': len(sel) / len(tr),
                    'mean': m, 'hac_t': t,
                    'sub_t_min': min(subsample_t(pnl)),
                    'win%': (pnl > 0).mean() * 100,
                    'annual_est': 12 * m * (len(sel) / len(tr))})
    return pd.DataFrame(out).set_index('filter').round(2)

print("FULL SAMPLE\n", sweep(trades))
print("\nOUT-OF-SAMPLE HALF\n", sweep(oos))


