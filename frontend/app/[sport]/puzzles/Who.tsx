// Who am I? One player a day, six clues. Each wrong guess opens the next clue.

"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { SkillBars } from "@/components/charts/small";
import { SearchBox } from "@/components/SearchBox";
import { StatTable } from "@/components/StatTable";
import { PlayerLink } from "@/components/teams";
import { api } from "@/lib/api";
import { SPORTS, type Sport, link } from "@/lib/sport";
import { store, today, useOnDevice, useStored } from "@/lib/store";
import { toast } from "@/lib/toast";
import type { Found } from "@/lib/types";

import type { Answer, Daily, GuessResult, Hint } from "./types";

interface Game {
  day: string;
  shown: number;
  guesses: string[];
  done: boolean;
  won: boolean;
  answer: Answer | null;
}

interface Streak {
  n: number;
  best: number;
}

const freshGame = (day: string): Game => ({
  day,
  shown: 1,
  guesses: [],
  done: false,
  won: false,
  answer: null,
});

function recordResult(sport: Sport, won: boolean) {
  const key = `who.${sport}.streak`;
  const streak = store.get<Streak>(key, { n: 0, best: 0 });
  const n = won ? streak.n + 1 : 0;
  store.set(key, { n, best: Math.max(streak.best, n) });
}

function Clue({ hint }: { hint: Hint }) {
  let body;
  if (hint.text) body = <div className="say">{hint.text}</div>;
  else if (hint.columns && hint.row) {
    body = <StatTable columns={hint.columns} rows={[hint.row]} rowKey={() => "row"} />;
  } else if (hint.profile?.length) body = <SkillBars skills={hint.profile} />;
  else body = <div className="say">Not enough games for a profile.</div>;
  return (
    <div className="hint">
      <div className="cap">{hint.title}</div>
      {body}
    </div>
  );
}

/** The result as text to paste anywhere: one black square per miss, a green one for the hit. */
function shareText(sport: Sport, game: Game, total: number): string {
  const squares = "⬛".repeat(game.guesses.length) + (game.won ? "🟩" : "");
  const score = game.won ? `${game.guesses.length + 1}/${total}` : `X/${total}`;
  return [
    `Innings · Who am I? ${game.day} · ${SPORTS[sport]}`,
    `${score} ${squares}`,
    location.origin + link(sport, "puzzles", "who"),
  ].join("\n");
}

async function shareResult(text: string) {
  try {
    if (navigator.share) await navigator.share({ text });
    else {
      await navigator.clipboard.writeText(text);
      toast("Result copied");
    }
  } catch {
    // The reader closed the share sheet.
  }
}

function Finished({ sport, game, total }: { sport: Sport; game: Game; total: number }) {
  const verdict = game.won ? `Got it in ${game.guesses.length + 1}` : "Out of guesses";
  return (
    <>
      <p className="verdict">{verdict}</p>
      {game.answer && (
        <h2>
          <PlayerLink sport={sport} id={game.answer.player_id} name={game.answer.name} />
        </h2>
      )}
      <p className="row spaced">
        <button className="btn" onClick={() => shareResult(shareText(sport, game, total))}>
          Share result
        </button>
        <Link className="btn alt" href={link(sport, "puzzles", "hl")}>
          Play higher or lower
        </Link>
      </p>
      <p className="note">A new player arrives tomorrow.</p>
    </>
  );
}

/** Today's game: the saved one if it is from today, else a fresh one. */
function useTodaysGame(sport: Sport): Game {
  const saved = useStored<Partial<Game>>(`who.${sport}.day`, {});
  return saved.day === today() ? (saved as Game) : freshGame(today());
}

function WhoGame({ sport }: { sport: Sport }) {
  const game = useTodaysGame(sport);
  const streak = useStored<Streak>(`who.${sport}.streak`, { n: 0, best: 0 });
  const [puzzle, setPuzzle] = useState<Daily | null>(null);

  useEffect(() => {
    let current = true;
    api<Daily>("game/daily", { sport, shown: game.shown, day: game.day }).then((daily) => {
      if (current) setPuzzle(daily);
    });
    return () => {
      current = false;
    };
  }, [sport, game.shown, game.day]);

  if (!puzzle) return null;
  const total = puzzle.total;

  const guess = async (found: Found) => {
    if (found.kind !== "player") return;
    const isLastGuess = game.guesses.length + 1 >= total;
    const result = await api<GuessResult>("game/guess", {
      sport,
      player_id: found.player_id,
      day: game.day,
      last: String(isLastGuess),
    });
    const key = `who.${sport}.day`;
    if (result.correct || isLastGuess) {
      const guesses = result.correct ? game.guesses : [...game.guesses, found.name];
      const finished = { done: true, won: result.correct, answer: result.answer, shown: total };
      store.set(key, { ...game, guesses, ...finished });
      recordResult(sport, result.correct);
    } else {
      const shown = Math.min(total, game.shown + 1);
      store.set(key, { ...game, guesses: [...game.guesses, found.name], shown });
      toast("Not this player. Here is another clue.");
    }
  };

  return (
    <>
      <p className="standfirst">
        Guess today&apos;s {SPORTS[sport].toLowerCase()} player. Each wrong guess opens a new clue. You
        get {total} guesses.
      </p>
      <div className="meta">
        <span className="chip">Streak {streak.n}</span>
        <span>Best {streak.best}</span>
        <span>
          Clue {Math.min(game.shown, total)} of {total}
        </span>
      </div>
      {puzzle.hints.map((hint) => (
        <Clue key={hint.title} hint={hint} />
      ))}
      {game.guesses.length > 0 && (
        <div className="pills">
          {game.guesses.map((name) => (
            <span className="chip" key={name}>
              ✕ {name}
            </span>
          ))}
        </div>
      )}
      {game.done ? (
        <Finished sport={sport} game={game} total={total} />
      ) : (
        <SearchBox placeholder="Type a player's name" sport={sport} inline onPick={guess} />
      )}
    </>
  );
}

/** Waits for the device, since today's game and the streak live there. */
export function WhoAmI({ sport }: { sport: Sport }) {
  return useOnDevice() ? <WhoGame sport={sport} /> : null;
}
