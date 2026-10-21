// The shapes of the match story the server sends.

import type { MatchSummary, WinEvent } from "@/lib/types";

export interface MatchDetail extends MatchSummary {
  fmt: string;
  venue: string | null;
  lead_changes: number | null;
  winner_low: number | null;
}

/** One play: what happened, the score, and the first team's win chance around it. */
export interface Play extends WinEvent {
  at: string;
  score: string;
  text: string;
}

export interface PlayerLine {
  player_id: string;
  name: string;
  line: string | null;
  wpa: number;
  rae: number;
}

export interface Story {
  headline: string;
  standfirst: string;
  paragraphs: string[];
  turning: { seq: number; text: string };
}

export interface MatchPage {
  match: MatchDetail;
  events: Play[];
  players: PlayerLine[];
  story: Story;
  call: { p1: number } | null;
}
