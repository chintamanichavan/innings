// The forecast for the chosen pair, and how well forecasts like it have done.

import { CalibrationLegend } from "@/components/charts/small";
import { api } from "@/lib/api";
import { num } from "@/lib/format";
import type { Sport } from "@/lib/sport";

import { Calibration } from "./Calibration";
import type { Evaluation, Prediction } from "./types";

const METHOD_NAMES = {
  "base rate": "Always pick the usual side",
  elo: "Team rating only",
  full: "Rating, form and lineups",
};
const PERCENT = 100;

interface PairProps {
  sport: Sport;
  pool: string;
  a: string;
  b: string;
}

export async function Result({ sport, pool, a, b }: PairProps) {
  if (!a || !b || a === b) return <p className="empty">Pick two different teams.</p>;
  const result = await api<Prediction>("predict", { sport, pool, a, b });
  const tiles: [number, string][] = [
    [result.neutral, `${a} win before the toss`],
    [result.a_first, "batting first"],
    [result.a_second, "chasing"],
  ];
  return (
    <div className="tiles">
      {tiles.map(([chance, label]) => (
        <div className="tile" key={label}>
          <b>{num(chance * PERCENT, 0)}%</b>
          <span>{label}</span>
        </div>
      ))}
    </div>
  );
}

export function TrackRecord({ evaluation, side }: { evaluation: Evaluation; side: string }) {
  return (
    <>
      <h2 className="label">Does the forecast work?</h2>
      <div className="scroll">
        <table>
          <thead>
            <tr>
              <th className="l">Method</th>
              <th>Games</th>
              <th>Right</th>
            </tr>
          </thead>
          <tbody>
            {evaluation.overall.map((method) => (
              <tr key={method.model}>
                <td className="l">{METHOD_NAMES[method.model]}</td>
                <td>{num(method.n)}</td>
                <td>{num(method.accuracy * PERCENT, 1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="note">Tested only on seasons the model had not seen.</p>
      <CalibrationLegend />
      <figure>
        <Calibration bins={evaluation.calibration} side={side} />
      </figure>
      <p className="note">
        Each dot is a group of games. On the dashed line, a 70% call comes true 70% of the time.
      </p>
    </>
  );
}
