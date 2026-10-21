// Small charts with no state of their own: calibration, skill sliders, heat cells.

import type { CSSProperties } from "react";

import { num, pct } from "@/lib/format";
import { tip } from "@/lib/toast";

import { Svg } from "./base";
import { xy } from "./scale";

// ---- did the forecast match what happened? ----

export interface CalibrationBin {
  model: string;
  predicted: number;
  actual: number;
  n: number;
}

export interface CalibrationSeries {
  model: string;
  color: string;
  name: string;
}

const CALIBRATION_SERIES: CalibrationSeries[] = [
  { model: "elo", color: "var(--series-2)", name: "Team rating only" },
  { model: "full", color: "var(--series-1)", name: "Our forecast" },
];

/** Stated chance against what happened, one line per series (by default, our two models). */
export function CalibrationChart({
  bins,
  side,
  series = CALIBRATION_SERIES,
}: {
  bins: CalibrationBin[];
  side: string;
  series?: CalibrationSeries[];
}) {
  const width = 440,
    height = 320;
  const left = 42,
    right = 22,
    top = 10,
    bottom = height - 38;
  const x = (chance: number) => left + (width - left - right) * chance;
  const y = (chance: number) => top + (bottom - top) * (1 - chance);
  return (
    <Svg width={width} height={height} label="Forecast accuracy">
      {[0, 0.25, 0.5, 0.75, 1].map((chance) => (
        <g key={chance}>
          <line className="axis" x1={left} x2={width - right} y1={y(chance)} y2={y(chance)} />
          <text x={left - 7} y={y(chance) + 4} textAnchor="end">
            {chance * 100}%
          </text>
          <text x={x(chance)} y={bottom + 15} textAnchor="middle">
            {chance * 100}%
          </text>
        </g>
      ))}
      <line className="ref" x1={x(0)} y1={y(0)} x2={x(1)} y2={y(1)} />
      <text x={(left + width - right) / 2} y={height - 5} textAnchor="middle">
        Stated chance {side ? `the ${side} side wins` : "of winning"}
      </text>
      {series.map(({ model, color, name }) => {
        const mine = bins.filter((bin) => bin.model === model);
        return (
          <g key={model}>
            <polyline
              fill="none"
              stroke={color}
              strokeWidth="2"
              points={mine.map((bin) => xy(x(bin.predicted), y(bin.actual))).join(" ")}
            />
            {mine.map((bin) => (
              <circle
                key={bin.predicted}
                cx={x(bin.predicted)}
                cy={y(bin.actual)}
                r="4.5"
                fill={color}
                stroke="var(--card)"
                strokeWidth="2"
                {...tip(
                  name,
                  `Said ${pct(bin.predicted)}. Happened ${pct(bin.actual)}. ${num(bin.n)} games.`,
                )}
              />
            ))}
          </g>
        );
      })}
    </Svg>
  );
}

export function CalibrationLegend({ series = CALIBRATION_SERIES }: { series?: CalibrationSeries[] }) {
  return (
    <div className="legend">
      {[...series].reverse().map(({ model, color, name }) => (
        <span key={model}>
          <i style={{ background: color }} />
          {name}
        </span>
      ))}
    </div>
  );
}

// ---- skill profile ----

export interface Skill {
  label: string;
  pct: number; // ahead of this share of qualified players, 0 to 100
}

/** Grey in the middle, red toward 100, blue toward 0. */
function rankColor(rank: number): string {
  const strength = Math.round(Math.abs(rank - 50) * 2);
  const pole = rank >= 50 ? "var(--hi)" : "var(--lo)";
  return `color-mix(in oklab, ${pole} ${strength}%, var(--mid))`;
}

const rankTip = (skill: Skill) =>
  tip(skill.label, `Ahead of ${Math.round(skill.pct)}% of qualified players`);

/** Percentile sliders for a player's skills. Pass a second player's skills to compare. */
export function SkillBars({ skills, other }: { skills: Skill[]; other?: Skill[] | null }) {
  return (
    <>
      {skills.map((skill, index) => {
        const rival = other?.[index];
        const color = rankColor(skill.pct);
        return (
          <div className="pct" key={skill.label}>
            <span>{skill.label}</span>
            {rival ? (
              <div className="track">
                <div
                  className="dot"
                  style={{ left: `${skill.pct}%`, background: "var(--series-1)" }}
                  {...rankTip(skill)}
                />
                <div className="dot b" style={{ left: `${rival.pct}%` }} {...rankTip(rival)} />
              </div>
            ) : (
              <div className="track">
                <div className="fill" style={{ width: `${skill.pct}%`, background: color }} />
                <div
                  className="dot"
                  style={{ left: `${skill.pct}%`, background: color }}
                  {...rankTip(skill)}
                />
              </div>
            )}
            <b>
              {Math.round(skill.pct)}
              {rival && <span className="dim"> · {Math.round(rival.pct)}</span>}
            </b>
          </div>
        );
      })}
    </>
  );
}

// ---- small pieces ----

/** A background tint for a heat-table cell, from light at `low` to strong at `high`. */
export function heatStyle(value: number, low: number, high: number): CSSProperties {
  const strength = Math.round(6 + (58 * (value - low)) / (high - low));
  return { background: `color-mix(in oklab, var(--seq) ${strength}%, var(--card))` };
}
