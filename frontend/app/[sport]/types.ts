// Shapes of the home feed and the followed-teams feed, used by the front and following pages.

import type { MatchSummary, WinEvent } from "@/lib/types";

export interface Story {
  headline: string;
  standfirst: string;
  paragraphs: string[];
  turning: { seq: number; text: string };
}

export interface Lead {
  match: MatchSummary;
  story: Story;
  events: WinEvent[];
}

export interface TopPlay {
  match_id: string;
  date: string;
  team1: string;
  team2: string;
  text: string;
  wp1: number;
  wp1_post: number;
}

export interface FormPlayer {
  player_id: string;
  name: string;
  value: number;
  n: number;
}

export interface Home {
  latest: string;
  recent: MatchSummary[];
  lead: Lead | null;
  classic: MatchSummary | null;
  on_this_day: MatchSummary[];
  top_play: TopPlay;
  hot_league: string;
  hot_leagues: string[];
  hot_bat: FormPlayer[];
  hot_bowl: FormPlayer[];
  cold_bat: FormPlayer[];
  forecast: { n: number; right: number };
}

/** The newest match of one followed team. */
export interface TeamLatest {
  team: string;
  match: MatchSummary;
}
