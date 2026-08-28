# Author's note

## Where the question came from

I started from an intuition rather than a paper. The S&P 500 rises over long
horizons, so selling put options — taking the other side of downside protection —
looked like it should pay, in the way that writing insurance pays: you collect a
premium from people who want to be protected, and most of the time the event they
are insuring against does not happen.

Reading around that idea, I found two things that sharpened it. Put options on
equity indices are systematically more expensive than equivalent calls, and
implied volatility — the input that prices them — tends to sit above the
volatility that subsequently materialises. If that second gap were real and
persistent, options would be priced above their eventual payoff on average, and
the seller would be collecting the difference.

That is the variance risk premium, and it is long established in the literature.
I did not discover it. What I wanted to know was whether it held up in the data
across the full VIX history, whether it had been arbitraged away, and whether an
account-sized, defined-risk position could actually capture it.

## Division of labour

The methodology was designed with AI assistance and I want to be exact about
that, because this repository contains a specification written to me rather than
by me.

**Claude (Anthropic) supplied the statistical apparatus.** I had no training in
time-series econometrics. The choice of Newey–West HAC estimation, the
non-overlapping subsampling design, the bootstrap, the pre-registration structure
itself, and the specific traps to watch for — all of that came out of that
collaboration, and the two pre-registration documents are the record of it. The
working paper's prose was drafted from my computed results and then revised by me.

**The questions, the code and the verification are mine.** The original
hypothesis, the decision to structure the trade as a bull put spread rather than a
naked short put, and the VIX-timing idea that Study 2 ultimately rejected were all
mine. I wrote every line of analysis code, ran it, and checked it.

The most accurate way to read this is as a supervised project in which the
supervisor was an AI. The methodology is not my original contribution. What
follows is.

## Where my reasoning was wrong

**My original intuition conflated two different things, and my own analysis later
exposed it.** I reasoned that selling puts should pay because the market drifts
upward. That is a claim about equity returns. The variance risk premium is a claim
about volatility being overpriced — a different source of return entirely, and the
one I set out to measure.

The conflation came back in Study 2. Reviewing the year-by-year breakdown of the
simulated strategy, I noticed that every losing year coincided with an equity bear
market. A material share of what I had measured was equity beta, not volatility
premium — the two things I had run together at the start, now showing up mixed
together in my result. It is the eighth limitation in my write-up and it is not in
the specification I was given; it is the one substantive weakness in the work I
found on my own. It is also why the follow-up study specifies a delta-matched
benchmark: that is the test that separates them.

**I also assumed a high win rate meant an edge.** The simulated strategy wins
82.2% of trades, which sounds decisive. But the payoff is asymmetric — wins
collect the full credit, losses run to nearly the full width of the spread — and
the win rate required merely to break even is 69.7%. Only the 12.5-point excess
carries any information. A strategy winning 82% of the time can still lose money.

**I found a look-ahead bias bug in my own code.** The realised-volatility window
must cover the days strictly *after* each observation date. Mine ran backwards.
The specification had warned this was the most common error in this analysis and I
made it anyway. I caught it by reconstructing a single observation by hand and
comparing it against the vectorised column — a check nobody asked me to run. The
uncorrected version produced a plausible, confident, entirely meaningless number,
which is what makes this class of bug dangerous: nothing fails, and the output
looks right.

## The hypothesis I killed

I expected the premium to be worth timing. High VIX means expensive options, so
selling only when VIX was elevated should beat selling indiscriminately.

Per trade, that is true — mean P&L rises monotonically with VIX, and filtering to
VIX ≥ 30 gives the best per-trade result in the sample at $16.53 against $8.35
unfiltered. It is what I expected to find.

It is also the wrong way to measure it. A filter that only trades above VIX 30
sits idle for 92% of days, and those days are not free — they are days the
unfiltered strategy is earning. Ranking the filters by expected annual return
rather than per-trade return inverts the result completely: VIX ≥ 30 produces an
estimated $15.87 a year against $100.14 for unconditional entry. All nine filters
I tested underperformed doing nothing, on both the full sample and the
out-of-sample half.

Neither the filter sweep nor the annualised measure was specified. I built both,
and the measure is what makes the conclusion correct rather than backwards.

## What I would do differently

**Use real option data.** This is a simulation, not a backtest. Both legs are
priced with Black–Scholes at VIX, which ignores volatility skew — and skew applies
precisely to the out-of-the-money strikes this strategy sells, so the error hits
where it matters most. It also assumes fills at theoretical prices, which nobody
gets. Rerunning against WRDS/OptionMetrics option-chain data would make it an
actual backtest, and it is the only way to settle my pre-registered criterion F3.

**Model the exit.** Every position here is held to expiry, which is neither what a
real playbook does nor the least risky choice. I would test earlier exits, a range
of times to expiry, and whether when a position is closed relates to how it
performs. I would want to be careful doing it, though: I have just finished
demonstrating that nine plausible entry filters all failed once measured properly,
and searching across exit rules is the same kind of search. Any exploration of it
needs criteria fixed in advance and an out-of-sample split, or I will find a rule
that works only in the sample I found it in.

**I am still not fully convinced.** The premium is clearly measurable, but I keep
returning to why it persists. My own analysis argues it is compensation for crash
risk rather than an inefficiency — the −3.65 skew and February 2020, when VIX sat
at 15.56 and realised volatility came in at 87.52, make that case fairly
convincingly. Risk compensation would explain why nobody has competed it away.

What that argument does not tell me is whether the compensation is *adequate* for
the particular position I simulated: a small, defined-risk seller taking a bounded
but frequently maximal loss, paying retail transaction costs. A premium can be
real, economically justified, and still not worth collecting at my size. Index
data cannot distinguish those cases. Option-chain data can, and until it does I
would not describe this as a strategy I have validated.

## Status

Working paper, not peer-reviewed. My pre-registered criterion F3 — whether the
premium survives realistic transaction costs — is recorded as unresolved rather
than resolved in my favour, because index data cannot settle it. That question
needs option-chain data, and it is what the follow-up study is for.
