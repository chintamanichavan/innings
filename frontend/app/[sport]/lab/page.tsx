// The lab: a neural network that learned cricket ball by ball. Watch it learn, ask it about
// a matchup, let it play an innings, then see how good it is and where it falls short.

import type { Metadata } from "next";

import { CountUp, GrowBar } from "@/components/motion";
import { ApiError, api } from "@/lib/api";
import { capital, num, pct } from "@/lib/format";
import { tip } from "@/lib/toast";

import { LabMap } from "./LabMap";
import { Matchup } from "./Matchup";
import { Simulator } from "./Simulator";
import type { CalibrationPoint, Card, ModelScore, PlayerMap, SimulatedLeague } from "./types";

export const metadata: Metadata = {
  title: "The lab",
  description: "A neural network learns cricket, one ball at a time. Watch it, ask it, test it.",
};

const NETWORK = "Network"; // every network row in the score table starts with this
const FULL_NETWORK = "Network: + who is playing";
const CALIBRATION_TOP = 0.115; // the calibration charts run from 0 to this chance
const NOT_TRAINED = 503; // what the server answers before `innings train` has run

function NotTrained() {
  return (
    <>
      <p className="kicker">The lab</p>
      <h1 className="page">The network has not been trained yet</h1>
      <p className="standfirst">
        Run <code>innings train</code> on a machine with a graphics card. It takes about four minutes.
      </p>
    </>
  );
}

function Facts({ card }: { card: Card }) {
  const facts: [number, string][] = [
    [card.deployed.balls, "balls it learned from"],
    [card.deployed.vocabulary.batters, "batters it knows by name"],
    [card.deployed.parameters, "numbers inside the network"],
    [card.seconds, "seconds to train, start to finish"],
  ];
  return (
    <div className="tiles">
      {facts.map(([count, text]) => (
        <div className="tile" key={text}>
          <CountUp value={count} />
          <span>{text}</span>
        </div>
      ))}
    </div>
  );
}

