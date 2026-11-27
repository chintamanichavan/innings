// The shape of the team page's answer from the server.

import type { MatchSummary } from "@/lib/types";

export interface Season {
  year: number;
  league: string;
  w: number;
  l: number;
  rf: number;
  ra: number;
}

export interface BestPlayer {
  player_id: string;
  name: string;
  rae: number;
}

export interface TeamPage {
  team: string;
  year: number;
  seasons: Season[];
  elo: { date: string; elo: number }[];
  best: { bat: BestPlayer[]; bowl: BestPlayer[] };
  games: MatchSummary[];
  classics: MatchSummary[];
  lede: string[];
  squad: SquadPlayer[];
  table: TableRow[] | null;
}

export interface SquadPlayer {
  player_id: string;
  name: string;
  role: "Batters" | "Wicketkeepers" | "All-rounders" | "Bowlers";
  matches: number;
  runs: number;
  wickets: number;
}

/** One line of a league's points table. */
export interface TableRow {
  team: string;
  played: number;
  won: number;
  lost: number;
  no_result: number;
  points: number;
  net_run_rate: number;
}

export interface TeamSeason {
  squad: SquadPlayer[];
  table: TableRow[] | null; // only franchise leagues have one
}
