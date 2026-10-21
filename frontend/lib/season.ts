// One season played many times over: what the server sends, and small sums on it.

/** The running count. Rewritten by the tally every second while the job runs. */
export interface Tally {
  year: number;
  teams: string[];
  running: boolean;
  target: number; // seasons the job set out to play
  seasons: number;
  matches: number;
  balls: number;
  seconds: number;
  balls_per_second: number;
  title: number[]; // share of seasons each team won, in the order of `teams`
  final: number[];
  playoffs: number[];
  league_wins: number[]; // average league wins a season
  history: { seasons: number; title: number[] }[]; // the title odds as they settled
  real: { champion: string | null; league_wins: number[]; playoffs: string[] };
}

export interface Finding {
  title: string;
  value: string;
  text: string;
  seconds: number;
}

/** Written once, when the job has finished. */
export interface Report {
  year: number;
  made: { seasons: number; matches: number; balls: number; playing_seconds: number };
  seconds: number;
  balls_per_second: number;
  lake: { files: number; rows: number; bytes: number; writers: number; rows_per_second: number };
  counts: { simulator: number; tally: number; lake: number };
  findings: Finding[];
  at: string;
}

export interface SeasonData {
  tally: Tally | null;
  report: Report | null;
}

/** Team numbers, likeliest champion first. */
export function byTitle(tally: Tally): number[] {
  return tally.teams.map((_, team) => team).sort((a, b) => tally.title[b] - tally.title[a]);
}

/** A big count in words a reader can hold: 1.77 billion, 7.4 million, 52,000. */
export function bigNumber(count: number): string {
  if (count >= 1e9) return `${(count / 1e9).toFixed(2)} billion`;
  if (count >= 1e6) return `${(count / 1e6).toFixed(1)} million`;
  return Math.round(count).toLocaleString("en-US");
}

/** A file size in gigabytes or megabytes. */
export function diskSize(bytes: number): string {
  return bytes >= 1e9 ? `${(bytes / 1e9).toFixed(1)} GB` : `${Math.round(bytes / 1e6)} MB`;
}
