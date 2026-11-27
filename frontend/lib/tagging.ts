// Hand-tagging balls: the shapes the server sends, and saving a tag.

import { ApiError } from "./api";

export interface TagField {
  name: string;
  values: string[];
  ordered: boolean;
}

export type Tags = Record<string, string | null>;

export interface Tag {
  at: string;
  tagger: string;
  tags: Tags;
  clock: string | null;
  differs: boolean;
}

export interface TagBall {
  innings: number;
  over: number;
  ball: number;
  bat_team: string;
  field_team: string;
  batter: string;
  bowler: string;
  bowler_id: string;
  runs: number;
  runs_bat: number;
  extras: number;
  wide: boolean;
  noball: boolean;
  dismissal: string | null;
  wicket: boolean;
  phase: string;
  tag: Tag | null;
}

export interface TagMatchSummary {
  match_id: string;
  date: string;
  team1: string;
  team2: string;
  venue: string;
  balls: number;
  death: number;
  tagged: number;
}

export interface TagMatch extends Omit<TagMatchSummary, "balls" | "death" | "tagged"> {
  balls: TagBall[];
}

export const FIELD_LABEL: Record<string, string> = {
  delivery: "Delivery",
  pace: "Pace",
  angle: "Angle",
  line: "Line",
  length: "Length",
  shot: "Shot",
  contact: "Contact",
  zone: "Where it went",
  height: "Ground or air",
  ring: "Ring",
};

/** The fields after `shot` or `contact` that mean nothing once the batter missed or left it. */
export const AFTER_CONTACT = ["contact", "zone", "height", "ring"];

/** What the scorecard says of a ball, short: "4", "1 wide", "W". */
export function scored(ball: TagBall): string {
  const parts = [String(ball.runs)];
  if (ball.wide) parts.push("wide");
  if (ball.noball) parts.push("no-ball");
  if (ball.wicket) parts.push(`out, ${ball.dismissal}`);
  return parts.join(" ");
}

export interface NewTag {
  tagger: string;
  match_id: string;
  innings: number;
  over: number;
  ball: number;
  tags: Tags;
  clock: string | null;
  differs: boolean;
}

/** Save one tag; the server adds the scorecard's runs and wicket and returns what it stored. */
export async function saveTag(tag: NewTag): Promise<Tag> {
  const response = await fetch("/api/tag", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(tag),
  });
  if (response.ok) return response.json() as Promise<Tag>;
  const problem = (await response.json().catch(() => ({}))) as { detail?: string };
  throw new ApiError(problem.detail ?? "The tag was not saved.", response.status);
}
