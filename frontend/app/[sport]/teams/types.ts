// The shapes of the teams page's answers from the server.

import type { CalibrationBin } from "@/components/charts/small";

export interface Rating {
  team: string;
  elo: number;
  form: number; // share of the last 10 games won
  bat: number;
  bowl: number;
}

export interface Ratings {
  full_members_only: boolean;
  rows: Rating[];
}

export interface Method {
  model: "base rate" | "elo" | "full";
  n: number;
  accuracy: number;
}

export interface Evaluation {
  overall: Method[];
  calibration: CalibrationBin[];
}

export interface Prediction {
  a_first: number;
  a_second: number;
  neutral: number;
}
