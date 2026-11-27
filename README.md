# Innings

Cricket, told through win chance. Every ball changes a side's chance of winning; Innings
measures that change and writes the match up from it.

## What it does

Innings is a sports almanac you read. Every match, player and team opens with a headline
and a short story written from the numbers. The chart is the illustration. The full tables
come last.

**What only Innings does**
- **The honest forecaster** – a call before every game, scored by one public rule (a coin
  flip scores 0, sure-and-wrong costs 75). The record on seasons the model never trained on is
  on show, worst misses included.

**For fans**
- **Front page** – game of the week as a story, a form guide, a classic and a play of the day. Pick your teams and they lead the page.
- **Match centre** – the result, player of the match, and four tabs: Summary (scorecard in
  brief, win probability in both teams' colours, the story), Scorecard, Commentary (every ball,
  over by over, with end-of-over summaries) and Graphs (worm, run rate, Manhattan, partnerships).
- **Profiles** – a career summary by format, as every profile opens (Mat, Inns, NO, Runs, HS, Ave,
  SR, 100s, 50s; Wkts, BBI, Econ, 5w), recent form, then the deeper numbers.
- **Teams** – the season's points table (P W L NR Pts NRR) and the squad by role.
- **Puzzle corner** – a daily "Who am I?", Higher or Lower, and You vs the Model, with
  streaks and a shareable result.
- **Records** – wildest games, biggest comebacks, biggest plays, best single games.
- **Follow** teams and players. Replay any match ball by ball.

**At scale**
- **The stream** (`/cricket/stream`) – one real IPL season played 100,000 times by the neural
  network on a graphics card. Every ball goes through Kafka into a Parquet data lake, and the
  page shows each team's title odds settling. Below it, real matches replay live through the
  same broker. See "A season, 100,000 times" below.

**Stats you can cut any way**
- **Ask** (`/cricket/ask`) – type a question in plain words: "Kohli vs leg spin since 2020",
  "best death bowlers IPL 2025", "MI vs CSK 2020-2023". The page shows how each word was read,
  lists the words it could not place, and answers with a table. The question is in the address,
  so an answer is a link to share.
- **Matchups** (`/cricket/matchups`) – a batter against bowlers, or a bowler against batters:
  by bowling type, batting hand, phase, ground, opponent, league or year. Head to head when
  both are named. Every player page opens with theirs.
- **Impact** (`/cricket/impact`) – who changes games, for any league, year and phase: runs
  added above average (RAE), win chance added (WPA), and for bowlers wickets above average
  (W+): wickets taken minus those an average bowler takes on the same balls. Below, the single
  innings and spells that swung matches most.

**Underneath**
- **Stats** – leaderboards, splits, game logs, team rating history, venues, compare.
- **Player value** – RAE (runs above expected), WPA (win probability added) and Clutch.
- **Win probability** – for T20, ODI and Test cricket (a Test draw counts half).
- **Match prediction** – Elo + recent form + lineup strength, tested on unseen seasons.

**App**
- Real URLs with link previews, so a shared match shows its headline.
- Installable on a phone, with a bottom tab bar. Light and dark editions.
- Apple News design language, the same skin as Artha: warm off-white page, white rounded
  cards with a soft lift, serif headlines, one red accent for section labels.
- Self-hosted fonts. No logos or photos: story cards use the two teams' colours instead.

## Run it

Innings is two programs. The **backend** (Python, FastAPI) owns the data and the models and
answers under `/api`. The **frontend** (TypeScript, Next.js, in `frontend/`) draws the pages
and passes every `/api` request on to the backend.

```sh
docker compose up -d --build    # all of it: http://127.0.0.1:8453
```

To work on it:

```sh
uv sync
uv run innings all              # download data, build models (a few minutes)
uv run innings serve            # the API, on http://127.0.0.1:8453
uv run pytest                   # API, unit and style tests
uv run ruff check src tests

cd frontend && pnpm install
API_URL=http://127.0.0.1:8453 pnpm dev    # the website, on http://127.0.0.1:8454
pnpm typecheck && pnpm test && pnpm format:check
```

