// The title odds settling: one line per team, from the first ten seasons to the last.
// Python noted the odds at each point along the way; this only draws them, left to right.

"use client";

import { useEffect, useRef, useState } from "react";

import { Svg, useWidth, xy } from "@/components/charts/base";
import { pct } from "@/lib/format";
import { animate, ease } from "@/lib/motion";
import type { Tally } from "@/lib/season";
import { identity } from "@/lib/teams";

const HEIGHT = 340;
const PLAY_MS = 6000;
const LABEL_GAP = 12; // pixels between two team labels
const MARKS = [10, 100, 1000, 10_000, 100_000, 1_000_000];

/** Where to write each line's label: beside the line's end, moved down where two would overlap. */
function labelHeights(ends: number[]): number[] {
  const order = ends.map((_, team) => team).sort((a, b) => ends[a] - ends[b]);
  const heights = [...ends];
  for (let place = 1; place < order.length; place++) {
    const above = heights[order[place - 1]];
    heights[order[place]] = Math.max(heights[order[place]], above + LABEL_GAP);
  }
  return heights;
}

export function OddsChart({ tally }: { tally: Tally }) {
  const [box, width] = useWidth();
  const [shown, setShown] = useState(1); // how far along the chart is drawn, 0 to 1
  const stop = useRef(() => {});
  useEffect(() => () => stop.current(), []);

  const history = tally.history;
  if (!width || history.length < 2) return <div ref={box} className="chart-slot" />;

  const left = 40,
    right = 46,
    top = 12,
    bottom = HEIGHT - 30;
  const first = Math.log10(history[0].seasons);
  const last = Math.log10(history.at(-1)!.seasons);
  const top_share = Math.ceil(Math.max(...history.flatMap((point) => point.title)) * 10) / 10;
  // Each step along is ten times as many seasons, so the early wobble has room to show.
  const x = (seasons: number) =>
    left + ((width - left - right) * (Math.log10(seasons) - first)) / (last - first);
  const y = (share: number) => bottom - ((bottom - top) * share) / top_share;
  const upto = Math.max(2, Math.ceil(history.length * shown));
  const drawn = history.slice(0, upto);
  const now = drawn.at(-1)!;

  const play = () => {
    stop.current();
    stop.current = animate(PLAY_MS, (progress) => setShown(ease(progress)));
  };

  return (
    <div className="panel">
      <div className="odds-head">
        <button className="btn" onClick={play}>
          Play it again
        </button>
        <span>
          After <b>{now.seasons.toLocaleString("en-US")}</b> seasons
        </span>
      </div>
      <div ref={box} className="chart-slot">
        <Svg
          width={width}
          height={HEIGHT}
          label="Each team's share of titles as more seasons are played"
        >
          {[0, top_share / 2, top_share].map((share) => (
            <g key={share}>
              <line className="axis" x1={left} x2={width - right} y1={y(share)} y2={y(share)} />
              <text x={left - 6} y={y(share) + 4} textAnchor="end">
                {pct(share)}
              </text>
            </g>
          ))}
          {MARKS.filter((mark) => Math.log10(mark) >= first && Math.log10(mark) <= last).map((mark) => (
            <text key={mark} x={x(mark)} y={bottom + 18} textAnchor="middle">
              {mark.toLocaleString("en-US")}
            </text>
          ))}
          {tally.teams.map((team, number) => (
            <polyline
              key={team}
              points={drawn.map((point) => xy(x(point.seasons), y(point.title[number]))).join(" ")}
              fill="none"
              stroke={identity(team).color}
              strokeWidth="2"
              strokeLinejoin="round"
            />
          ))}
          {labelHeights(now.title.map(y)).map((height, number) => {
            const { color, code } = identity(tally.teams[number]);
            return (
              <text
                key={code}
                className="strong"
                x={x(now.seasons) + 5}
                y={height + 4}
                style={{ fill: color }}
              >
                {code}
              </text>
            );
          })}
        </Svg>
      </div>
      <p className="note">
        Left to right, the number of seasons played goes up ten times at each mark. Early on, a few
        lucky seasons throw the lines about. By the right-hand edge they have stopped moving.
      </p>
    </div>
  );
}
