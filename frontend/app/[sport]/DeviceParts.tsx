// The front page's panels that depend on this device: followed teams and players, puzzle streak.

"use client";

import Link from "next/link";

import { StoryCard } from "@/components/matches";
import { type Sport, link } from "@/lib/sport";
import { type FollowedPlayer, today, useStored } from "@/lib/store";

import { useLatest } from "./useLatest";

/** The newest match of each followed team, with the "Top story" label that follows them. */
export function YourTeams({ sport }: { sport: Sport }) {
  const latest = useLatest(sport);
  if (!latest?.length) return null;
  return (
    <>
      <h2 className="label">Your teams</h2>
      <div className="cols3">
        {latest.map((item) => (
          <StoryCard key={item.team} match={item.match} label={item.team} />
        ))}
      </div>
      <h2 className="label">Top story</h2>
    </>
  );
}

interface Streak {
  n: number;
  best: number;
}
interface DayGame {
  day?: string;
  done?: boolean;
  won?: boolean;
}

function puzzleBlurb(playedToday: boolean, game: DayGame): string {
  if (!playedToday) return "Six clues, one player. New every day.";
  return game.won
    ? "Solved today. A new player arrives tomorrow."
    : "Today's player got away. Try again tomorrow.";
}

export function PuzzlePanel({ sport }: { sport: Sport }) {
  const streak = useStored<Streak>(`who.${sport}.streak`, { n: 0, best: 0 });
  const game = useStored<DayGame>(`who.${sport}.day`, {});
  const playedToday = game.day === today() && !!game.done;
  return (
    <div className="panel puzzle">
      <p className="kicker quiet">Puzzle corner</p>
      <h3>Who am I?</h3>
      <p>{puzzleBlurb(playedToday, game)}</p>
      <div className="row">
        <Link className="btn sm" href={link(sport, "puzzles", "who")}>
          {playedToday ? "See today's answer" : "Play today's puzzle"}
        </Link>
        <span className="sub small">
          Streak <b>{streak.n}</b> · best {streak.best}
        </span>
      </div>
      <p className="note">
        <Link className="u" href={link(sport, "puzzles", "hl")}>
          Higher or lower
        </Link>{" "}
        ·{" "}
        <Link className="u" href={link(sport, "puzzles", "pick")}>
          You vs the model
        </Link>
      </p>
    </div>
  );
}

export function FollowedPlayerLinks({ sport }: { sport: Sport }) {
  const players = useStored<FollowedPlayer[]>("follows", []).filter((player) => player.sport === sport);
  if (!players.length) return null;
  return (
    <>
      <h2 className="label">Players you follow</h2>
      <div className="pills">
        {players.map((player) => (
          <Link key={player.id} href={link(sport, "player", player.id)}>
            {player.name}
          </Link>
        ))}
      </div>
    </>
  );
}
