// The part of the match story the replay uses.

import type { MatchSummary, WinEvent } from "@/lib/types";

export type ReplayMatch = Pick<MatchSummary, "match_id" | "league" | "date" | "team1" | "team2">;

export interface Play extends WinEvent {
  at: string;
  score: string;
  text: string;
}

export interface ReplayPage {
  match: ReplayMatch;
  events: Play[];
  story: { headline: string; paragraphs: string[] };
}
