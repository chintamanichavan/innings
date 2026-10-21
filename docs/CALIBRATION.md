# Is my model better calibrated than the betting market?

The question, data, method and predictions below were written before any
odds were compared with the model, and are left as written. What was measured
follows them, from [Measured](#measured) on.

## The question

Innings gives every side a chance of winning, before the match and after every
ball. A chance is only worth something if it is right as often as it says: of
all the times it says 70%, that side should win about 70% of the time. That is
calibration. The hardest thing to measure it against is a betting market,
where people with money at stake set the price. So: on the same matches, at
the same moments, are Innings' chances closer to what happened than the
market's?

## The data

- **The market.** Betfair's data scientists publish free files of Betfair
  Exchange prices for the Big Bash League, seasons 2020/21 to 2025/26
  (`BBL10_Match_Odds.csv` to `BBL15_Match_Odds.csv` on
  betfair-datascientists.github.io). Each match has the best back and lay
  price for each side at eleven moments: the first ball; after 4, 6, 10 and 15
  overs of each innings; and at the end of the first innings. An exchange is
  people betting against each other, so its prices are the crowd's view with a
  thin spread, not a bookmaker's view with a margin. The files are used as
  downloaded and are not republished; the page shows only the comparison.
- **The matches.** Cricsheet's ball-by-ball records of the same matches,
  already in Innings: 309 BBL matches over the six seasons.
- **Joining them.** By date and the two team names. Matches cut short by
  rain (a reduced number of overs, or a result by method) and matches without
  a result are left out, and the number left out is reported.

## The two chances, at each moment

| Moment | Innings | Market |
|---|---|---|
| First ball | the pre-match forecast (team ratings, recent form, lineup strength) | first-ball price |
| After 4, 6, 10, 15 overs, and end of the first innings | the in-play win model, from the score, wickets and balls left | price at that moment |
| After 4, 6, 10, 15 overs of the chase | the in-play win model, now with the target | price at that moment |

The market's chance for a side is the middle of its back and lay prices,
turned into a chance (1 / price), then scaled so the two sides add to one.
A moment where a price is missing, or the spread is wider than a fifth of the
price, is left out of that moment's sample.

**No looking ahead.** The win chances stored in Innings come from models
fitted on every match, including these. For this study both models are fitted
again for each season, on matches before that season only. The in-play model
does not know who is playing: it sees only the state of the game. The market
knows the teams, the players, the pitch and the weather. That gap is part of
the answer, not a flaw to hide.

## How the two are compared

1. **Accuracy at each moment.** The Brier score (the mean squared gap between
   the chance and what happened, 0 is perfect, 0.25 is a coin flip) and the
   log loss, for Innings and for the market on the same matches. The difference
   gets a 95% interval from resampling whole matches.
2. **Calibration.** All moments pooled; chances grouped into ten bins; how often
   the side won in each bin, for each source. One number per source: the
   calibration error, the average gap between what a bin said and what
   happened, weighted by how many chances fall in it.
3. **Would it have made money?** At each moment, where Innings' chance for a side
   is higher than the price implies by more than a margin, back that side for
   one unit at the best back price. Return per unit staked, with a 95% interval
   from resampling matches, before the exchange's commission.

## Predicted, before measuring

| Measure | Predicted |
|---|---|
| Matches joined | 270 to 300 of 309 |
| Brier at the first ball, Innings / market | 0.245 / 0.240: both near a coin flip, market a little better; the difference's interval includes zero |
| Brier mid-match (after 10 overs of the first innings) | market better by 0.01 to 0.02: it knows the teams |
| Brier late in the chase (after 15 overs) | both about 0.10; the gap smaller than earlier |
| Calibration error, pooled | both under 0.04; Innings a little worse, too sure of itself at the ends |
| Backing Innings' edges (margin 5 points) | loses money: −2% to −10% per unit, interval including small gains |
| The answer to the question | no: the market is better calibrated, most of all early in a match |

## Not in scope

Other leagues (the free files cover only Australian competitions), the
women's Big Bash (not yet in Innings), and real betting: no money is placed,
and the exchange's commission and the price moving after a bet are ignored.

---

## Measured

Run with `uv run innings market` (about 80 seconds; it downloads the six
season files on first use and writes `data/market/report.json`).

### The matches

| | Matches |
|---|---|
| BBL matches in Innings, 2020/21 to 2025/26 | 309 |
| Priced in Betfair's files | 303 |
| Found in both | 301 |
| Left out: cut by rain, or no result | 14 |
| **Scored** | **287** |

A moment a match never reached (a chase won inside fifteen overs, say) is not
scored, nor is one whose price was missing or too wide, so the late moments
have fewer matches.

### Accuracy at each moment

Brier score, lower is better. The gap is Innings minus the market; above zero
means the market was closer. The interval comes from resampling whole matches.

| Moment | Matches | Innings | Market | Gap | 95% interval |
|---|---|---|---|---|---|
| First ball | 287 | 0.2432 | 0.2332 | +0.0100 | +0.0016 to +0.0182 |
| 1st innings, 4 overs | 276 | 0.2294 | 0.2147 | +0.0147 | +0.0035 to +0.0262 |
| 1st innings, 6 overs | 283 | 0.2332 | 0.2197 | +0.0135 | +0.0024 to +0.0246 |
| 1st innings, 10 overs | 279 | 0.2258 | 0.2081 | +0.0178 | +0.0068 to +0.0275 |
| 1st innings, 15 overs | 272 | 0.2008 | 0.1930 | +0.0078 | −0.0016 to +0.0168 |
| End of 1st innings | 281 | 0.1958 | 0.1893 | +0.0064 | −0.0041 to +0.0171 |
| Chase, 4 overs | 263 | 0.1753 | 0.1670 | +0.0083 | −0.0025 to +0.0192 |
| Chase, 6 overs | 249 | 0.1585 | 0.1530 | +0.0055 | −0.0055 to +0.0166 |
| Chase, 10 overs | 233 | 0.1490 | 0.1383 | +0.0107 | +0.0007 to +0.0214 |
| Chase, 15 overs | 139 | 0.1312 | 0.1186 | +0.0126 | −0.0074 to +0.0322 |

The market is closer at every moment. The gap is clearly real at the first
ball, through the first ten overs of the first innings, and at ten overs of
the chase; elsewhere the interval includes zero. Log loss tells the same story.

### Calibration

All 2,562 scored chances pooled, each counted from both sides so the answer
does not depend on which side a source lists first.

| Chance said | Innings: won | Market: won |
|---|---|---|
| 0–10% (avg 4%) | 6.4% | 4.1% |
| 10–20% (15%) | 14.0% | 14.4% |
| 20–30% (25%) | 26.2% | 20.1% |
| 30–40% (35%) | 34.7% | 33.8% |
| 40–50% (45%) | 47.7% | 44.3% |
| **Calibration error** | **0.015** | **0.017** |

(The upper half mirrors the lower.) The difference in calibration error,
Innings minus market, has a 95% interval of −0.027 to +0.022: no difference.

### Predicted against measured

| Measure | Predicted | Measured | |
|---|---|---|---|
| Matches joined | 270–300 of 309 | 287 scored (301 joined) | right |
| Brier at the first ball | 0.245 / 0.240, interval including zero | 0.243 / 0.233, interval +0.002 to +0.018 | wrong: the market is clearly better before a ball is bowled |
| Gap after 10 overs of the first innings | market better by 0.01–0.02 | +0.018 | right |
| Late in the chase | both about 0.10, smaller gap | 0.131 / 0.119, gap +0.013 | wrong on both |
| Calibration error | both under 0.04, Innings a little worse | 0.015 / 0.017, no difference | half right: both well under, Innings not worse |
| Backing Innings' edges | −2% to −10% a unit, interval including small gains | −3.6% on 1,412 bets, −17.7% to +10.7% | right |
| The answer | no, the market is better calibrated | equally calibrated; the market is more accurate | wrong in an instructive way |

### What it means

**Calibration and accuracy are different things, and they came apart here.**
Innings is as honest about its uncertainty as the market is: when it says 70%,
the side wins about 70% of the time. But the market is sharper. It moves
further from 50% when it has reason to, and is right to. A forecaster that
knows less but is honest about it is calibrated and less accurate, and that is
what Innings is.

**Why the market knows more.** The in-play model sees only the score, wickets
and balls left. To test whether knowing the teams closes the gap, the in-play
chance was blended with Innings' own pre-match forecast, with the two weights
for each innings fitted on earlier seasons only (so 2020/21 has no blend, and
the comparison uses the other five seasons):

| Moment | Innings | Innings + its pre-match forecast | Market |
|---|---|---|---|
| 1st innings, 4 overs | 0.2286 | 0.2242 | 0.2106 |
| 1st innings, 10 overs | 0.2259 | 0.2213 | 0.2024 |
| Chase, 10 overs | 0.1462 | 0.1421 | 0.1285 |
| Chase, 15 overs | 0.1212 | 0.1170 | 0.1180 |

Remembering the teams helps a little and closes about a fifth of the gap. The
rest is what the market knows and Innings' ratings do not: the pitch, the
weather, which players are in form, late team news. The first-ball gap (0.010)
is the same thing in its purest form, as both sides there know the toss and
the batting order. (Late in the chase the blend draws level with the market,
on 112 matches.)

**Money.** Backing every side Innings rated five points above the market lost
3.6% a unit over 1,412 bets, before commission, with an interval wide enough to
include breaking even. No edge was found, which is what a forecaster that is
calibrated but less sharp than the market should expect.

### Known limits

- 287 matches is a small sample for a league; intervals are wide.
- Lineup strength in the pre-match forecast uses players' past values, which
  were scored with the build's expected-runs model, fitted on all years. That
  leaks a little information from the future into the first-ball forecast; it
  can only flatter Innings, which still lost there.
- Exchange prices at a moment are a snapshot; the market's chance is the
  middle of the back and lay prices, and moments with a wide or missing price
  are left out.
