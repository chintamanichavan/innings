// The shapes of the model tables the server sends.

import type { Metric } from "@/lib/meta";

export interface CricketModel {
  metrics: Metric[];
  league: string;
  fmt: string;
  er: { balls_left: number; wkts: number; er: number }[];
}
