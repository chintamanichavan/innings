// A row of the match list.

export interface MatchRow {
  match_id: string;
  date: string;
  league: string;
  venue: string | null;
  team1: string;
  team2: string;
  score1: number;
  score2: number;
  winner: string | null;
  note: string | null;
  line1: string | null;
  line2: string | null;
  result: string | null;
}
