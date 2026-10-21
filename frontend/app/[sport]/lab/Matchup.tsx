// "Ask it": what the network expects on one ball between a batter and a bowler, beside what
// it expects from two players it knows nothing about.

"use client";

import { useEffect, useState } from "react";

import { Marked } from "@/components/Marked";
import { SearchBox } from "@/components/SearchBox";
import { api } from "@/lib/api";
import { capital, num, pct } from "@/lib/format";
import type { FoundPlayer } from "@/lib/types";

import type { MatchupAnswer } from "./types";

const PHASES = [
  ["start", "Early"],
  ["middle", "Middle"],
  ["end", "Late"],
] as const;
const FORMATS = ["T20", "ODI", "Test"];
// A famous pair to start with, so the panel is not empty.
const FIRST_BATTER = "Virat Kohli";
const FIRST_BOWLER = "Jasprit Bumrah";

type Phase = (typeof PHASES)[number][0];

async function findCricketer(name: string): Promise<FoundPlayer | null> {
  const found = await api<{ players: Omit<FoundPlayer, "kind">[] }>("find", { term: name });
  const player = found.players.find((candidate) => candidate.sport === "ck");
  return player ? { kind: "player", ...player } : null;
}

function sentence({ batter, bowler, pair, average }: MatchupAnswer): string {
  return (
    `${batter.name} against ${bowler.name}: ${num(pair.runs_per_ball, 2)} runs a ball ` +
    `and a ${pct(pair.wicket)} chance of a wicket. Two unknown players in the same spot: ` +
    `${num(average.runs_per_ball, 2)} runs a ball and ${pct(average.wicket)}.`
  );
}

function caveat({ batter, bowler }: MatchupAnswer): string {
  const unknown = [batter, bowler].filter((player) => !player.known).map((player) => player.name);
  if (!unknown.length) return "";
  return (
    ` The network has seen too little of ${unknown.join(" and ")} to know them, so it treats` +
    " them as average."
  );
}

/** One bar for the pair over a thinner one for two unknown players. Widths slide when they change. */
function Bars({ answer }: { answer: MatchupAnswer }) {
  const highest = Math.max(...answer.pair.chances, ...answer.average.chances);
  return (
    <div className="bars">
      {answer.outcomes.map((name, index) => (
        <div className="bar-row" key={name}>
          <span>{capital(name)}</span>
          <div className="bar-pair">
            <i className="pair" style={{ width: `${(answer.pair.chances[index] / highest) * 100}%` }} />
            <i
              className="avg"
              style={{ width: `${(answer.average.chances[index] / highest) * 100}%` }}
            />
          </div>
          <b>{pct(answer.pair.chances[index])}</b>
        </div>
      ))}
    </div>
  );
}

export function Matchup() {
  const [batter, setBatter] = useState<FoundPlayer | null>(null);
  const [bowler, setBowler] = useState<FoundPlayer | null>(null);
  const [fmt, setFmt] = useState("T20");
  const [phase, setPhase] = useState<Phase>("end");
  const [answer, setAnswer] = useState<MatchupAnswer | null>(null);

  useEffect(() => {
    Promise.all([findCricketer(FIRST_BATTER), findCricketer(FIRST_BOWLER)]).then(([first, second]) => {
      setBatter((current) => current ?? first);
      setBowler((current) => current ?? second);
    });
  }, []);

  useEffect(() => {
    if (!batter || !bowler) return;
    let current = true; // a slow answer must not replace a newer one
    api<MatchupAnswer>("lab/matchup", {
      batter: batter.player_id,
      bowler: bowler.player_id,
      fmt,
      phase,
    }).then((next) => current && setAnswer(next));
    return () => {
      current = false;
    };
  }, [batter, bowler, fmt, phase]);

  return (
    <div className="panel">
      <div className="filters">
        <SearchBox
          inline
          sport="ck"
          playersOnly
          placeholder="A batter"
          shown={batter?.name}
          onPick={(found) => found.kind === "player" && setBatter(found)}
        />
        <span className="sub">facing</span>
        <SearchBox
          inline
          sport="ck"
          playersOnly
          placeholder="A bowler"
          shown={bowler?.name}
          onPick={(found) => found.kind === "player" && setBowler(found)}
        />
        <select aria-label="Format" value={fmt} onChange={(event) => setFmt(event.target.value)}>
          {FORMATS.map((name) => (
            <option key={name}>{name}</option>
          ))}
        </select>
        <div className="seg">
          {PHASES.map(([key, name]) => (
            <button key={key} className={key === phase ? "on" : ""} onClick={() => setPhase(key)}>
              {name}
            </button>
          ))}
        </div>
      </div>
      {answer && <Bars answer={answer} />}
      <div className="legend">
        <span>
          <i style={{ background: "var(--series-1)" }} />
          This pair
        </span>
        <span>
          <i style={{ background: "var(--ink-3)" }} />
          Two unknown players, same moment
        </span>
      </div>
      <p className="prose small">
        {answer ? (
          <>
            <Marked text={sentence(answer)} />
            {caveat(answer)}
          </>
        ) : (
          "Choose a batter and a bowler."
        )}
      </p>
    </div>
  );
}
