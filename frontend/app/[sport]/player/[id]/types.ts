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
