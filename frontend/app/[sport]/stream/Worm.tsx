// The worm: each side's runs, over by over, both innings on one set of axes. A dot marks each
// wicket. The second side's line chases the first; the dashed line is its target.

"use client";

import { Svg, useWidth, xy } from "@/components/charts/base";
import type { LiveMatch, Point } from "@/lib/stream";
import { identity } from "@/lib/teams";

const HEIGHT = 140;
const FULL: Record<string, number> = { T20: 120, ODI: 300 };

export function Worm({ match }: { match: LiveMatch }) {
  const [box, width] = useWidth();
  if (!width) return <div ref={box} className="chart-slot worm" />;

  const full = FULL[match.fmt] ?? 120;
  const innings = [1, 2].map((number) =>
    match.points.filter((point) => point.innings === number && point.kind !== "end"),
  );
  const most = Math.max(
    60,
    ...match.points.map((point) => point.score),
    ...innings[1].map((p) => p.target ?? 0),
  );
  const left = 30,
    right = 8,
    top = 8,
    bottom = HEIGHT - 20;
  const x = (point: Point) => left + ((width - left - right) * (full - point.balls_left)) / full;
  const y = (runs: number) => bottom - ((bottom - top) * runs) / (Math.ceil(most / 50) * 50);
  const ceiling = Math.ceil(most / 50) * 50;
  const target = innings[1][0]?.target;
  const everyFive = full / 6 / 4; // four marks across the overs

  return (
    <div ref={box} className="chart-slot worm">
      <Svg width={width} height={HEIGHT} label={`Runs over by over: ${match.team1} and ${match.team2}`}>
        {[0, ceiling / 2, ceiling].map((runs) => (
          <g key={runs}>
            <line className="axis" x1={left} x2={width - right} y1={y(runs)} y2={y(runs)} />
            <text x={left - 5} y={y(runs) + 4} textAnchor="end">
              {runs}
            </text>
          </g>
        ))}
        {[0, 1, 2, 3, 4].map((step) => {
          const over = step * everyFive;
          const at = left + ((width - left - right) * over * 6) / full;
          return (
            <text key={step} x={at} y={bottom + 15} textAnchor="middle">
              {over}
            </text>
          );
        })}
        {target != null && (
          <line className="ref" x1={left} x2={width - right} y1={y(target)} y2={y(target)} />
        )}
        {innings.map((points, index) => {
          if (!points.length) return null;
          const color = identity(points[0].bat_team).color;
          const line = points.map((point) => xy(x(point), y(point.score))).join(" ");
          return (
            <g key={index}>
              <polyline
                points={line}
                fill="none"
                stroke={color}
                strokeWidth="2.2"
                strokeLinejoin="round"
              />
              {points
                .filter((point, at) => at > 0 && point.wickets > points[at - 1].wickets)
                .map((point) => (
                  <circle
                    key={point.n}
                    cx={x(point)}
                    cy={y(point.score)}
                    r="3.2"
                    fill={color}
                    stroke="var(--card)"
                  />
                ))}
            </g>
          );
        })}
      </Svg>
    </div>
  );
}