`uv sync --extra train && uv run innings train` trains the neural network (about four
minutes on one graphics card) and writes it to `data/nn/`. The site runs it with
onnxruntime on an ordinary processor, so the container needs no PyTorch.

`innings ingest --refresh` downloads fresh data. `innings build` rebuilds models only.
`innings refresh --every 12` rebuilds on a timer; the server picks up the new database
without a restart. `docker compose` runs six containers: `api`, `web`, `refresh`, and for the
live stream `kafka`, `bowler` and `scorer`. The season job runs outside Docker, because it
needs the graphics card; it leaves its results in `data/season/` for the site to show.

## How the code is laid out

```
src/innings/
  config.py            paths, what to load, and the shape of each cricket format
  ingest/              the Cricsheet loader   -> every ball, with the game state before it;
                       styles.py: batting hand and bowling style from Wikipedia infoboxes
  models/
    cricket_limited.py T20 and ODI: runs and win chance from balls left and wickets down
    cricket_test.py    Tests: no ball limit, four innings, and a draw is a result
    cricket.py         runs the right model per format, then credits batter and bowler
    ratings.py         team Elo, recent form, and fading player ratings
    predict.py         one pass through history, then a small model, tested on unseen years
    common.py          what the models share: RAE, WPA, scoring a model
  aggregates.py        season lines, one match list, lineups
  insights.py          thrill, biggest plays, splits, clutch, skill profiles, form
  balls.py             playing styles, and one wide row a ball that every slice reads
  web/
    db.py              read-only queries; reopens when a rebuild swaps the file
    stories.py         turns plays, matches, players and teams into plain sentences
    scorecard.py       batting and bowling cards, fall of wickets, partnerships, runs per over
    slices.py          any filter over every ball, counted as a batting or bowling line
    ask.py             a question in plain words read into a slice; a fixed vocabulary, no AI
    matches, players, teams, forecasts   one module per subject
    routes/            the JSON API, one file per section of the site
  season/              one season played many times: the big batch job
    fixtures.py        a real IPL season: who played whom, where, in what order, who bowled when
    engine.py          the network bats out many innings at once on a graphics card
    simulate.py        whole seasons in blocks: the league, the table, then the playoffs
    table.py           the league table of many seasons at once
    record.py          a finished match as 729 bytes, the message that goes through Kafka
    lake.py            Kafka -> Parquet: unpacks matches into one row a ball
    tally.py           Kafka -> the live count of who has won the title
    findings.py        questions asked of the lake with DuckDB
    run.py             starts the writers and the tally, plays the seasons, writes the report
  stream/              the live stream through Kafka
    feed.py            past matches turned back into messages: start, innings, ball, end
    state.py           one match's score, kept up to date a ball at a time (no Kafka in it)
    scoring.py         the saved win models, asked about many matches at once
    scorer.py          reads balls, keeps the scores, writes each ball with its win chance
    bowler.py          replays close matches into Kafka at the pace of a live game
    board.py           the scoreboard inside the API server, which the page listens to
    bench.py           measures balls a second and checks every answer against the build
    wire.py            the Kafka details: broker, topics, how a message is written
  feeds.py             news headlines and live scores from publishers' free RSS feeds
  nn/                  the neural network: features, data, model, training, serving

frontend/              the website: Next.js (App Router), React, TypeScript in strict mode
  app/[sport]/         one folder per page; page.tsx runs on the server and fetches its data
  components/          shared pieces: charts/, scorecard/, frame/ (header, tab bar, first visit)
  lib/                 addresses, the API call, formatting, device storage, animation helpers
  tests/               unit tests (vitest)
```

Python does the thinking and the browser does the drawing. Anything that moves on a page
(the learning map, the simulated innings, the Manhattan) is worked out in Python and sent as
plain numbers; the TypeScript only plays it back.

