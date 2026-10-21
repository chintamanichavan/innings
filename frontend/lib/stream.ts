// The live stream as the page sees it: what the server sends, and how new records are
// folded into the matches on show. Plain data in, plain data out, so it can be tested.

const FULL_INNINGS: Record<string, number> = { T20: 120, ODI: 300 };

/** One step of a match after the scorer has dealt with it: an innings starting, a ball, the end. */
export interface Point {
  kind: "innings" | "ball" | "end";
  match_id: string;
  n: number; // this record's place in its match, counting from 1
  innings: number;
  bat_team: string;
  score: number;
  wickets: number;
  balls_left: number;
  target: number | null;
  wp1: number; // the first team's chance of winning after this
  at?: string; // over.ball, for a ball
  text?: string; // "Bumrah to Kohli, FOUR"
  what?: string;
  card?: Card; // the scoreboard after a ball
  result?: string; // at the end: "Mumbai Indians won by 5 wickets (8 balls left)"
}

/** What a cricket scoreboard shows beside the score. */
export interface Card {
  batters: {
    name: string;
    runs: number;
    balls: number;
    fours: number;
    sixes: number;
    on_strike: boolean;
  }[];
  bowler: { name: string; figures: string } | null; // figures: overs-maidens-runs-wickets
  this_over: string[]; // "•", "1", "4", "W", "wd" ...
  partnership: [runs: number, balls: number];
  last_wicket: string | null;
}

export interface MatchStart {
  kind: "start";
  match_id: string;
  fmt: string;
  competition: string;
  team1: string;
  team2: string;
  venue: string | null;
  date: string;
}

export type StreamRecord = Point | MatchStart;

export interface LiveMatch extends Omit<MatchStart, "kind"> {
  points: Point[];
}

/** How the pipeline is doing right now. */
export interface Figures {
  connected: boolean;
  taken: number;
  matches: number;
  per_second: number;
  delay_ms: number | null;
  slowest_ms: number | null;
}

export interface BenchRun {
  scorers: number;
  matches: number;
  balls: number;
  seconds: number;
  per_second: number;
  checked: number;
  worst_difference: number;
  at: string;
}

export interface Snapshot {
  on: boolean;
  matches: LiveMatch[];
  cursor: number;
  figures: Figures;
  bench: BenchRun[];
}

/** What one pushed message holds. `reload` means: too far behind, ask for a fresh snapshot. */
export interface News {
  reload?: boolean;
  records?: StreamRecord[];
  cursor?: number;
  figures?: Figures;
}

export const isOver = (match: LiveMatch) => match.points.at(-1)?.kind === "end";

/**
 * The matches after some new records. A new match takes the place of the finished ones.
 * A record the page has already seen is skipped, so a dropped connection that sends the
 * last few again does no harm.
 */
export function withRecords(matches: LiveMatch[], records: StreamRecord[]): LiveMatch[] {
  let next = matches;
  for (const record of records) {
    if (record.kind === "start") {
      const { kind: _, ...facts } = record;
      const kept = next.filter((match) => !isOver(match) && match.match_id !== record.match_id);
      next = [...kept, { ...facts, points: [] }];
      continue;
    }
    next = next.map((match) => {
      const seen = match.points.at(-1)?.n ?? 0;
      if (match.match_id !== record.match_id || record.n <= seen) return match;
      return { ...match, points: [...match.points, record] };
    });
  }
  return next;
}

/** How far through the match a point is, from 0 to 1. Each innings is half the chart. */
export function progress(point: Point, fmt: string): number {
  if (point.kind === "end") return 1;
  const full = FULL_INNINGS[fmt] ?? 120;
  const bowled = Math.min(1, Math.max(0, 1 - point.balls_left / full));
  return (point.innings - 1 + bowled) / 2;
}

/** Runs an over: 9.45. */
export function runRate(runs: number, balls: number): string {
  return balls > 0 ? ((runs * 6) / balls).toFixed(2) : "0.00";
}

/** Balls bowled, as overs: 17.3. */
export function overs(balls: number): string {
  return balls % 6 ? `${Math.floor(balls / 6)}.${balls % 6}` : `${balls / 6}`;
}

/** The line under the score: the chase, the innings break, or the result. */
export function status(match: LiveMatch, last: Point, code: (team: string) => string): string {
  if (last.kind === "end") return last.result ?? "Match over";
  if (last.innings === 2 && last.target != null) {
    const need = last.target - last.score;
    if (last.kind === "innings")
      return `Innings break. ${code(last.bat_team)} need ${last.target} to win`;
    return `${code(last.bat_team)} need ${need} run${need === 1 ? "" : "s"} in ${last.balls_left} ball${
      last.balls_left === 1 ? "" : "s"
    }`;
  }
  return `${code(last.bat_team)} batting first`;
}

/** Where an innings stands at its latest ball, or null if it has not started. */
export function inningsScore(match: LiveMatch, innings: number): Point | null {
  return match.points.findLast((point) => point.innings === innings && point.kind !== "end") ?? null;
}
