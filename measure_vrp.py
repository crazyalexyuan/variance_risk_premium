"""
Study 1 — Measuring the variance risk premium in S&P 500 index options.

Computes VRP = VIX_t - RV(t -> t+21) from daily index data, 1990-2026, and tests
whether its mean exceeds zero under three inference methods that account for the
overlapping-window autocorrelation inherent in the construction.

Methodology and pre-registered falsification criteria: 01_preregistration_vrp.md
Results and verdicts:                                  01_results_vrp.md

Usage
-----
    python measure_vrp.py

On first run this downloads from Yahoo Finance and writes data/vrp_raw.csv.
Subsequent runs load that snapshot, so results are reproducible and match the
paper. Delete the file (or pass --refresh) to pull current data instead.
"""

import argparse
import os

import numpy as np
import pandas as pd
import statsmodels.api as sm
import yfinance as yf
from scipy import stats

START = "1990-01-01"
END = "2026-08-15"
WINDOW = 21          # trading days; ~30 calendar days, matching the VIX horizon
TRADING_DAYS = 252
HAC_LAGS = WINDOW    # dependence extends as far as the overlap
SNAPSHOT = os.path.join("data", "vrp_raw.csv")


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def load_raw(refresh: bool = False) -> pd.DataFrame:
    """Return daily VIX and S&P 500 closes, preferring the committed snapshot.

    Pulling live data makes results drift as new observations arrive, which
    means published figures can never be reproduced exactly. Caching a snapshot
    fixes that without preventing anyone from re-running on current data.
    """
    if os.path.exists(SNAPSHOT) and not refresh:
        raw = pd.read_csv(SNAPSHOT, index_col=0, parse_dates=True)
        print(f"loaded snapshot: {SNAPSHOT}")
        return raw

    data = yf.download(["^VIX", "^GSPC"], start=START, end=END, progress=False)
    raw = pd.DataFrame({
        "vix": data["Close"]["^VIX"],
        "spx": data["Close"]["^GSPC"],
    })
    os.makedirs(os.path.dirname(SNAPSHOT), exist_ok=True)
    raw.to_csv(SNAPSHOT)
    print(f"downloaded and cached: {SNAPSHOT}")
    return raw


def build_vrp(raw: pd.DataFrame) -> pd.DataFrame:
    """Construct the VRP series from raw closes.

    Realised volatility is computed over the WINDOW days *following* each date.
    The shift(-WINDOW) is what enforces that: without it the window looks
    backwards, which produces a plausible but meaningless result. This exact
    error occurred during development and was caught by manually reconstructing
    a single observation against the vectorised column.
    """
    df = raw.copy()
    df["returns"] = np.log(df["spx"] / df["spx"].shift(1))

    # Zero-mean convention, standard in the realised-volatility literature:
    # drift over 21 days is negligible relative to volatility.
    fwd_sum_sq = df["returns"].pow(2).rolling(WINDOW).sum().shift(-WINDOW)
    df["volatility"] = 100 * np.sqrt((TRADING_DAYS / WINDOW) * fwd_sum_sq)

    df["vrp_vol"] = df["vix"] - df["volatility"]          # volatility points
    df["vrp_var"] = df["vix"] ** 2 - df["volatility"] ** 2  # variance framing

    # The final WINDOW rows have no forward window and must be dropped, never
    # filled -- filling would invent market data.
    return df.dropna()


# ---------------------------------------------------------------------------
# Inference helpers
# ---------------------------------------------------------------------------

def hac_fit(series: pd.Series, lags: int = HAC_LAGS):
    """Mean of `series` with Newey-West HAC standard errors."""
    return sm.OLS(series.values, np.ones(len(series))).fit(
        cov_type="HAC", cov_kwds={"maxlags": lags}
    )


def subsample_tstats(series: pd.Series, step: int = WINDOW) -> list:
    """t-statistics from all `step` non-overlapping subsamples.

    Taking every 21st observation gives a near-independent sample, but the
    result depends slightly on the starting offset. Running all offsets and
    reporting the range is the assumption-free cross-check: if the conclusion
    flips depending on offset, it isn't robust.
    """
    return [
        float(stats.ttest_1samp(series.iloc[offset::step], 0).statistic)
        for offset in range(step)
    ]


def bootstrap_ci(series: pd.Series, draws: int = 10_000, seed: int = 42):
    """Distribution-free CI, resampling the non-overlapping series.

    Resampling the daily series would be invalid -- it is autocorrelated, so the
    draws would not be independent. Thinning to every WINDOW-th observation
    first is what makes the bootstrap legitimate here.
    """
    independent = series.iloc[::WINDOW].values
    rng = np.random.default_rng(seed)
    means = rng.choice(
        independent, size=(draws, len(independent)), replace=True
    ).mean(axis=1)
    return np.percentile(means, [2.5, 97.5])


# ---------------------------------------------------------------------------
# Reporting sections
# ---------------------------------------------------------------------------

