// Shapes the Python server sends that more than one page uses.

import type { Sport } from "./sport";

/** A finished match, as it appears in lists and cards. */
export interface MatchSummary {
  sport: Sport;
  match_id: string;
  date: string;
  league: string;
  team1: string;
  team2: string;
  score1: number | null;
  score2: number | null;
  line1?: string | null; // each side's score as cricket writes it: "155/8 (20 ov)"
  line2?: string | null;
  result?: string | null; // "Royal Challengers Bengaluru won by 5 wickets (12 balls left)"
  art?: "ground" | "stumps" | "six" | "trophy" | null; // the rendered picture behind its card
  winner: string | null;
  thrill?: number | null;
  headline?: string | null;
}

/** One play, with the first team's win chance before and after it. */
export interface WinEvent {
  seq: number;
  period: number;
  wp1: number;
  wp1_post: number;
}

export interface FoundPlayer {
  kind: "player";
  sport: Sport;
  player_id: string;
  name: string;
}

export interface FoundTeam {
  kind: "team";
  sport: Sport;
  team: string;
  pool: string;
}

export type Found = FoundPlayer | FoundTeam;

export interface League {
  sport: Sport;
  league: string;
  first: number;
  last: number;
}

/** Every year a league has data for, newest first. */
export function yearsOf(league: League): number[] {
  const years: number[] = [];
  for (let year = league.last; year >= league.first; year--) years.push(year);
  return years;
}
