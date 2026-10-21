// The stream: one IPL season played 100,000 times on a graphics card, every ball sent through
// Kafka into a data lake. Below it, the same idea at the pace of a real match.

import type { Metadata } from "next";

import { GrowBar } from "@/components/motion";
import { api } from "@/lib/api";
import { num } from "@/lib/format";
import { type SeasonData, bigNumber } from "@/lib/season";
import type { BenchRun, Snapshot } from "@/lib/stream";

import { LiveBoard } from "./LiveBoard";
import { Season } from "./Season";

export const metadata: Metadata = {
  title: "The stream",
  description: "One IPL season played 100,000 times: 1.8 billion balls through Kafka into a data lake.",
};

/** Balls a second with one, two or more scorers sharing the work. */
function SpeedTest({ runs }: { runs: BenchRun[] }) {
  const fastest = Math.max(...runs.map((run) => run.per_second));
  return (
    <div className="panel">
      <div className="gains">
        {runs.map((run) => (
          <div className="gain net" key={run.scorers}>
            <span>
              {run.scorers} {run.scorers === 1 ? "scorer" : "scorers"}
            </span>
            <div>
              <GrowBar percent={(run.per_second / fastest) * 100} />
            </div>
            <b>{num(run.per_second)}</b>
          </div>
        ))}
      </div>
    </div>
  );
}

const HOW_BUILT: [title: string, text: string][] = [
  [
    "A real season, replayed.",
    "The 70 league matches keep their real grounds, batting orders and bowlers. Playoffs follow each table.",
  ],
  [
    "A graphics card bowls.",
    "The neural network from the lab plays 70,000 innings at once, one ball in all of them at each step.",
  ],
  [
    "A match is 729 bytes.",
    "One byte for what each ball was, one for who faced it. A message a ball would be far too many.",
  ],
  [
    "Kafka sits in the middle.",
    "The simulator only writes to Kafka. The writers and the tally only read. None waits for another.",
  ],
  [
    "Six writers, six lanes.",
    "The topic has six partitions. Each writer owns one and unpacks its matches into rows, all at once.",
  ],
  [
    "The lake is a star.",
    "One huge table of balls holds short numbers. They point into tiny tables of people, teams and outcomes.",
  ],
  [
    "Count it three ways.",
    "The simulator, the tally and the lake each count the balls. If they differ, something was lost.",
  ],
];

function Shortfall() {
  return (
    <>
      <h2 className="label">Where it falls short</h2>
      <div className="prose small">
        <p>
          <b>These balls were never bowled.</b> Cricket has about five million real balls on record,
          which is not big data. The volume here is made by a model. The pipeline is real; the cricket
          is imagined.
        </p>
        <p>
          <b>The model is too wild at the edges.</b> Its average innings is a little low, yet its best
          innings beat every real record. Read the title odds as a fair guide and the records as fun.
        </p>
        <p>
          <b>It knows some players only as &ldquo;unknown&rdquo;.</b> A player with fewer than 200 balls
          on record gets an average vector. New signings are treated alike.
        </p>
        <p>
          <b>Some of cricket is left out.</b> The toss is a coin. A tie is a coin. Every wicket falls to
          the striker and goes to the bowler. Nobody is injured, rested or dropped.
        </p>
        <p>
          <b>There is one Kafka broker, on one machine.</b> A real system runs several and keeps copies,
          so that losing a machine loses nothing.
        </p>
      </div>
    </>
  );
}

function SwitchedOff() {
  return (
    <p className="note">
      The stream is switched off on this server. <code>docker compose up -d</code> starts Kafka, the
      bowler and the scorer.
    </p>
  );
}

export default async function Stream() {
  const [season, snapshot] = await Promise.all([api<SeasonData>("season"), api<Snapshot>("stream")]);
  const runs = snapshot.bench;
  const checked = runs.length ? Math.max(...runs.map((run) => run.checked)) : 0;
  const exact = runs.every((run) => run.worst_difference === 0);
  const tally = season.tally;

  return (
    <>
      <p className="kicker">The stream</p>
      <h1 className="page">
        {tally
          ? `IPL ${tally.year}, played ${num(tally.target)} times`
          : "A season, played 100,000 times"}
      </h1>
      <p className="standfirst">
        {tally?.real.champion ?? "One team"} won the real one. Was that likely, or lucky? We let the
        neural network play the whole season again and again. Every ball went through Kafka into a data
        lake{tally ? `: ${bigNumber(tally.balls)} of them` : ""}.
      </p>
      <Season initial={season} />

      <h2 className="label">How it was built</h2>
      <ol className="steps">
        {HOW_BUILT.map(([title, text]) => (
          <li key={title}>
            <b>{title}</b>
            {text}
          </li>
        ))}
      </ol>

      <Shortfall />

      <h2 className="label">The same stream, at match pace</h2>
      <p className="note pulled">
        The season above was a batch: as fast as the machine could go. This is the other kind of stream.
        Famous close matches are replayed one ball a second, and each ball is scored as it lands.
      </p>
      {snapshot.on ? <LiveBoard initial={snapshot} /> : <SwitchedOff />}

      {runs.length > 0 && (
        <>
          <h2 className="label">How fast can the scorer go?</h2>
          <p className="note pulled">
            We sent {num(runs[0].matches)} real matches through as fast as they would go, one message a
            ball. The number is balls scored each second.
          </p>
          <SpeedTest runs={runs} />
          <p className="note">
            All {num(checked)} answers were then checked against the nightly build.{" "}
            {exact ? "Every one matched exactly." : "Not every one matched."} Each scorer was held to
            one processor core, so that adding scorers is a fair test.
          </p>
        </>
      )}
    </>
  );
}
