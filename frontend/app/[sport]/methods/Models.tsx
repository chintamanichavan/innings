// The model section of the methods page: scores and the heat table.

import { heatStyle } from "@/components/charts/small";
import type { Metric } from "@/lib/meta";
import { num } from "@/lib/format";

import { LeaguePicker } from "./LeaguePicker";
import type { CricketModel } from "./types";

const WICKETS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];
const BALLS_PER_OVER = 6;

function ModelScore({ metrics }: { metrics: Metric[] }) {
  const by = Object.fromEntries(metrics.map((metric) => [metric.metric, metric]));
  const tested = metrics[0]?.split || "";
  return (
    <div className="tiles">
      <div className="tile">
        <b>{num(by.accuracy?.value * 100, 1)}%</b>
        <span>right side picked, ball by ball</span>
      </div>
      <div className="tile">
        <b>{num(by.brier?.value, 3)}</b>
        <span>Brier score. 0.25 is a coin flip</span>
      </div>
      <div className="tile">
        <b>{num(by.n?.value)}</b>
        <span>test events, {tested}</span>
      </div>
    </div>
  );
}

export function CricketModelSection({ model, leagues }: { model: CricketModel; leagues: string[] }) {
  const isTest = model.fmt === "Test";
  // For Tests the table's columns are innings numbers; otherwise they are overs left.
  const columns = [...new Set(model.er.map((state) => state.balls_left))];
  if (isTest) columns.reverse();
  const highest = Math.max(...model.er.map((state) => state.er));
  const cellFor = (wickets: number, column: number) => {
    const state = model.er.find((s) => s.wkts === wickets && s.balls_left === column);
    if (!state) return <td key={column}></td>;
    return (
      <td key={column} style={heatStyle(state.er, 0, highest)}>
        {num(state.er)}
      </td>
    );
  };
  return (
    <>
      <h2 className="label">The {model.fmt} win chance model</h2>
      <LeaguePicker leagues={leagues} current={model.league} />
      <ModelScore metrics={model.metrics} />
      <h2 className="label">
        Runs still to come{isTest ? " in the innings" : ""}, {model.league}
      </h2>
      <div className="scroll">
        <table className="heat">
          <thead>
            <tr>
              <th className="l">{isTest ? "Match innings" : "Overs left"}</th>
              {columns.map((column) => (
                <th key={column}>{isTest ? column : column / BALLS_PER_OVER}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {WICKETS.map((wickets) => (
              <tr key={wickets}>
                <td className="l">{wickets} down</td>
                {columns.map((column) => cellFor(wickets, column))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="note">
        Some corners never happen in real games, such as no wickets down with one over left. The model
        fills them in, so read those cells loosely.
      </p>
    </>
  );
}
