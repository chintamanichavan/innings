// A single value over time, such as a team's rating.

"use client";

import type { ReactNode } from "react";

import { num } from "@/lib/format";

import { Crosshair, NARROW, Svg, clamp, useWidth, xy } from "./base";

interface LineChartProps {
  points: { date: string; value: number }[];
  label: string; // names the value
  digits?: number;
  reference?: number; // draws a dashed line at this value
  maxHeight?: number;
}

type Scale = (value: number) => number;

function yearMarks(
  firstTime: number,
  lastTime: number,
  width: number,
  x: Scale,
  top: number,
  bottom: number,
) {
  const firstYear = new Date(firstTime).getFullYear();
  const lastYear = new Date(lastTime).getFullYear();
  const step = Math.max(1, Math.ceil((lastYear - firstYear) / (width < NARROW ? 4 : 8)));
  const marks: ReactNode[] = [];
  for (let year = firstYear + 1; year <= lastYear; year += step) {
    const at = x(Number(new Date(year, 0, 1)));
    marks.push(<line key={`l${year}`} className="axis" x1={at} x2={at} y1={top} y2={bottom} />);
    marks.push(
      <text key={`t${year}`} x={at + 4} y={bottom + 18}>
        {year}
      </text>,
    );
  }
  return marks;
}

export function LineChart({ points, label, digits = 0, reference, maxHeight = 260 }: LineChartProps) {
  const [box, width] = useWidth();
  if (points.length < 2) return <p className="empty">Not enough games to draw this yet.</p>;
  if (!width) return <div ref={box} className="chart-slot" />;

  const height = Math.round(clamp(170, width * 0.3, maxHeight));
  const left = 48,
    right = 52,
    top = 14,
    bottom = height - 26;
  const times = points.map((point) => Number(new Date(point.date)));
  const values = points.map((point) => point.value);
  const firstTime = Math.min(...times),
    lastTime = Math.max(...times);

  let low = Math.min(...values, reference ?? Infinity);
  let high = Math.max(...values, reference ?? -Infinity);
  const padding = (high - low) * 0.08 || 1;
  low -= padding;
  high += padding;

  const x: Scale = (time) =>
    left + ((width - left - right) * (time - firstTime)) / (lastTime - firstTime || 1);
  const y: Scale = (value) => top + (bottom - top) * (1 - (value - low) / (high - low));
  const line = points.map((point, index) => xy(x(times[index]), y(point.value))).join(" ");
  const last = points.length - 1;
  const lastX = x(times[last]),
    lastY = y(values[last]);

  return (
    <div ref={box} className="chart-slot">
      <Svg width={width} height={height} label={label}>
        {[low, (low + high) / 2, high].map((value) => (
          <g key={value}>
            <line className="axis" x1={left} x2={width - right} y1={y(value)} y2={y(value)} />
            <text x={left - 7} y={y(value) + 4} textAnchor="end">
              {num(value, digits)}
            </text>
          </g>
        ))}
        {yearMarks(firstTime, lastTime, width, x, top, bottom)}
        {reference != null && (
          <line className="ref" x1={left} x2={width - right} y1={y(reference)} y2={y(reference)} />
        )}
        <polyline
          className="draw"
          pathLength={1}
          points={line}
          fill="none"
          stroke="var(--ink)"
          strokeWidth="2"
          strokeLinejoin="round"
        />
        <circle
          cx={lastX}
          cy={lastY}
          r="5"
          fill="var(--accent)"
          stroke="var(--card)"
          strokeWidth="2.5"
        />
        <text className="strong" x={lastX + 9} y={lastY + 4}>
          {num(values[last], digits)}
        </text>
        <Crosshair
          width={width}
          left={left}
          right={right}
          top={top}
          bottom={bottom}
          place={(pointerX) => {
            let nearest = 0;
            times.forEach((time, index) => {
              if (Math.abs(x(time) - pointerX) < Math.abs(x(times[nearest]) - pointerX))
                nearest = index;
            });
            const when = String(points[nearest].date).slice(0, 10);
            return {
              x: x(times[nearest]),
              y: y(values[nearest]),
              title: when,
              text: `${label}: ${num(values[nearest], digits)}`,
            };
          }}
        />
      </Svg>
    </div>
  );
}
