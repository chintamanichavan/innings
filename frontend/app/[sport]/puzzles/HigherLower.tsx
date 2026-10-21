// Higher or lower: did the second player have more of a stat than the first?
// A right answer keeps the run going; a wrong one ends it.

"use client";

import { useCallback, useEffect, useState } from "react";

import { Crest } from "@/components/teams";
import { api } from "@/lib/api";
import { num } from "@/lib/format";
import type { Sport } from "@/lib/sport";
import { store, useStored } from "@/lib/store";

import type { HigherLowerRound, SeasonCard } from "./types";

const REVEAL_MS = 900; // how long the answer stays up before the next pair

type Phase = "asking" | "right" | "over";

function Season({
  season,
  metric,
  revealed,
}: {
  season: SeasonCard;
  metric: string;
  revealed: boolean;
}) {
  return (
    <div className="panel">
      <Crest team={season.team} size="lg" />
      <h3 className="spaced">{season.name}</h3>
      <div className="sub">
        {season.year} · {season.team}
      </div>
      <div className="big">{revealed ? num(season.value) : "?"}</div>
      <div className="sub">{metric}</div>
    </div>
  );
}

function Controls({
  phase,
  run,
  onGuess,
  onAgain,
}: {
  phase: Phase;
  run: number;
  onGuess: (guess: number) => void;
  onAgain: () => void;
}) {
  if (phase === "over") {
    return (
      <>
        <p className="verdict">Run over at {run}</p>
        <button className="btn" onClick={onAgain}>
          Play again
        </button>
      </>
    );
  }
  if (phase === "right") return <p className="verdict">Correct</p>;
  return (
    <div className="pickrow">
      <button onClick={() => onGuess(1)}>Higher</button>
      <button onClick={() => onGuess(-1)}>Lower</button>
    </div>
  );
}

export function HigherOrLower({ sport }: { sport: Sport }) {
  const [round, setRound] = useState<HigherLowerRound | null>(null);
  const [at, setAt] = useState(0); // index of the known card; the next one is the question
  const [run, setRun] = useState(0);
  const [phase, setPhase] = useState<Phase>("asking");
  const bestKey = `hl.${sport}.best`;
  const best = useStored(bestKey, 0);

  const fetchRound = useCallback(() => api<HigherLowerRound>("game/higher-lower", { sport }), [sport]);

  useEffect(() => {
    fetchRound().then(setRound);
  }, [fetchRound]);

  // After a right answer, show it briefly, then move to the next pair (or deal a new set).
  useEffect(() => {
    if (phase !== "right" || !round) return;
    const timer = setTimeout(async () => {
      if (at + 2 >= round.cards.length) {
        setRound(await fetchRound());
        setAt(0);
      } else setAt(at + 1);
      setPhase("asking");
    }, REVEAL_MS);
    return () => clearTimeout(timer);
  }, [phase, round, at, fetchRound]);

  if (!round) return null;
  const { cards, metric } = round;

  const answer = (guess: number) => {
    const difference = Math.sign(cards[at + 1].value - cards[at].value);
    const right = difference === 0 || difference === guess; // a tie counts either way
    if (!right) {
      setPhase("over");
      return;
    }
    setRun(run + 1);
    if (run + 1 > best) store.set(bestKey, run + 1);
    setPhase("right");
  };

  const restart = async () => {
    const fresh = await fetchRound();
    setRound(fresh);
    setAt(0);
    setRun(0);
    setPhase("asking");
  };

  return (
    <>
      <p className="standfirst">
        Did the second player have more or fewer {metric} that season? Keep the run alive.
      </p>
      <div className="meta">
        <span className="chip">Run {run}</span>
        <span>Best {best}</span>
      </div>
      <div className="duel">
        <Season season={cards[at]} metric={metric} revealed />
        <div className="vs">or</div>
        <Season season={cards[at + 1]} metric={metric} revealed={phase !== "asking"} />
      </div>
      <Controls phase={phase} run={run} onGuess={answer} onAgain={restart} />
    </>
  );
}
