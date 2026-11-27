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

/** One ball of commentary. `swing` is the batting side's change in win chance, when it is large. */
export interface CommentaryBall {
  at: string; // "17.3"
  text: string; // "Siraj to Rashid Khan, FOUR"
  mark: string; // "4", "W", "wd", "•"
  wicket: string | null; // "Rashid Khan c Rohit b Siraj 7 (3), 140/6 (17.3 ov)"
  swing: number | null;
}

export interface CommentaryOver {
  over: number; // from 1
  balls: CommentaryBall[];
  end: {
    runs: number;
    score: string;
    batters: { name: string; runs: number; balls: number }[];
    bowler: { name: string; figures: string } | null;
  };
}

export interface CommentaryData {
  innings: { number: number; team: string; overs: CommentaryOver[] }[];
}
