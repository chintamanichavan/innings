// A slice of every ball, as /api/slice and /api/ask send it, and the words for its parts.

import type { Column } from "./format";
import type { Query } from "./sport";

/** The filters a slice can carry. The page's address uses the same names. */
export const SLICE_FIELDS = [
  "role",
  "batter",
  "bowler",
  "hand",
  "type",
  "family",
  "fmt",
  "league",
  "phase",
  "chase",
  "venue",
  "team",
  "opponent",
  "first",
  "last",
  "by",
  "min",
] as const;

export type SliceField = (typeof SLICE_FIELDS)[number];
export type SliceQuery = Partial<Record<SliceField, string>>;

export type SliceRow = Record<string, number | null> & { key: string; label: string };

export interface SliceAnswer {
  slice: SliceQuery;
  title: string;
  columns: Column[];
  total: Record<string, number | null>;
  rows: SliceRow[];
  min: number;
  names: { batter: string | null; bowler: string | null };
  coverage: Coverage;
}

export interface Coverage {
  type: number; // share of balls whose bowler's type is known
  hand: number; // share of balls whose batter's hand is known
}

/** The slice fields out of a page's query, and nothing else. */
export function sliceOf(query: Record<string, string>): SliceQuery {
  const picked: SliceQuery = {};
  for (const name of SLICE_FIELDS) if (query[name]) picked[name] = query[name];
  return picked;
}

/** Whose numbers a matchup shows: the bowler's only when a bowler is named and no batter. */
export function roleOf(slice: SliceQuery): "bat" | "bowl" {
  if (slice.role === "bat" || slice.role === "bowl") return slice.role;
  return slice.bowler && !slice.batter ? "bowl" : "bat";
}

export const BOWLING_TYPES: [key: string, label: string][] = [
  ["right-pace", "Right-arm pace"],
  ["left-pace", "Left-arm pace"],
  ["off-spin", "Off-spin"],
  ["leg-spin", "Leg-spin"],
  ["left-orthodox", "Left-arm orthodox"],
  ["left-wrist", "Left-arm wrist-spin"],
];

export const PHASES: [key: string, label: string][] = [
  ["powerplay", "Powerplay"],
  ["middle", "Middle overs"],
  ["death", "Death overs"],
  ["new-ball", "Test: new ball"],
  ["old-ball", "Test: old ball"],
  ["second-new-ball", "Test: second new ball"],
];

/** The ways a table can be split, for whoever's numbers it shows. */
export function splitsFor(role: "bat" | "bowl"): [key: string, label: string][] {
  const opponentKind: [string, string][] =
    role === "bat"
      ? [
          ["type", "Bowling type"],
          ["family", "Pace or spin"],
          ["bowler", "Each bowler"],
        ]
      : [
          ["hand", "Batting hand"],
          ["batter", "Each batter"],
        ];
  return [
    ["year", "Year"],
    ...opponentKind,
    ["phase", "Phase"],
    ["venue", "Ground"],
    ["opponent", "Opponent"],
    ["league", "League"],
    ["fmt", "Format"],
    ["innings", "Each innings"],
  ];
}

/** Does this split, or a filter, lean on the styles we only partly know? */
export function needsStyles(slice: SliceQuery): { type: boolean; hand: boolean } {
  return {
    type: ["type", "family"].includes(slice.by ?? "") || Boolean(slice.type || slice.family),
    hand: slice.by === "hand" || Boolean(slice.hand),
  };
}

/** The query for /api/slice, with a sort if one was chosen. */
export function sliceParams(slice: SliceQuery, sort = ""): Query {
  return { ...slice, sort };
}
