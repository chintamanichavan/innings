// What /api/scorecard/<match> sends. See src/innings/web/scorecard.py.

export interface BattingLine {
  player_id: string;
  name: string;
  runs: number;
  balls: number;
  fours: number;
  sixes: number;
  strike_rate: number | null;
  out: boolean;
  how: string; // "c Smith b Starc", or "not out"
}

export interface BowlingLine {
  player_id: string;
  name: string;
  overs: string; // as cricket writes it: "3.4"
  maidens: number;
  runs: number;
  wickets: number;
  economy: number | null;
  wides: number;
  no_balls: number;
}

export interface FallOfWicket {
  wicket: number;
  score: number;
  name: string;
  over: string;
}

export interface Partnership {
  wicket: number;
  runs: number;
  balls: number;
  batters: { name: string; runs: number }[];
}

/** One over: its runs and wickets, and the score when it ended. */
export interface Over {
  over: number;
  runs: number;
  wickets: number;
  score: number;
}

export interface InningsCard {
  number: number;
  team: string;
  runs: number;
  wickets: number;
  overs: string;
  target: number | null;
  batting: BattingLine[];
  did_not_bat: string[];
  bowling: BowlingLine[];
  extras: { total: number; byes: number; wides: number; no_balls: number };
  fall_of_wickets: FallOfWicket[];
  partnerships: Partnership[];
  by_over: Over[];
}

export interface ScorecardData {
  innings: InningsCard[];
}

const ALL_OUT = 10;

/** "351/7", or "187" when the side was bowled out. */
export function total(innings: InningsCard): string {
  return innings.wickets >= ALL_OUT ? String(innings.runs) : `${innings.runs}/${innings.wickets}`;
}

/** "India", or "India, 2nd innings" when a side bats twice. */
export function inningsName(innings: InningsCard, all: InningsCard[]): string {
  const sameSide = all.filter((other) => other.team === innings.team);
  if (sameSide.length < 2) return innings.team;
  return `${innings.team}, ${sameSide.indexOf(innings) === 0 ? "1st" : "2nd"} innings`;
}
