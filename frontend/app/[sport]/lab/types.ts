// What the Lab API sends. See src/innings/web/lab.py.

export interface ModelScore {
  model: string;
  all: number;
  known_players: number;
  T20: number;
  ODI: number;
  Test: number;
}

export interface CalibrationPoint {
  stated: number;
  happened: number;
  n: number;
}

export interface SimulatedLeague {
  league: string;
  real_innings: number;
  real_mean: number;
  real_spread: number;
  simulated_mean: number;
  simulated_spread: number;
}

export interface Card {
  seconds: number;
  evaluation: {
    balls: { train: number; validate: number; test: number };
    known_player_share: number;
    scores: ModelScore[];
    result: { format: "T20" | "ODI" | "Test"; balls: number; accuracy: number; brier: number }[];
    calibration: { wicket: CalibrationPoint[]; six: CalibrationPoint[] };
  };
  deployed: {
    balls: number;
    parameters: number;
    vocabulary: { batters: number; bowlers: number; venues: number; leagues: number };
    curve: { epoch: number; train: number }[];
    simulated_vs_real: SimulatedLeague[];
  };
  win_models: Record<string, number>;
}

export interface MapPlayer {
  id: string;
  name: string;
  balls: number;
  strike_rate: number;
  nearest: number[]; // positions in the players list
}

/** Where the network places each batter after each epoch. frames[epoch][player] = [x, y]. */
export interface PlayerMap {
  epochs: number;
  players: MapPlayer[];
  frames: [x: number, y: number][][];
  probes: { stat: string; r_squared: number }[];
}

export interface BallChances {
  chances: number[];
  runs_per_ball: number;
  wicket: number;
}

export interface MatchupAnswer {
  outcomes: string[];
  batter: { id: string; name: string; known: boolean };
  bowler: { id: string; name: string; known: boolean };
  pair: BallChances;
  average: BallChances;
}

export interface Simulation {
  start: { balls: number; wickets: number; score: number };
  target: number | null;
  limit: number;
  paths: [ball: number, score: number][][];
  innings: number;
  mean: number;
  low: number;
  high: number;
  histogram: { low: number; high: number; share: number }[];
  win: number | null;
  all_out: number;
}