def report_headline(df: pd.DataFrame) -> None:
    vrp = df["vrp_vol"]
    print("\n=== HEADLINE ===")
    print(f"observations      {len(df):,}")
    print(f"range             {df.index.min().date()} to {df.index.max().date()}")
    print(f"mean VIX          {df['vix'].mean():.2f}")
    print(f"mean realised vol {df['volatility'].mean():.2f}")
    print(f"mean VRP          {vrp.mean():+.2f} volatility points")
    print(f"median VRP        {vrp.median():+.2f}")
    print(f"std VRP           {vrp.std():.2f}")
    print(f"% positive        {(vrp > 0).mean() * 100:.1f}%")


def report_inference(df: pd.DataFrame) -> None:
    """Four methods side by side. The naive test is computed deliberately, as
    the wrong answer -- the size of the discrepancy is itself the finding."""
    vrp = df["vrp_vol"]
    print("\n=== INFERENCE ===")

    naive = stats.ttest_1samp(vrp, 0)
    print(f"naive t-test            t = {naive.statistic:.1f}   <-- INVALID, assumes independence")

    ts = subsample_tstats(vrp)
    print(f"non-overlapping (21x)   t = {min(ts):.1f} to {max(ts):.1f}   (~{len(vrp) // WINDOW} obs each)")

    res = hac_fit(vrp)
    lo, hi = np.asarray(res.conf_int())[0]
    print(f"Newey-West HAC          z = {float(np.asarray(res.tvalues)[0]):.1f}   95% CI [{lo:.2f}, {hi:.2f}]")

    b_lo, b_hi = bootstrap_ci(vrp)
    print(f"bootstrap (10k draws)         95% CI [{b_lo:.2f}, {b_hi:.2f}]")

    # Sensitivity: the estimate should not move much at double the lag length.
    res42 = hac_fit(vrp, lags=WINDOW * 2)
    print(f"HAC sensitivity (lags={WINDOW * 2}) z = {float(np.asarray(res42.tvalues)[0]):.1f}")

    ratio = abs(naive.statistic) / max(ts)
    print(f"\nnaive overstates by ~{ratio:.1f}x  (sqrt({WINDOW}) = {np.sqrt(WINDOW):.1f} predicted from overlap)")


def report_distribution(df: pd.DataFrame) -> None:
    """The economic content is in the shape, not the mean: many small positives
    and a few very large negatives is the payoff profile of an insurance seller."""
    vrp = df["vrp_vol"]
    print("\n=== DISTRIBUTION ===")
    print(vrp.describe(percentiles=[.01, .05, .25, .5, .75, .95, .99]).round(2).to_string())
    print(f"skewness          {vrp.skew():.2f}")
    print(f"excess kurtosis   {vrp.kurtosis():.2f}")


def report_worst_episodes(df: pd.DataFrame, n: int = 10) -> None:
    monthly_min_dates = df.groupby(df.index.to_period("M"))["vrp_vol"].idxmin()
    worst = df.loc[monthly_min_dates, ["vix", "volatility", "vrp_vol"]].nsmallest(n, "vrp_vol")
    print(f"\n=== {n} WORST EPISODES ===")
    print(worst.round(2).to_string())


def report_subperiods(df: pd.DataFrame) -> None:
    """Is the premium decaying? A premium arbitraged away since the 1990s would
    be of no use today, regardless of the long-run average."""
    periods = [("1990s", "1990", "1999"), ("2000s", "2000", "2009"),
               ("2010s", "2010", "2019"), ("2020s", "2020", "2026")]

    rows = []
    for name, start, end in periods:
        sub = df.loc[start:end, "vrp_vol"]
        lo, hi = np.asarray(hac_fit(sub).conf_int())[0]
        rows.append({
            "period": name,
            "n": len(sub),
            "mean": sub.mean(),
            "std": sub.std(),
            "pct_pos": (sub > 0).mean(),
            "mean_over_std": sub.mean() / sub.std(),
            "ci_low": lo,
            "ci_high": hi,
        })

    print("\n=== SUB-PERIOD STABILITY ===")
    print(pd.DataFrame(rows).set_index("period").round(3).to_string())


def report_vix_buckets(df: pd.DataFrame) -> None:
    """Descriptive only. Any trading rule derived from this table would be
    in-sample selection -- see 02_results_spread.md, where nine such filters were
    tested and all nine underperformed unconditional entry."""
    buckets = pd.cut(df["vix"], [0, 15, 20, 25, 30, 100])
    summary = df.groupby(buckets, observed=True)["vrp_vol"].agg(
        n="count", mean="mean", median="median", std="std",
        pct_pos=lambda x: (x > 0).mean(), worst="min",
    )
    print("\n=== VRP BY VIX LEVEL (descriptive) ===")
    print(summary.round(3).to_string())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true",
                        help="ignore the cached snapshot and download current data")
    args = parser.parse_args()

    df = build_vrp(load_raw(refresh=args.refresh))

    report_headline(df)
    report_inference(df)
    report_distribution(df)
    report_worst_episodes(df)
    report_subperiods(df)
    report_vix_buckets(df)


if __name__ == "__main__":
    main()
