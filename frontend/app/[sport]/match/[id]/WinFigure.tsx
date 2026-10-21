// The win-chance chart of a match, with a tooltip for every play, and its caption.

"use client";

import { WinChart } from "@/components/charts/WinChart";
import { pct } from "@/lib/format";

import type { MatchDetail, Play } from "./types";

interface WinFigureProps {
  match: MatchDetail;
  events: Play[];
  turning: number;
}

function caption(match: MatchDetail): string {
  const draws = match.fmt === "Test" ? " A draw counts as half a win." : "";
  return (
    `${match.team1}'s chance of winning after every ball.${draws} ` +
    "Move across the chart to read each one."
  );
}

export function WinFigure({ match, events, turning }: WinFigureProps) {
  const tipOf = (play: Play) => ({
    title: `${play.at} · ${play.score}`,
    text: `${play.text} — ${match.team1} ${pct(play.wp1_post)}`,
  });
  return (
    <figure>
      <WinChart
        events={events}
        team1={match.team1}
        team2={match.team2}
        turning={turning}
        tipOf={tipOf}
      />
      <figcaption>{caption(match)}</figcaption>
    </figure>
  );
}
