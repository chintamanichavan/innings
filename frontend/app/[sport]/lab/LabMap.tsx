// "Watch it learn": every well-known batter as a dot, moving from where a random start put
// them to where the trained network places them, one training epoch at a time.

"use client";

import { type MouseEvent, useEffect, useRef, useState } from "react";

import { SearchBox } from "@/components/SearchBox";
import { num } from "@/lib/format";
import {
  type Rgb,
  animate,
  blend,
  ease,
  prepareCanvas,
  reducedMotion,
  solid,
  themeColor,
  whenVisible,
} from "@/lib/motion";
import { hideTip, showTip } from "@/lib/toast";

import type { PlayerMap } from "./types";

const HEIGHT = 440;
const EPOCH_MS = 650; // how long the dots take to move from one epoch to the next
const MARGIN = 26;
const HOVER_REACH = 14; // a dot answers the pointer from this many pixels away
const CURVE = { width: 132, height: 44 }; // the small error curve in the corner

type Point = [x: number, y: number];
interface Colors {
  pale: Rgb;
  strong: Rgb;
  ink: Rgb;
  accent: Rgb;
}

/** Where one batter's dot is, `where` epochs into training. `where` may be a fraction. */
function pointAt(frames: PlayerMap["frames"], index: number, where: number, width: number): Point {
  const before = Math.min(frames.length - 1, Math.floor(where));
  const after = Math.min(frames.length - 1, before + 1);
  const mix = ease(where - before);
  const [x0, y0] = frames[before][index];
  const [x1, y1] = frames[after][index];
  const x = x0 + (x1 - x0) * mix;
  const y = y0 + (y1 - y0) * mix;
  return [
    MARGIN + ((x + 1) / 2) * (width - 2 * MARGIN),
    MARGIN + ((y + 1) / 2) * (HEIGHT - 2 * MARGIN),
  ];
}

/** The training error falling, with a dot at the current epoch. */
function drawErrorCurve(
  context: CanvasRenderingContext2D,
  errors: number[],
  where: number,
  colors: Colors,
) {
  const highest = Math.max(...errors);
  const lowest = Math.min(...errors);
  const left = MARGIN;
  const top = HEIGHT - MARGIN - CURVE.height;
  const x = (epoch: number) => left + (CURVE.width * (epoch - 1)) / (errors.length - 1);
  const y = (error: number) => top + (CURVE.height * (highest - error)) / (highest - lowest || 1);

  context.strokeStyle = solid(colors.ink, 0.55);
  context.lineWidth = 1.5;
  context.beginPath();
  errors.forEach((error, index) => context.lineTo(x(index + 1), y(error)));
  context.stroke();
  context.fillStyle = solid(colors.ink, 0.7);
  context.font = "500 11px system-ui, sans-serif";
  context.fillText("Its error, falling", left, top - 8);

  const epoch = Math.max(1, Math.round(where));
  context.fillStyle = solid(colors.accent);
  context.beginPath();
  context.arc(x(epoch), y(errors[epoch - 1]), 4, 0, 2 * Math.PI);
  context.fill();
}

function drawMap(
  canvas: HTMLCanvasElement,
  data: PlayerMap,
  errors: number[],
  where: number,
  picked: number,
): Point[] {
  const { context, width } = prepareCanvas(canvas, HEIGHT);
  const colors: Colors = {
    pale: themeColor("--ink-3"),
    strong: themeColor("--seq"),
    ink: themeColor("--ink"),
    accent: themeColor("--accent"),
  };
  const rates = data.players.map((player) => player.strike_rate);
  const slowest = Math.min(...rates);
  const fastest = Math.max(...rates);
  const points = data.players.map((_, index) => pointAt(data.frames, index, where, width));
  context.clearRect(0, 0, width, HEIGHT);

  if (picked >= 0) {
    // lines from the chosen batter to the ones the network puts nearest
    context.strokeStyle = solid(colors.ink, 0.35);
    context.lineWidth = 1;
    for (const neighbour of data.players[picked].nearest) {
      context.beginPath();
      context.moveTo(...points[picked]);
      context.lineTo(...points[neighbour]);
      context.stroke();
    }
  }
  points.forEach(([x, y], index) => {
    const speed = (rates[index] - slowest) / (fastest - slowest);
    // Slow scorers are grey and faint, fast ones blue and solid. Others fade when one is picked.
    const strength = (0.45 + 0.45 * speed) * (picked >= 0 && index !== picked ? 0.55 : 1);
    context.beginPath();
    context.arc(x, y, index === picked ? 7 : 4, 0, 2 * Math.PI);
    context.fillStyle = blend(colors.pale, colors.strong, speed, strength);
    context.fill();
  });
  if (picked >= 0) {
    const [x, y] = points[picked];
    context.strokeStyle = solid(colors.ink);
    context.lineWidth = 2;
    context.beginPath();
    context.arc(x, y, 9, 0, 2 * Math.PI);
    context.stroke();
    context.fillStyle = solid(colors.ink);
    context.font = "600 13px system-ui, sans-serif";
    context.fillText(data.players[picked].name, Math.min(x + 13, width - 150), y + 4);
  }
  drawErrorCurve(context, errors, where, colors);
  return points;
}

