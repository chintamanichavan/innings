// What the forecaster API sends. See src/innings/web/forecasts.py.

import type { CalibrationBin } from "@/components/charts/small";

export interface Tally {
  n: number;
  right: number;
  per_call: number;
}

export interface LeagueTally extends Tally {
  league: string;
}

/** One call we made, once the game was over. */
export interface Call {
  id: string;
  date: string;
  league: string;
  team1: string;
  team2: string;
  winner: string;
  pick: string;
  conf: number;
  points: number;
  right: boolean;
}

export interface ForecastPage {
  record: Tally;
  by_league: LeagueTally[];
  series: { date: string; value: number }[];
  misses: Call[];
  recent: Call[];
}

export interface Evaluation {
  calibration: CalibrationBin[];
}

/** One moment of the market comparison. See src/innings/web/routes/market.py. */
export interface MarketMoment {
  label: string;
  n: number;
  innings: number;
  market: number;
  gap: number;
  low: number;
  high: number;
  clear: boolean;
}

export interface MarketPage {
  matches: { scored: number; priced: number };
  chances: number;
  calibration_error: { innings: number; market: number; gap_interval: [number, number] };
  calibration: CalibrationBin[];
  moments: MarketMoment[];
  widest: MarketMoment;
  betting: { edge: number; bets: number; return_per_unit: number };
}