| | Cricket (T20, ODI) | Cricket (Test) |
|---|---|---|
| State | balls left, wickets down | wickets down, lead, match balls bowled |
| State value | boosted model, monotone in balls and wickets | runs left in the innings, by wickets |
| Win probability | balls, wickets, runs needed, edge over par | win / draw / loss; a draw counts half |
| Data | Cricsheet: T20Is, ODIs (from 2002), 16 T20 leagues (below) | Cricsheet Tests (from 2001) |

RAE = runs scored + state value after − state value before.
WPA = win chance after − win chance before.

## Results on held-out data

| | Cricket |
|---|---|
| Win probability, right side per event | 75.4% |
| Match prediction, accuracy | 64.4% |
| Match prediction, coin-flip baseline | 50.9% |

## The lab: a neural network that learned cricket

`src/innings/nn/` trains one network to answer one question: what happens on the next ball?
It sees the match situation, the last 24 balls, and a learned vector for the batter, the
bowler and the ground. The Lab page (`/cricket/lab`) shows it learning, lets you ask it about
any batter against any bowler, and lets it bat out an innings 1,000 times.

Scored once on 782,485 balls from 2025 and 2026 that no model saw (log loss, lower is better):

| Model | Score |
|---|---|
| League average | 1.488 |
| Situation table | 1.465 |
| Gradient boosting | 1.433 |
| Network, situation only | 1.430 |
| Network, plus recent balls | 1.421 |
| Network, plus who is playing | 1.419 |

Where it falls short, as the page also says: its guess at the match result is worse than the
older win models (so they stay in charge of win chances), its simulated totals average about
11% too low, and it knows both players on only 38% of test balls.

## A season, 100,000 times

Royal Challengers Bengaluru won the real IPL in 2026. Was that likely, or lucky? To find out,
the neural network from the lab plays the whole season again, 100,000 times.

```
graphics card  ->  Kafka  ->  6 lake writers  ->  Parquet lake  ->  DuckDB
                        \->  tally            ->  the live page
```

```sh
uv sync --extra train
docker compose up -d kafka
uv run innings season run --seasons 100000     # about nine minutes on one desktop
```

- **A real season, replayed.** The 70 league matches keep their real grounds, batting orders and
  bowlers (`season/fixtures.py`). The playoffs follow each simulated table.
- **A graphics card bowls.** `season/engine.py` plays 70,000 innings at once: one step asks the
  network about the next ball of every innings, draws an outcome for each, and moves each score
  on. It is the same network the site serves, rebuilt from the same exported file (`nn/gpu.py`).
- **A match is 729 bytes.** A JSON message a ball would be about two billion messages. A match
  is one fixed-size record: a byte for what each ball was and a byte for who faced it. Readers
  lay thousands side by side and unpack them with no loop (`season/record.py`).
- **Kafka sits in the middle.** The simulator only writes. Six lake writers, one to a partition,
  unpack matches into rows. The tally keeps the running title count for the page.
- **The lake is a star.** One huge `balls` table of short numbers, pointing into tiny `matches`,
  `people`, `teams` and `outcomes` tables. DuckDB reads the Parquet files directly.
- **Counted three ways.** The simulator, the tally and the lake each count the balls. They must
  agree, or something was lost or doubled.

Measured on one desktop (RTX 5070 Ti), 100,000 seasons of IPL 2026:

| | |
|---|---|
| Matches played | 7,400,000 |
| Balls bowled, streamed and stored | 1,765,365,574 |
| Time, start to finish | 9.6 minutes |
| Balls a second, end to end | 3,080,066 |
| Lake on disk | 2.9 GB in 30 Parquet files (1.6 bytes a ball) |
| Slowest question asked of all 1.77 billion rows | 5.0 seconds |
| Balls counted by simulator, tally and lake | equal |

