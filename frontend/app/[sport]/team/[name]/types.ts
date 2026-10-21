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
}
