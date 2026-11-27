// The first team's chance of winning after every play of a match.

"use client";

import { type ReactNode, useId } from "react";

import { identity } from "@/lib/teams";
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

/** The over a play was in, from its "17.3" label; null when the play has no label. */
function overOf(event: WinEvent): number | null {
  const at = (event as WinEvent & { at?: string }).at;
  return at ? Number(at.split(".")[0]) : null;
}

/** Small over numbers along the bottom: every 5 overs in a T20, 10 in a one-day game, 25 in a Test. */
function overMarks(events: WinEvent[], x: Scale, bottom: number) {
  const longest = Math.max(0, ...events.map((event) => overOf(event) ?? 0));
  if (!longest) return null;
  const step = longest < 20 ? 5 : longest < 50 ? 10 : 25;
  return events.map((event, index) => {
    const over = overOf(event);
    const previous = events[index - 1];
    const starts =
      over != null && over > 0 && over % step === 0 && (!previous || overOf(previous) !== over);
    if (!starts || previous?.period !== event.period) return null;
    return (
      <text key={`o${index}`} className="tick" x={x(index)} y={bottom + 12} textAnchor="middle">
        {over}
      </text>
    );
  });
}

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
      <text key={`t${index}`} x={at + 4} y={bottom + 26}>
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
  const clip = useId(); // a page can hold several charts, and each needs its own clip shapes
  if (!width || !events.length) return <div ref={box} className="chart-slot" />;

  const height = Math.round(compact ? clamp(180, width * 0.3, 240) : clamp(230, width * 0.34, 350));
  const left = 46,
    right = 14,
    top = 22,
    bottom = height - 36;
  const [one, two] = [identity(team1), identity(team2)];
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
        {/* 100% at the top is a sure win for the first side; 100% at the bottom, for the second. */}
        <text className="strong" x={left - 7} y={y(1) + 4} textAnchor="end" style={{ fill: one.color }}>
          {one.code}
        </text>
        <text x={left - 7} y={y(0.75) + 4} textAnchor="end">
          75%
        </text>
        <text x={left - 7} y={y(0.5) + 4} textAnchor="end">
          50%
        </text>
        <text x={left - 7} y={y(0.25) + 4} textAnchor="end">
          75%
        </text>
        <text className="strong" x={left - 7} y={y(0) + 4} textAnchor="end" style={{ fill: two.color }}>
          {two.code}
        </text>
        {periodMarks(events, width, x, top, bottom)}
        {overMarks(events, x, bottom)}
        {/* The area is the first side's colour while it leads, the second side's while it trails. */}
        <clipPath id={`above${clip}`}>
          <rect x={left} y={top} width={width - left - right} height={y(0.5) - top} />
        </clipPath>
        <clipPath id={`below${clip}`}>
          <rect x={left} y={y(0.5)} width={width - left - right} height={bottom - y(0.5)} />
        </clipPath>
        {[
          [`above${clip}`, one.color],
          [`below${clip}`, two.color],
        ].map(([clip, color]) => (
          <polygon
            key={clip}
            clipPath={`url(#${clip})`}
            points={`${left},${y(0.5)} ${line} ${endX},${y(0.5)}`}
            fill={color}
            opacity=".32"
          />
        ))}
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
