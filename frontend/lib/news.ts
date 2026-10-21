// Headlines and live scores from publishers' free feeds. See src/innings/feeds.py.

export interface Headline {
  source: string;
  title: string;
  link: string;
  summary: string;
  published: string | null; // ISO time, or null when the feed gave none we could read
}

export interface News {
  items: Headline[];
  sources: { name: string; ok: boolean; items: number }[];
}

/** One side of a live score line. `score` is as the feed writes it: "13 & 244/10". */
export interface LiveSide {
  team: string;
  score: string;
  batting: boolean;
}

export interface LiveMatch {
  first: LiveSide;
  second: LiveSide;
  started: boolean;
  link: string;
}

export interface LiveScores {
  matches: LiveMatch[];
  ok: boolean;
  source: string;
}

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/** "12 minutes ago", "3 hours ago", or the date once it is more than a day old. */
export function timeAgo(published: string | null, now: number): string {
  if (!published) return "";
  const then = new Date(published).getTime();
  const gap = Math.max(0, now - then);
  if (gap < MINUTE) return "just now";
  if (gap < HOUR) return plural(Math.floor(gap / MINUTE), "minute");
  if (gap < DAY) return plural(Math.floor(gap / HOUR), "hour");
  return new Date(published).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function plural(count: number, unit: string): string {
  return `${count} ${unit}${count === 1 ? "" : "s"} ago`;
}

/** The feed says "Australia Women"; the rest of the site says "Australia (W)". */
export function siteTeamName(feedName: string): string {
  return feedName.replace(/ Women$/, " (W)");
}
