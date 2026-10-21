// The puzzle corner. Three games, one per file; this page picks which to show.

import { Pills } from "@/components/controls";
import { type Sport, link } from "@/lib/sport";

import { HigherOrLower } from "./HigherLower";
import { YouVsModel } from "./Pick";
import { WhoAmI } from "./Who";

const GAMES = {
  who: { title: "Who am I?", Play: WhoAmI },
  hl: { title: "Higher or lower", Play: HigherOrLower },
  pick: { title: "You vs the model", Play: YouVsModel },
};

type GameKey = keyof typeof GAMES;

const isGame = (key: string): key is GameKey => key in GAMES;

/** The title of the game at this address; an unknown game shows the first. */
export function gameTitle(arg: string): string {
  return GAMES[isGame(arg) ? arg : "who"].title;
}

export function PuzzleCorner({ sport, arg }: { sport: Sport; arg: string }) {
  const key = isGame(arg) ? arg : "who";
  const { title, Play } = GAMES[key];
  const tabs = (Object.keys(GAMES) as GameKey[]).map((name): [string, string, string] => [
    name,
    GAMES[name].title,
    link(sport, "puzzles", name),
  ]);
  return (
    <>
      <p className="kicker">Puzzle corner</p>
      <h1 className="page">{title}</h1>
      <Pills items={tabs} current={key} />
      <div className="game">
        <Play key={sport} sport={sport} />
      </div>
    </>
  );
}
