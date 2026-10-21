// Shapes of the records feed: games, plays, and single-game performances.

export interface RecordGame {
  match_id: string;
  date: string;
  team1: string;
  team2: string;
  score1: number;
  score2: number;
  winner: string;
  thrill: number;
  winner_low: number;
  lead_changes: number;
}

export interface RecordPlay {
  match_id: string;
  date: string;
  team1: string;
  team2: string;
  league: string;
  moment: string;
  text: string;
  wp1: number;
  wp1_post: number;
}

export interface Performance {
  match_id: string;
  date: string;
  team1: string;
  team2: string;
  player_id: string;
  name: string;
  wpa: number;
  rae: number;
}