| Team | Won the title | Made the playoffs | League wins, simulated | Real |
|---|---|---|---|---|
| Rajasthan Royals | 22.1% | 62% | 8.0 | 8 |
| Royal Challengers Bengaluru | 18.0% | 63% | 8.1 | 9 |
| Sunrisers Hyderabad | 15.1% | 52% | 7.5 | 9 |
| Punjab Kings | 12.7% | 49% | 7.4 | 7 |
| Mumbai Indians | 9.1% | 44% | 7.2 | 4 |
| Kolkata Knight Riders | 8.4% | 38% | 7.0 | 6 |
| Delhi Capitals | 5.3% | 25% | 6.3 | 7 |
| Lucknow Super Giants | 4.7% | 27% | 6.4 | 4 |
| Chennai Super Kings | 2.4% | 19% | 5.9 | 6 |
| Gujarat Titans | 2.3% | 21% | 6.1 | 9 |

Royal Challengers Bengaluru, the real champions, were the second most likely.

Its limits, as the page also says: these balls were never bowled, so the volume is made by a
model; the model's rare innings are too big (its records beat every real one); players with
fewer than 200 real balls are "unknown" to it; and the toss, ties, run-outs, injuries and
selection are left out or settled by a coin.

## The stream at match pace

The season job is a batch. This is the other kind of stream: real matches replayed one ball a
second, each scored as it lands.

```
bowler  ->  Kafka topic "balls"  ->  scorer  ->  Kafka topic "scored"  ->  API  ->  the page
```

- **A ball is a message.** It says what happened and carries no answer. Messages are keyed by
  match, so Kafka keeps one match in order while many run side by side.
- **The scorer keeps state.** It holds each match's runs, wickets and balls left, and asks the
  saved win models (`data/models/`, written by the build) as each ball arrives. It never waits
  for a batch to fill, yet under load it hands the models thousands of balls at once.
- **It scales by adding scorers.** They join one consumer group and Kafka shares the matches out.
- **The topic is the backup.** A scorer that restarts reads its partitions again from the start
  to rebuild every score, and answers only the balls nobody has answered.
- **The page is pushed to.** The API server follows the "scored" topic and sends each ball to the
  browser over one open connection (server-sent events).

`uv run innings stream bench --scorers 6` pushes every limited-overs match through a real
broker and checks each answer against the nightly build. On one desktop, each scorer held to
one core, 3,583,777 balls:

| Scorers | Balls a second |
|---|---|
| 1 | 36,578 |
| 2 | 68,038 |
| 3 | 96,169 |
| 6 | 187,011 |

Every one of the 3,583,777 answers matched the build exactly. A live ball takes about 25
milliseconds from the bowler to the scoreboard.

Its limits, as the page also says: the matches are replays, because no free live ball feed
exists; five million balls is not big data; there is one broker with no copies; a restarted
scorer may answer its last few balls twice (the scoreboard drops the repeats); and Tests are
not on the stream.

## How the code is kept honest

- **Small files with one job.** `tests/test_style.py` fails on any line over 110 characters,
  in Python and in the TypeScript, and on any source file over 500 lines.
- **Types end to end.** The frontend is TypeScript in strict mode with no `any`: every API
  answer a page uses has a written type. Prettier formats it; `tsc` checks it.
- **The build is repeatable.** The same data gives the same numbers every time: model
  training rows are ordered, and ties are broken by fixed keys.
- **Tests at three levels.** Pure logic (ratings, wording), the API against the built
  database, and style. The stream has its own: a ball scored on the stream gets exactly the
  build's number, and a restarted scorer carries on from the same ball. The season has its own:
  the graphics card runs the same network as the site, every simulated innings obeys the rules,
  and each lake row names the right batter and bowler. The network has its own: no ball sees itself or another innings, the
  exported model matches PyTorch, and a simulated innings obeys the rules of cricket.
- **Measured, not guessed.** Endpoints answer in under 70 ms warm. The front page ships
  about 60 kB of data.

## Known limits

- T20 leagues loaded: IPL, BBL, PSL, CPL, SA20, and for scouting the Syed Mushtaq Ali Trophy
  (SMAT), T20 Blast, BPL, ILT20, LPL, MLC, Nepal Premier League, Super Smash and CSA T20;
  for women the WPL, Women's Big Bash and Super Smash. The Hundred is left out: a 100-ball
  innings needs its own win model. Cricsheet's SMAT has gaps (no 2025 season, 8 matches in 2024).

