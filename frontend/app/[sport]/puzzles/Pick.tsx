// You vs the model: ten real past games. You pick the winner; so did the model, beforehand.

"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Marked } from "@/components/Marked";
import { Crest } from "@/components/teams";
import { api } from "@/lib/api";
import { day, num, pct } from "@/lib/format";
import { type Sport, link } from "@/lib/sport";
import { store, useStored } from "@/lib/store";

import type { PickGame } from "./types";

interface Lifetime {
  you: number;
  model: number;
  n: number;
}

const NO_GAMES: Lifetime = { you: 0, model: 0, n: 0 };

function RoundOver({
  you,
  model,
  games,
  all,
  onAgain,
}: {
  you: number;
  model: number;
  games: number;
  all: Lifetime;
  onAgain: () => void;
}) {
  let verdict = "The model wins this round";
  if (you > model) verdict = "You beat the model";
  if (you === model) verdict = "A draw with the model";
  return (
    <>
      <p className="verdict">{verdict}</p>
      <div className="tiles">
        <div className="tile">
          <b>
            {you}/{games}
          </b>
          <span>you</span>
        </div>
        <div className="tile">
          <b>
            {model}/{games}
          </b>
          <span>the model</span>
        </div>
        <div className="tile">
          <b>
            {all.you}–{all.model}
          </b>
          <span>all time, over {all.n} games</span>
        </div>
      </div>
      <button className="btn" onClick={onAgain}>
        New round
      </button>
    </>
  );
}

interface TeamButtonProps {
  game: PickGame;
  team: string;
  chosen: string | null;
  onPick: (team: string) => void;
}

function TeamButton({ game, team, chosen, onPick }: TeamButtonProps) {
  const score = team === game.team1 ? game.score1 : game.score2;
  const won = game.winner === team;
  const classes = [chosen === team ? "chosen" : "", chosen && won ? "right" : ""].join(" ");
  return (
    <button className={classes} disabled={chosen !== null} onClick={() => onPick(team)}>
      <Crest team={team} size="lg" />
      <span>{team}</span>
      {chosen && (
        <span className="sub small">
          {num(score)}
          {won ? " · won" : ""}
        </span>
      )}
    </button>
  );
}

function VerdictLine({
  sport,
  game,
  chosen,
  modelPick,
}: {
  sport: Sport;
  game: PickGame;
  chosen: string;
  modelPick: string;
}) {
  const word = (right: boolean) => (right ? "right" : "wrong");
  const confidence = pct(Math.max(game.p_model, 1 - game.p_model));
  const sentence =
    `You picked ${chosen}: ${word(chosen === game.winner)}. ` +
    `The model gave ${modelPick} ${confidence}: ${word(modelPick === game.winner)}.`;
  return (
    <p className="prose small">
      <Marked text={sentence} />{" "}
      <Link className="u" href={link(sport, "match", game.match_id)}>
        Read the game
      </Link>
    </p>
  );
}

export function YouVsModel({ sport }: { sport: Sport }) {
  const [games, setGames] = useState<PickGame[] | null>(null);
  const [at, setAt] = useState(0);
  const [you, setYou] = useState(0);
  const [model, setModel] = useState(0);
  const [chosen, setChosen] = useState<string | null>(null);
  const lifetimeKey = `pick.${sport}`;
  const all = useStored(lifetimeKey, NO_GAMES);

  useEffect(() => {
    api<PickGame[]>("game/pick", { sport }).then(setGames);
  }, [sport]);

  if (!games) return null;

  const newRound = async () => {
    const fresh = await api<PickGame[]>("game/pick", { sport });
    setGames(fresh);
    setAt(0);
    setYou(0);
    setModel(0);
  };

  if (at >= games.length) {
    return <RoundOver you={you} model={model} games={games.length} all={all} onAgain={newRound} />;
  }

  const game = games[at];
  const modelPick = game.p_model >= 0.5 ? game.team1 : game.team2;
  const battedFirst = `${game.team1} batted first.`;
  const nextLabel = at + 1 < games.length ? "Next game" : "See the result";

  const pick = (team: string) => {
    const youWereRight = team === game.winner;
    const modelWasRight = modelPick === game.winner;
    setChosen(team);
    setYou(you + Number(youWereRight));
    setModel(model + Number(modelWasRight));
    const saved = store.get(lifetimeKey, NO_GAMES);
    store.set(lifetimeKey, {
      you: saved.you + Number(youWereRight),
      model: saved.model + Number(modelWasRight),
      n: saved.n + 1,
    });
  };

  const advance = () => {
    setChosen(null);
    setAt(at + 1);
  };

  return (
    <>
      <p className="standfirst">
        Real past games. Pick the winner. The model made its call before the game, without seeing the
        result.
      </p>
      <div className="meta">
        <span className="chip">
          Game {at + 1} of {games.length}
        </span>
        <span>You {you}</span>
        <span>Model {model}</span>
      </div>
      <p className="kicker spaced">
        {day(game.date)} <span className="sep">{game.league}</span>
      </p>
      <p className="sub">{[game.venue || "", battedFirst].filter(Boolean).join(". ")}</p>
      <div className="pickrow">
        {[game.team1, game.team2].map((team) => (
          <TeamButton key={team} game={game} team={team} chosen={chosen} onPick={pick} />
        ))}
      </div>
      {chosen && <VerdictLine sport={sport} game={game} chosen={chosen} modelPick={modelPick} />}
      {chosen && (
        <button className="btn" onClick={advance}>
          {nextLabel}
        </button>
      )}
    </>
  );
}
