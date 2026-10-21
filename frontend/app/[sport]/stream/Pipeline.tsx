// The pipeline drawn as five stops. A dot runs along it each time a ball comes through.

import { num } from "@/lib/format";
import type { Figures } from "@/lib/stream";

const STOPS: [name: string, does: string][] = [
  ["Bowler", "Replays a past match, one ball at a time"],
  ["Kafka: balls", "Holds each ball, in order, by match"],
  ["Scorer", "Keeps the score and asks the win model"],
  ["Kafka: scored", "Holds each ball with its win chance"],
  ["This page", "Hears each ball the moment it is scored"],
];

export function Pipeline({ figures }: { figures: Figures }) {
  return (
    <div className="panel pipe">
      <ol>
        {STOPS.map(([name, does]) => (
          <li key={name}>
            <b>{name}</b>
            <span>{does}</span>
          </li>
        ))}
      </ol>
      {/* A new key restarts the animation, so the dot sets off again for every ball. */}
      <div className="pipe-track" aria-hidden="true">
        {figures.taken > 0 && <i key={figures.taken} />}
      </div>
      <p className="note">
        {figures.delay_ms == null
          ? "Waiting for the next ball."
          : `The last few balls took ${num(figures.delay_ms)} milliseconds to get from the bowler to ` +
            `the scoreboard, through Kafka twice. The slowest took ${num(figures.slowest_ms)}.`}
      </p>
    </div>
  );
}