- A bowler has one type: the first style their infobox lists. Part-timers who bowl two kinds
  are counted as the first.
- In a matchup, `Out` counts only the striker's own dismissals; a non-striker run out belongs
  to no matchup. Career tables count every dismissal, so the two can differ by a few.

- No credit for fielders yet.
- Cricket wicket values lean high: weak sides lose early wickets more often.
- Elo cannot compare teams that never meet (associate T20I nations).
- No pitch adjustment.
- Test forecasts leave draws out: they give the chance of winning a match that has a winner.
- Test and ODI history starts in the early 2000s, so older careers are cut short.
- State values are fit on all seasons, so player ratings used in prediction carry a
  very small look-ahead. Elo, form and the final model do not.

## Adding a sport

The database keeps a `sport` column and the API takes a `sport` parameter, but cricket is the
only sport today. A new sport needs a loader that writes one row per play with the game state
before it, a state-value model, an entry in `PARAMS` (`models/ratings.py`), `SPECS` and `SPORTS`
(`web/specs.py`), and build steps that fill the shared tables. Several queries and pages still
assume cricket and would need a pass. Sports that flow continuously (football, basketball) need
a different core than one delivery per play.

## Data credits

Data is from [Cricsheet](https://cricsheet.org), under the Open Data Commons
Attribution License.

Batting hands and bowling styles come from the infobox of each player's English Wikipedia
article (CC BY-SA), found through the ESPNcricinfo ID that Cricsheet's register gives each
player and Wikidata links to the article. Wikipedia lets clients that send no contact details
make 10 requests a minute, so the first download takes about ten minutes; after that only new
players are looked up. The infobox text is kept as written in `data/raw/styles.csv` and read at
build time. `src/innings/styles_known.csv` fills in players whose article gives no style.

How much is known, measured on the full database: the bowler's type for 88% of all balls and
the batter's hand for 89%. In ODIs, Tests and the franchise leagues it is 97–100%; in T20Is it
is about 55%, because players from smaller nations mostly have no article. Tables say how much
of their own balls they could place.

## News and live scores

Headlines come from the public RSS feeds of ESPNcricinfo, BBC Sport, the Guardian, NDTV Sports
and Sky Sports. Innings shows the headline, one line of summary and a link to the publisher;
it never copies an article. Live scores come from ESPNcricinfo's public live feed, which gives
each match's score line and nothing finer, so live matches have no win chance or scorecard.
A feed that fails is skipped, and feed text is treated as untrusted (`src/innings/feeds.py`).

## Story-card pictures

A match card shows one of four scenes, each modelled and rendered in Blender in shades of grey:
the broadcast view down the pitch under floodlights (`animation/card_ground.py`), broken stumps
for a side bowled out (`card_stumps.py`), a six into the lights for a high-scoring game
(`card_six.py`) and a trophy for a final (`card_trophy.py`). The build picks one for every match
(`ART` in `aggregates.py`). The page lays the picture over the two teams' colours and keeps only
its light and shade, so four renders suit every match. `PREVIEW=1 blender -b -P
animation/card_six.py` renders a quick, small version into `animation/check/`.

## The opening animation

On a first load the name is spelled with cricket kit. The capital I is a plain willow bat, the
small i wears a helmet as its dot, and a 3D ball is bowled in to rest as the full stop in
"Innings." Each piece is modelled and rendered by Blender from a Python script:

```sh
blender -b -P animation/ball.py      # writes frontend/public/intro/ball.webp, in about 10 seconds
blender -b -P animation/bat.py       # writes bat.webp
blender -b -P animation/helmet.py    # writes helmet.webp
```

Each script decides what its piece looks like; the constants at the top are the things to
change, and `animation/studio.py` holds the camera and lights they share. The ball script
writes one picture holding every frame of one turn. The website only moves those pictures
(`frontend/components/frame/Intro.tsx` and the "intro" rules in `globals.css`). It uses no script, plays once per page load, and is skipped for readers who
ask for less motion.
