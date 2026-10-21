// The replay player: the chart drawn up to the current play and the controls.

"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { WinChart } from "@/components/charts/WinChart";
import { pct } from "@/lib/format";
import { type Sport, link } from "@/lib/sport";

import type { Play, ReplayMatch } from "./types";

const INNINGS_NAMES = ["1st", "2nd", "3rd", "4th"];
const BIG_MOMENTS = 14; // "Next big moment" stops at this many of the largest swings
const AUTOPLAY_MS = 1400;

interface ReplayProps {
  sport: Sport;
  match: ReplayMatch;
  events: Play[];
  firstParagraph: string;
}

function whenLabel(play: Play): string {
  return `${INNINGS_NAMES[play.period - 1]} innings · ${play.at}`;
}

/** The sequence numbers of the biggest swings, in match order. */
function bigMoments(events: Play[]): number[] {
  const swing = (play: Play) => Math.abs(play.wp1_post - play.wp1);
  const biggest = [...events].sort((a, b) => swing(b) - swing(a)).slice(0, BIG_MOMENTS);
  return biggest.map((play) => play.seq).sort((a, b) => a - b);
}

export function Replay({ sport, match, events, firstParagraph }: ReplayProps) {
  const [at, setAt] = useState(0);
  const [playing, setPlaying] = useState(false);
  const last = events.length - 1;
  const play = events[at];
  const atEnd = at >= last;

  // One timer while playing; it stops by itself at the last ball and when the page is left.
  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(() => setAt((now) => Math.min(last, now + 1)), AUTOPLAY_MS);
    return () => clearInterval(timer);
  }, [playing, last]);
  useEffect(() => {
    if (playing && atEnd) setPlaying(false);
  }, [playing, atEnd]);

  const moveTo = (index: number) => {
    setPlaying(false);
    setAt(Math.min(last, index));
  };
  const nextBigMoment = () => {
    const next = bigMoments(events).find((seq) => seq > play.seq);
    return next == null ? last : events.findIndex((event) => event.seq === next);
  };

  return (
    <>
      <figure>
        <WinChart events={events} team1={match.team1} team2={match.team2} upto={at} />
      </figure>
      <div className="panel narrow">
        <div className="meta flush">
          <span className="chip">{whenLabel(play)}</span>
          <span>{play.score}</span>
          <span>
            {match.team1} {pct(play.wp1)} → <b>{pct(play.wp1_post)}</b>
          </span>
        </div>
        <h2 className="replay-play">{play.text}</h2>
      </div>
      <div className="row spaced">
        <button className="btn" disabled={atEnd} onClick={() => moveTo(at + 1)}>
          Next ball
        </button>
        <button className="btn alt" disabled={atEnd} onClick={() => moveTo(nextBigMoment())}>
          Next big moment
        </button>
        <button className="btn alt" onClick={() => setPlaying(!playing)}>
          {playing ? "Pause" : "Play"}
        </button>
        <button className="btn alt" onClick={() => moveTo(0)}>
          Start again
        </button>
        <Link className="btn alt" href={link(sport, "match", match.match_id)}>
          Skip to the story
        </Link>
      </div>
      <p className="note">
        {atEnd ? `That was the last ball. ${firstParagraph}` : `Ball ${at + 1} of ${events.length}.`}
      </p>
    </>
  );
}
