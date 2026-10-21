// Facts about the data that many pages need: the leagues and how the models scored.

import { cache } from "react";

import { api } from "./api";
import type { Sport } from "./sport";
import type { League } from "./types";

export interface Metric {
  sport: Sport;
  model: string;
  split: string;
  metric: string;
  value: number;
}

export interface Meta {
  leagues: (League & { matches: number; latest: string })[];
  metrics: Metric[];
  events: { sport: Sport; n: number }[];
}

/** Loaded once per page request, however many components ask. */
export const getMeta = cache(() => api<Meta>("meta"));

export async function leaguesOf(sport: Sport) {
  return (await getMeta()).leagues.filter((league) => league.sport === sport);
}