/** Each model's error, drawn as how far it improves on always guessing the league average. */
function ScoreTable({ scores }: { scores: ModelScore[] }) {
  const baseline = scores[0].all;
  const largest = Math.max(...scores.map((score) => baseline - score.all));
  return (
    <div className="panel">
      <div className="gains">
        {scores.map((score) => {
          const byFormat = `T20 ${num(score.T20, 3)}. ODI ${num(score.ODI, 3)}. Test ${num(score.Test, 3)}.`;
          return (
            <div
              key={score.model}
              className={`gain ${score.model.startsWith(NETWORK) ? "net" : ""}`}
              {...tip(score.model, byFormat)}
            >
              <span>{score.model}</span>
              <div>
                <GrowBar percent={((baseline - score.all) / largest) * 100} />
              </div>
              <b>{num(score.all, 3)}</b>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** Stated chance against what happened, for one outcome. */
function Calibration({ bins, outcome }: { bins: CalibrationPoint[]; outcome: string }) {
  const width = 440,
    height = 300;
  const left = 40,
    right = 14,
    top = 10,
    bottom = height - 38;
  const x = (chance: number) => left + ((width - left - right) * chance) / CALIBRATION_TOP;
  const y = (chance: number) => bottom - ((bottom - top) * chance) / CALIBRATION_TOP;
  return (
    <figure>
      <div>
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`Stated chance of a ${outcome}`}>
          {[0, 0.05, 0.1].map((chance) => (
            <g key={chance}>
              <line className="axis" x1={left} x2={width - right} y1={y(chance)} y2={y(chance)} />
              <text x={left - 6} y={y(chance) + 4} textAnchor="end">
                {num(chance * 100)}%
              </text>
              <text x={x(chance)} y={bottom + 15} textAnchor="middle">
                {num(chance * 100)}%
              </text>
            </g>
          ))}
          <line className="ref" x1={x(0)} y1={y(0)} x2={x(CALIBRATION_TOP)} y2={y(CALIBRATION_TOP)} />
          <text x={(left + width - right) / 2} y={height - 3} textAnchor="middle">
            Chance of a {outcome} the network stated
          </text>
          {bins.map((bin) => (
            <circle
              key={bin.stated}
              cx={x(bin.stated)}
              cy={y(bin.happened)}
              r="4.5"
              fill="var(--series-1)"
              stroke="var(--card)"
              strokeWidth="2"
              {...tip(
                `Said ${num(bin.stated * 100, 1)}%`,
                `Happened ${num(bin.happened * 100, 1)}% of the time, over ${num(bin.n)} balls.`,
              )}
            />
          ))}
        </svg>
      </div>
    </figure>
  );
}

function Probes({ probes }: { probes: PlayerMap["probes"] }) {
  return (
    <div className="panel">
      <div className="gains">
        {probes.map((probe) => {
          const share = Math.max(0, probe.r_squared);
          return (
            <div className="gain net" key={probe.stat}>
              <span>{capital(probe.stat)}</span>
              <div>
                <GrowBar percent={share * 100} />
              </div>
              <b>{pct(share)}</b>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function WinModelTable({ card }: { card: Card }) {
  return (
    <div className="scroll">
      <table>
        <thead>
          <tr>
            <th className="l">Format</th>
            <th>Network</th>
            <th>Our win model</th>
          </tr>
        </thead>
        <tbody>
          {card.evaluation.result.map((result) => (
            <tr key={result.format}>
              <td className="l">{result.format}</td>
              <td>{num(result.brier, 3)}</td>
              <td>
                <b>{num(card.win_models[`win_prob:${result.format}`], 3)}</b>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SimulatedTable({ rows }: { rows: SimulatedLeague[] }) {
  return (
    <div className="scroll">
      <table>
        <thead>
          <tr>
            <th className="l">First innings</th>
            <th>Real average</th>
            <th>Simulated</th>
            <th>Real spread</th>
            <th>Simulated</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.league}>
              <td className="l">{row.league}</td>
              <td>{num(row.real_mean)}</td>
              <td>{num(row.simulated_mean)}</td>
              <td>{num(row.real_spread)}</td>
              <td>{num(row.simulated_spread)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Shortfall({ card }: { card: Card }) {
  const rows = card.deployed.simulated_vs_real;
  const low =
    rows.reduce((sum, row) => sum + (1 - row.simulated_mean / row.real_mean), 0) / rows.length;
  return (
    <>
      <h2 className="label">Where it falls short</h2>
      <div className="cols2">
        <div>
          <div className="prose small">
            <p>
              <b>It is not the best judge of who wins.</b> The same network also guesses the match
              result. Our older, simpler win models beat it in every format, so they stay in charge of
              win chances across the site. Lower is better.
            </p>
          </div>
          <WinModelTable card={card} />
        </div>
        <div>
          <div className="prose small">
            <p>
              <b>Its innings come up short.</b> Simulated totals spread out like real ones, but average
              about {pct(low)} too low. Small errors on each ball add up over 120 or 300 of them.
            </p>
          </div>
          <SimulatedTable rows={rows} />
        </div>
      </div>
      <p className="note">
        It knows both the batter and the bowler on only {pct(card.evaluation.known_player_share)} of the
        balls it was tested on. New players arrive every season, and it has to treat them as average
        until it has seen 200 of their balls. Test innings cannot be simulated yet.
      </p>
    </>
  );
}

const HOW_BUILT: [title: string, text: string][] = [
  [
    "One question.",
    "What happens on the next ball? Nine answers: dot, 1, 2, 3, 4, 6, wicket, wide or no-ball.",
  ],
  [
    "What it sees.",
    "The score, wickets and overs. The last 24 balls. And a learned vector for the " +
      "batter, the bowler and the ground.",
  ],
  [
    "Split by time.",
    "It learns from balls up to 2023. Settings are chosen on 2024. It is scored " +
      "once, on 2025 and 2026.",
  ],
  [
    "Prove each part.",
    "The same network is trained three times with parts removed, so the table " +
      "shows what each part is worth.",
  ],
  [
    "Python thinks, the browser draws.",
    "Python trains the network and works out every frame you " +
      "see move. The page only plays them back.",
  ],
];

export default async function Lab() {
  let card: Card, players: PlayerMap;
  try {
    [card, players] = await Promise.all([api<Card>("lab"), api<PlayerMap>("lab/players")]);
  } catch (error) {
    if (error instanceof ApiError && error.status === NOT_TRAINED) return <NotTrained />;
    throw error;
  }
  const scores = card.evaluation.scores;
  const trees = scores.find((score) => score.model === "Gradient boosting")!;
  const full = scores.find((score) => score.model === FULL_NETWORK)!;

  return (
    <>
      <p className="kicker">The lab</p>
      <h1 className="page">A neural network learns cricket, one ball at a time</h1>
      <p className="standfirst">
        Nobody told it who the big hitters are. It watched {num(card.deployed.balls / 1e6, 1)} million
        balls and worked that out for itself. Here is what it learned, what it can do, and where it is
        still wrong.
      </p>
      <Facts card={card} />

      <h2 className="label">Watch it learn</h2>
      <p className="note pulled">
        Each dot is a batter. The network gives every batter 48 numbers; this map squashes them to two.
        Before training the dots are scattered at random. Press play and watch fast scorers and slow
        scorers pull apart.
      </p>
      <LabMap data={players} errors={card.deployed.curve.map((epoch) => epoch.train)} />

      <h2 className="label">Ask it</h2>
      <p className="note pulled">
        Pick a batter and a bowler. The bars show what the network expects from the next ball between
        them.
      </p>
      <Matchup />

      <h2 className="label">Watch it play</h2>
      <p className="note pulled">
        The network bats out the rest of an innings 1,000 times, ball by ball. Each line is one of those
        innings. Red lines reached the target. The bars on the right count where they all ended.
      </p>
      <Simulator />

      <h2 className="label">Is it any good?</h2>
      <p className="note pulled">
        Every model was scored on {num(card.evaluation.balls.test)} balls from 2025 and 2026 that none
        of them had seen. The number is its average surprise at what happened: lower is better. The bar
        shows how far each one improves on always guessing the league average.
      </p>
      <ScoreTable scores={scores} />
      <p className="note">
        The full network scores {num(full.all, 3)} against {num(trees.all, 3)} for gradient boosting,
        the usual strong choice for tables of numbers. That gap is small. A single ball of cricket is
        mostly luck, so no model can score much lower.
      </p>

      <h2 className="label">When it says 5%, is it 5%?</h2>
      <p className="note pulled">
        Balls are grouped by the chance the network gave. A dot on the dashed line means that chance
        turned out to be right.
      </p>
      <div className="cols2">
        <Calibration bins={card.evaluation.calibration.wicket} outcome="wicket" />
        <Calibration bins={card.evaluation.calibration.six} outcome="six" />
      </div>

      <h2 className="label">What a batter&apos;s 48 numbers know</h2>
      <p className="note pulled">
        We tried to work out each batter&apos;s real statistics from their 48 numbers alone. The bar is
        how much of the difference between batters they explain.
      </p>
      <Probes probes={players.probes} />
      <p className="note">
        The network learned how fast a batter scores, and how. It learned almost nothing about how long
        they survive.
      </p>

      <Shortfall card={card} />

      <h2 className="label">How it was built</h2>
      <ol className="steps">
        {HOW_BUILT.map(([title, text]) => (
          <li key={title}>
            <b>{title}</b>
            {text}
          </li>
        ))}
      </ol>
    </>
  );
}
