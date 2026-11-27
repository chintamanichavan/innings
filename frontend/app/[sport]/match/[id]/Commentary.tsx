// Every ball of the match, over by over, as commentary prints it. Each over ends with the
// runs it gave, the score, the batters in and the bowler's figures.

"use client";

import { useState } from "react";

import type { CommentaryData, CommentaryOver } from "./types";

const ORDINAL = ["1st", "2nd", "3rd", "4th"];

function Over({ over }: { over: CommentaryOver }) {
  const end = over.end;
  return (
    <div className="c-over">
      <div className="c-end">
        <b>Over {over.over}</b>
        <span>
          {end.runs} run{end.runs === 1 ? "" : "s"} · {end.score}
        </span>
        <span className="dim">
          {end.batters.map((batter) => `${batter.name} ${batter.runs} (${batter.balls})`).join(" · ")}
          {end.bowler && ` · ${end.bowler.name} ${end.bowler.figures}`}
        </span>
      </div>
      {/* Newest ball first, as commentary reads. */}
      {[...over.balls].reverse().map((ball, index) => (
        <div key={index} className={`c-ball ${ball.wicket ? "out" : ""}`}>
          <span className="c-at">{ball.at}</span>
          <i className={`ball b-${ball.mark.replace(/^\d+/, "") || ball.mark}`}>{ball.mark}</i>
          <p>
            {ball.text}
            {ball.wicket && <span className="c-wicket">{ball.wicket}</span>}
          </p>
          {ball.swing != null && (
            <span
              className={`c-swing ${ball.swing > 0 ? "up" : "down"}`}
              title="Change in the batting side's win chance"
            >
              {ball.swing > 0 ? "+" : "−"}
              {Math.round(Math.abs(ball.swing) * 100)}%
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

export function Commentary({ data }: { data: CommentaryData }) {
  const [chosen, setChosen] = useState(data.innings.length - 1); // the latest innings first
  const innings = data.innings[chosen];
  const sides = data.innings.map((each) => each.team);
  const name = (index: number) => {
    const each = data.innings[index];
    const twice = sides.filter((team) => team === each.team).length > 1;
    return twice
      ? `${each.team}, ${ORDINAL[sides.slice(0, index).filter((t) => t === each.team).length]} innings`
      : each.team;
  };
  return (
    <section className="commentary">
      <div className="pills">
        {data.innings.map((each, index) => (
          <button
            key={each.number}
            className={index === chosen ? "on" : ""}
            onClick={() => setChosen(index)}
          >
            {name(index)}
          </button>
        ))}
      </div>
      <p className="note">
        Latest over first. A percentage marks a ball that moved the batting side&apos;s chance of
        winning by 8 points or more.
      </p>
      <div className="c-overs">
        {[...innings.overs].reverse().map((over) => (
          <Over key={over.over} over={over} />
        ))}
      </div>
    </section>
  );
}
