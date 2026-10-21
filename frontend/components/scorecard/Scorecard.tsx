// The scorecard section of a match page: pick an innings, read its cards, see its pictures.

"use client";

import { useState } from "react";

import { Cards } from "./Cards";
import { Manhattan, Partnerships, Worm } from "./Graphics";
import { type ScorecardData, inningsName, total } from "./types";

export function Scorecard({ data }: { data: ScorecardData }) {
  const [chosen, setChosen] = useState(0);
  const all = data.innings;
  const innings = all[chosen];
  if (!innings) return null;
  return (
    <section className="scorecard">
      <h2 className="label">Scorecard</h2>
      <div className="pills">
        {all.map((each, index) => (
          <button
            key={each.number}
            className={index === chosen ? "on" : ""}
            onClick={() => setChosen(index)}
          >
            {inningsName(each, all)} · {total(each)}
          </button>
        ))}
      </div>
      <Cards innings={innings} />

      <h2 className="label">The match in pictures</h2>
      <div className="cols2">
        <figure>
          <figcaption className="kicker quiet">
            The worm: each side&apos;s score, over by over
          </figcaption>
          <Worm all={all} />
        </figure>
        <figure>
          <figcaption className="kicker quiet">
            Runs in each over: {inningsName(innings, all)}
          </figcaption>
          {/* Keyed by innings so the bars grow again when the reader picks another one. */}
          <Manhattan key={innings.number} innings={innings} all={all} />
        </figure>
      </div>
      <figure>
        <figcaption className="kicker quiet">Partnerships: {inningsName(innings, all)}</figcaption>
        <div className="panel">
          <Partnerships key={innings.number} innings={innings} />
        </div>
      </figure>
    </section>
  );
}
