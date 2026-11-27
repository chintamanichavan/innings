// The graphs tab of a match: the worm, the run rate, and for one innings the Manhattan and
// the partnerships.

"use client";

import { useState } from "react";

import { Manhattan, Partnerships, RunRate, Worm } from "./Graphics";
import { InningsPills } from "./InningsPills";
import { type ScorecardData, inningsName } from "./types";

export function MatchGraphs({ data }: { data: ScorecardData }) {
  const [chosen, setChosen] = useState(0);
  const all = data.innings;
  const innings = all[chosen];
  if (!innings) return null;
  return (
    <section className="scorecard">
      <div className="cols2">
        <figure>
          <figcaption className="kicker quiet">
            The worm: each side&apos;s score, over by over
          </figcaption>
          <Worm all={all} />
        </figure>
        <figure>
          <figcaption className="kicker quiet">Run rate: runs an over, so far</figcaption>
          <RunRate all={all} />
        </figure>
      </div>
      <h2 className="label">One innings</h2>
      <InningsPills all={all} chosen={chosen} choose={setChosen} />
      <div className="cols2">
        <figure>
          <figcaption className="kicker quiet">
            Runs in each over: {inningsName(innings, all)}
          </figcaption>
          {/* Keyed by innings so the bars grow again when the reader picks another one. */}
          <Manhattan key={innings.number} innings={innings} all={all} />
        </figure>
        <figure>
          <figcaption className="kicker quiet">Partnerships: {inningsName(innings, all)}</figcaption>
          <div className="panel">
            <Partnerships key={innings.number} innings={innings} />
          </div>
        </figure>
      </div>
    </section>
  );
}
