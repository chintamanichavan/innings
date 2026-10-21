// The first team's chance of winning after every play of a match.

"use client";

import type { ReactNode } from "react";

import type { WinEvent } from "@/lib/types";

import { Crosshair, NARROW, Svg, clamp, useWidth, xy } from "./base";

const INNINGS_NAMES = ["1st", "2nd", "3rd", "4th"];

interface WinChartProps<Event extends WinEvent> {
  events: Event[];
  team1: string;
  team2: string;
  turning?: number | null; // seq of the play to mark as the biggest moment
  tipOf?: (event: Event) => { title: string; text: string }; // turns on the crosshair
  compact?: boolean;
  upto?: number | null; // draw only the first plays, for a replay
}

type Scale = (value: number) => number;

function periodMarks(events: WinEvent[], width: number, x: Scale, top: number, bottom: number) {
  const room = width < NARROW ? 44 : 78; // pixels a label needs
  const marks: ReactNode[] = [];
  let lastLabelAt = -Infinity;
  events.forEach((event, index) => {
    const previous = events[index - 1];
    if (previous && previous.period === event.period) return;
    const at = x(index);
    if (index > 0)
      marks.push(<line key={`l${index}`} className="axis" x1={at} x2={at} y1={top} y2={bottom} />);
    if (at - lastLabelAt < room) return;
    const innings = INNINGS_NAMES[event.period - 1] + (width < NARROW ? "" : " innings");
    marks.push(
      <text key={`t${index}`} x={at + 4} y={bottom + 19}>
        {innings}
      </text>,
    );
    lastLabelAt = at;
  });
  return marks;
}

function BiggestMoment({ cx, cy, width, top }: { cx: number; cy: number; width: number; top: number }) {
  const above = cy > top + 34; // put the label where there is room
  const nearRight = cx > width * 0.7;
  return (
    <>
      <line
        className="axis strong-line"
        x1={cx}
        x2={cx}
        y1={above ? cy - 9 : cy + 9}
        y2={above ? cy - 22 : cy + 22}
      />
      <circle
        cx={cx}
        cy={cy}
        r={width < NARROW ? 6 : 8}
        fill="var(--accent)"
        stroke="var(--card)"
        strokeWidth="2.5"
      />
      <text
        className="strong"
        x={cx + (nearRight ? 4 : -4)}
        y={above ? cy - 27 : cy + 34}
        textAnchor={nearRight ? "end" : "start"}
      >
        Biggest moment
      </text>
    </>
  );
}

export function WinChart<Event extends WinEvent>(props: WinChartProps<Event>) {
  const { events, team1, team2, turning = null, tipOf, compact = false, upto = null } = props;
  const [box, width] = useWidth();
  if (!width || !events.length) return <div ref={box} className="chart-slot" />;

  const height = Math.round(compact ? clamp(170, width * 0.3, 230) : clamp(220, width * 0.34, 340));
  const left = 40,
    right = 14,
    top = 22,
    bottom = height - 28;
  const count = events.length;
  const x: Scale = (index) => left + ((width - left - right) * index) / count;
  const y: Scale = (chance) => top + (bottom - top) * (1 - chance);

  const shown = upto == null ? count : Math.min(count, upto + 1);
  const points = events.slice(0, shown).map((event, index) => xy(x(index), y(event.wp1)));
  const endX = x(shown),
    endY = y(events[shown - 1].wp1_post);
  points.push(xy(endX, endY));
  const line = points.join(" ");
  const turningIndex = turning == null ? -1 : events.findIndex((event) => event.seq === turning);

  return (
    <div ref={box} className="chart-slot">
      <Svg width={width} height={height} label={`Win chance for ${team1} through the match`}>
        <line className="axis" x1={left} x2={width - right} y1={y(1)} y2={y(1)} />
        <line className="axis" x1={left} x2={width - right} y1={y(0)} y2={y(0)} />
        <line className="ref" x1={left} x2={width - right} y1={y(0.5)} y2={y(0.5)} />
        {[0, 0.5, 1].map((chance) => (
          <text key={chance} x={left - 7} y={y(chance) + 4} textAnchor="end">
            {chance * 100}%
          </text>
        ))}
        <text className="strong" x={left + 6} y={y(1) + 15}>
          ↑ {team1} winning
        </text>
        <text className="strong" x={left + 6} y={y(0) - 7}>
          ↓ {team2} winning
        </text>
        {periodMarks(events, width, x, top, bottom)}
        <polygon
          points={`${left},${y(0.5)} ${line} ${endX},${y(0.5)}`}
          fill="var(--ink)"
          opacity=".06"
        />
        {/* The line sweeps in once, when the chart first appears. A replay draws it plain. */}
        <polyline
          className={upto == null ? "draw" : ""}
          pathLength={1}
          points={line}
          fill="none"
          stroke="var(--ink)"
          strokeWidth="2"
          strokeLinejoin="round"
        />
        {upto != null && <circle className="now" cx={endX} cy={endY} r="6" />}
        {upto == null && turningIndex >= 0 && (
          <BiggestMoment
            cx={x(turningIndex + 1)}
            cy={y(events[turningIndex].wp1_post)}
            width={width}
            top={top}
          />
        )}
        {tipOf && (
          <Crosshair
            width={width}
            left={left}
            right={right}
            top={top}
            bottom={bottom}
            place={(pointerX) => {
              const nearest = Math.round(((pointerX - left) / (width - left - right)) * count) - 1;
              const index = clamp(0, nearest, count - 1);
              return { x: x(index + 1), y: y(events[index].wp1_post), ...tipOf(events[index]) };
            }}
          />
        )}
      </Svg>
    </div>
  );
}
