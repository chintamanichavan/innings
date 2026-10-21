// The shape of the leaderboard the server sends.

import type { Column } from "@/lib/format";

/** A row also carries one number per column; StatTable reads those by column key. */
export interface LeaderRow {
  player_id: string;
  name: string;
  team: string;
  rae: number;
}

export interface Leaders {
  sort: string;
  min_opps: number;
  columns: Column[];
  rows: LeaderRow[];
}
