// What the puzzle APIs send. See src/innings/web/routes/games.py.

import type { Skill } from "@/components/charts/small";
import type { Column } from "@/lib/format";

export interface Hint {
  title: string;
  text?: string;
  columns?: Column[];
  row?: Record<string, number | null>;
  profile?: Skill[];
}

export interface Daily {
  total: number;
  hints: Hint[];
}

export interface Answer {
  player_id: string;
  name: string;
}

export interface GuessResult {
  correct: boolean;
  answer: Answer | null;
}

export interface SeasonCard {
  player_id: string;
  name: string;
  year: number;
  team: string;
  value: number;
}

export interface HigherLowerRound {
  metric: string;
  cards: SeasonCard[];
}

export interface PickGame {
  match_id: string;
  date: string;
  league: string;
  venue: string | null;
  team1: string;
  team2: string;
  score1: number;
  score2: number;
  winner: string;
  p_model: number;
}
