// The shapes of the player page's three answers from the server.

import type { Column } from "@/lib/format";

export type Role = "bat" | "bowl";

export interface SeasonRow {
  year: number | string; // the career total row says "Career"
  league: string;
  team: string;
}

export interface RoleTable {
  columns: Column[];
  rows: SeasonRow[];
  total: SeasonRow;
}

export interface Basics {
  name: string;
  roles: Partial<Record<Role, RoleTable>>;
}

export interface Dimension {
  label: string;
  pct: number;
}

export interface Profile {
  role: Role;
  fmt: string;
  n: number;
  dims: Dimension[];
}

/** A split of a career. */
export interface Split {
  role: Role;
  dim: string;
  key: string;
  n: number;
  runs: number;
  outs: number;
  rae: number;
  wpa: number;
}

export interface GameLine {
  match_id: string;
  date: string;
  team1: string;
  team2: string;
  bat_n: number;
  bat_v: number;
  bat_w: number;
  bowl_n: number;
  bowl_v: number;
  bowl_w: number;
}

export interface Extra {
  role: Role;
  lede: string[];
  profiles: Profile[];
  profile: Partial<Record<Role, Profile>>;
  log: GameLine[];
  series: { date: string; value: number }[];
  splits: Split[];
  alike: Alike[];
}

/** A player with a similar skill profile. `match` is out of 100. */
export interface Alike {
  player_id: string;
  name: string;
  fmt: string;
  match: number;
}

/** One format of a career, with the bat: as a profile's summary table shows it. */
export interface BattingLine {
  league: string;
  matches: number;
  innings: number;
  not_outs: number;
  runs: number;
  best: string; // "254*"
  average: number | null;
  balls: number;
  strike_rate: number | null;
  hundreds: number;
  fifties: number;
  fours: number;
  sixes: number;
}

export interface BowlingLine {
  league: string;
  matches: number;
  innings: number;
  balls: number;
  runs: number;
  wickets: number;
  best: string; // "6/27"
  average: number | null;
  economy: number | null;
  strike_rate: number | null;
  fours: number;
  fives: number;
}

export interface RecentGame {
  match_id: string;
  date: string;
  league: string;
  opponent: string | null;
  batted: boolean;
  runs: number;
  faced: number;
  out: boolean | null;
  wickets: number;
  conceded: number;
  bowled: number;
}

export interface Career {
  batting: BattingLine[];
  bowling: BowlingLine[];
  recent: RecentGame[];
}