export function LabMap({ data, errors }: { data: PlayerMap; errors: number[] }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const points = useRef<Point[]>([]);
  const stop = useRef(() => {});
  const [where, setWhere] = useState(data.epochs); // sits between two epochs while dots move
  const [picked, setPicked] = useState(-1);
  const [playing, setPlaying] = useState(false);
  const [played, setPlayed] = useState(false);
  const [missing, setMissing] = useState("");

  // The canvas is redrawn whenever anything it shows changes, and when its box changes size.
  useEffect(() => {
    const element = canvas.current!;
    const draw = () => {
      points.current = drawMap(element, data, errors, where, picked);
    };
    draw();
    const observer = new ResizeObserver(draw);
    observer.observe(element);
    return () => observer.disconnect();
  }, [data, errors, where, picked]);

  const play = () => {
    stop.current();
    setPlaying(true);
    stop.current = animate(EPOCH_MS * data.epochs, (progress) => setWhere(progress * data.epochs), {
      done: () => {
        setPlaying(false);
        setPlayed(true);
      },
    });
  };

  // Play once by itself, the first time the map scrolls into view.
  useEffect(() => {
    if (reducedMotion()) return;
    const unwatch = whenVisible(canvas.current!, play);
    return () => {
      unwatch();
      stop.current();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** The dot under the pointer, or -1. */
  const dotAt = (event: MouseEvent) => {
    const frame = canvas.current!.getBoundingClientRect();
    const x = event.clientX - frame.left;
    const y = event.clientY - frame.top;
    let nearest = -1;
    let best = HOVER_REACH ** 2;
    points.current.forEach(([px, py], index) => {
      const distance = (px - x) ** 2 + (py - y) ** 2;
      if (distance < best) {
        best = distance;
        nearest = index;
      }
    });
    return nearest;
  };

  const hover = (event: MouseEvent) => {
    const index = dotAt(event);
    if (index < 0) {
      hideTip();
      return;
    }
    const player = data.players[index];
    const line = `Strike rate ${num(player.strike_rate, 1)} over ${num(player.balls)} balls`;
    showTip(player.name, line, event.clientX, event.clientY);
  };

  const epoch = Math.round(where);
  const chosen = picked >= 0 ? data.players[picked] : null;
  return (
    <div className="panel">
      <div className="filters flush">
        <button className="btn sm" onClick={play}>
          {playing ? "Playing" : played ? "Play again" : "Play"}
        </button>
        <input
          id="map-epoch"
          type="range"
          min="0"
          max={data.epochs}
          step="1"
          value={epoch}
          aria-label="Training epoch"
          onChange={(event) => {
            stop.current();
            setPlaying(false);
            setWhere(Number(event.target.value));
          }}
        />
        <b id="map-label">{epoch === 0 ? "Before training" : `Epoch ${epoch} of ${data.epochs}`}</b>
        <SearchBox
          inline
          sport="ck"
          playersOnly
          placeholder="Find a batter on the map"
          onPick={(found) => {
            if (found.kind !== "player") return;
            const index = data.players.findIndex((player) => player.id === found.player_id);
            setPicked(index);
            setMissing(index < 0 ? `${found.name} has faced too few balls to be on the map.` : "");
          }}
        />
      </div>
      <canvas
        id="map-canvas"
        ref={canvas}
        className="lab-canvas"
        style={{ height: HEIGHT }}
        role="img"
        aria-label="Map of batters as the network sees them"
        onMouseMove={hover}
        onMouseLeave={hideTip}
        onClick={(event) => {
          const index = dotAt(event);
          if (index >= 0) setPicked(index);
        }}
      />
      <div className="legend">
        <span>
          <i className="slow" />
          Slow scorer
        </span>
        <span>
          <i className="fast" />
          Fast scorer
        </span>
        <span>
          {missing}
          {!missing && !chosen && "Tap a dot to see who the network thinks plays most like them."}
          {!missing && chosen && (
            <>
              <b>{chosen.name}</b> sits nearest to{" "}
              {chosen.nearest
                .slice(0, 3)
                .map((other) => data.players[other].name)
                .join(", ")}
              .
            </>
          )}
        </span>
      </div>
    </div>
  );
}
