// "Watch it play": the network bats out the rest of an innings many times, one ball at a
// time, and the page draws every one of those futures.

"use client";

import { useEffect, useRef, useState } from "react";

import { Marked } from "@/components/Marked";
import { api } from "@/lib/api";
import { ballsToOvers, num, oversToBalls, pct } from "@/lib/format";
import { type Rgb, animate, ease, prepareCanvas, solid, themeColor, whenVisible } from "@/lib/motion";

import type { Simulation } from "./types";

const HEIGHT = 340;
const DRAW_MS = 2600;
const PAD = { left: 44, right: 78, top: 16, bottom: 30 }; // the right gutter holds the tally
const TALLY_STARTS = 0.6; // the tally of final scores starts growing this far into the drawing

/** Where an innings stands. `overs` is as cricket writes it: 14.3. */
interface Start {
  fmt: string;
  league: string; // empty for the format's usual league
  score: string;
  wickets: string;
  overs: string;
  target: string;
}

const PRESETS: { name: string; start: Start }[] = [
  {
    name: "A fresh IPL innings",
    start: { fmt: "T20", league: "IPL", score: "0", wickets: "0", overs: "0", target: "" },
  },
  {
    name: "Need 60 off 30, five down",
    start: { fmt: "T20", league: "IPL", score: "140", wickets: "5", overs: "15", target: "200" },
  },
  {
    name: "Need 12 off the last over",
    start: { fmt: "T20", league: "T20I", score: "158", wickets: "6", overs: "19", target: "170" },
  },
  {
    name: "ODI chase: 120 for 3 after 25 overs, chasing 281",
    start: { fmt: "ODI", league: "ODI", score: "120", wickets: "3", overs: "25", target: "281" },
  },
];
const FIRST_SHOWN = 1; // the preset played when the simulator first scrolls into view

interface Layout {
  first: number;
  last: number;
  top: number;
  bottom: number;
  right: number;
  x: (ball: number) => number;
  y: (score: number) => number;
  ink: Rgb;
  rule: Rgb;
  accent: Rgb;
  line: Rgb;
}

/** Scales and colours for one drawing. */
function layout(result: Simulation, width: number): Layout {
  const first = result.start.balls;
  const last = result.limit;
  const highestPath = Math.max(...result.paths.map((path) => path[path.length - 1][1]));
  const highestBand = result.histogram[result.histogram.length - 1].high;
  const top = Math.max(result.target ?? 0, highestPath, highestBand) * 1.04;
  const bottom = result.start.score;
  const right = width - PAD.right;
  const plotHeight = HEIGHT - PAD.top - PAD.bottom;
  return {
    first,
    last,
    top,
    bottom,
    right,
    x: (ball) => PAD.left + ((right - PAD.left) * (ball - first)) / Math.max(1, last - first),
    y: (score) => HEIGHT - PAD.bottom - (plotHeight * (score - bottom)) / Math.max(1, top - bottom),
    ink: themeColor("--ink-3"),
    rule: themeColor("--rule"),
    accent: themeColor("--accent"),
    line: themeColor("--series-1"),
  };
}

function drawAxes(context: CanvasRenderingContext2D, result: Simulation, at: Layout) {
  context.font = "500 11px system-ui, sans-serif";
  context.lineWidth = 1;
  for (const share of [0, 0.5, 1]) {
    // three guides, each labelled with its score
    const score = at.bottom + (at.top - at.bottom) * share;
    context.strokeStyle = solid(at.rule);
    context.beginPath();
    context.moveTo(PAD.left, at.y(score));
    context.lineTo(at.right, at.y(score));
    context.stroke();
    context.fillStyle = solid(at.ink);
    context.fillText(String(Math.round(score)), 8, at.y(score) + 4);
  }
  context.fillText(`Over ${ballsToOvers(at.first)}`, PAD.left, HEIGHT - 9);
  context.fillText(`Over ${ballsToOvers(at.last)}`, at.right - 44, HEIGHT - 9);
  if (!result.target) return;

  context.strokeStyle = solid(at.accent);
  context.setLineDash([5, 4]);
  context.beginPath();
  context.moveTo(PAD.left, at.y(result.target));
  context.lineTo(at.right, at.y(result.target));
  context.stroke();
  context.setLineDash([]);
  context.fillStyle = solid(at.accent);
  context.fillText(`Target ${result.target}`, PAD.left + 6, at.y(result.target) - 6);
}

/** Every innings is drawn up to the same ball, so they all grow together. */
function drawInnings(
  context: CanvasRenderingContext2D,
  result: Simulation,
  at: Layout,
  progress: number,
) {
  const reach = at.first + (at.last - at.first) * ease(progress);
  context.lineWidth = 1.2;
  for (const path of result.paths) {
    const won = result.target != null && path[path.length - 1][1] >= result.target;
    context.strokeStyle = won ? solid(at.accent, 0.5) : solid(at.line, 0.3);
    context.beginPath();
    for (const [ball, score] of path) {
      // the first point is the start
      if (ball > reach) break;
      context.lineTo(at.x(ball), at.y(score));
    }
    context.stroke();
  }
}

/** Where the innings ended: bars growing out of the right edge, one per band of final scores. */
function drawTally(
  context: CanvasRenderingContext2D,
  result: Simulation,
  at: Layout,
  progress: number,
) {
  const grown = ease(Math.max(0, (progress - TALLY_STARTS) / (1 - TALLY_STARTS)));
  if (grown === 0) return;
  const largest = Math.max(...result.histogram.map((band) => band.share));
  for (const band of result.histogram) {
    const won = result.target != null && band.low >= result.target;
    const length = (((PAD.right - 14) * band.share) / largest) * grown;
    const height = Math.max(1, at.y(band.low) - at.y(band.high) - 1);
    context.fillStyle = won ? solid(at.accent, 0.85) : solid(at.line, 0.75);
    context.fillRect(at.right + 6, at.y(band.high), length, height);
  }
}

function draw(canvas: HTMLCanvasElement, result: Simulation, progress: number) {
  const { context, width } = prepareCanvas(canvas, HEIGHT);
  const at = layout(result, width);
  context.clearRect(0, 0, width, HEIGHT);
  drawAxes(context, result, at);
  drawInnings(context, result, at, progress);
  drawTally(context, result, at, progress);
}

function resultSentence(result: Simulation): string {
  const range =
    `Four in five of the ${num(result.innings)} innings ended between ${num(result.low)}` +
    ` and ${num(result.high)}. The average was ${num(result.mean)}.`;
  if (result.win == null) return `${range} The side was bowled out in ${pct(result.all_out)} of them.`;
  return `The chase came off in ${pct(result.win)} of them. ${range}`;
}

export function Simulator() {
  const canvas = useRef<HTMLCanvasElement>(null);
  const shown = useRef<Simulation | null>(null);
  const stop = useRef(() => {});
  const [start, setStart] = useState<Start>(PRESETS[0].start);
  const [preset, setPreset] = useState(-1);
  const [busy, setBusy] = useState(false);
  const [says, setSays] = useState("Pick a starting point, or set your own.");

  const run = async (from: Start) => {
    stop.current();
    setBusy(true);
    setSays("The network is batting…");
    try {
      const result = await api<Simulation>("lab/simulate", {
        fmt: from.fmt,
        league: from.league,
        score: from.score,
        wickets: from.wickets,
        balls: oversToBalls(from.overs),
        target: from.target,
        seed: Math.floor(Math.random() * 1e6),
      });
      const element = canvas.current;
      if (!element) return;
      shown.current = result;
      stop.current = animate(DRAW_MS, (progress) => draw(element, result, progress), {
        alive: () => element.isConnected,
        done: () => setSays(resultSentence(result)),
      });
    } catch (error) {
      setSays((error as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const choose = (index: number) => {
    setPreset(index);
    setStart(PRESETS[index].start);
    run(PRESETS[index].start);
  };

  useEffect(() => {
    const element = canvas.current!;
    const unwatch = whenVisible(element, () => choose(FIRST_SHOWN));
    const observer = new ResizeObserver(() => shown.current && draw(element, shown.current, 1));
    observer.observe(element);
    return () => {
      unwatch();
      observer.disconnect();
      stop.current();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // A starting point typed by hand uses the format's usual league.
  const edit = (field: keyof Start) => (event: { target: { value: string } }) => {
    setPreset(-1);
    setStart({ ...start, league: "", [field]: event.target.value });
  };

  return (
    <div className="panel">
      <div className="pills flush">
        {PRESETS.map((item, index) => (
          <button
            key={item.name}
            className={index === preset ? "on" : ""}
            onClick={() => choose(index)}
          >
            {item.name}
          </button>
        ))}
      </div>
      <div className="filters">
        <label>
          Format{" "}
          <select value={start.fmt} onChange={edit("fmt")}>
            <option>T20</option>
            <option>ODI</option>
          </select>
        </label>
        <label>
          Score <input type="number" min="0" value={start.score} onChange={edit("score")} />
        </label>
        <label>
          Wickets{" "}
          <input type="number" min="0" max="9" value={start.wickets} onChange={edit("wickets")} />
        </label>
        <label>
          Overs bowled{" "}
          <input type="number" min="0" step="0.1" value={start.overs} onChange={edit("overs")} />
        </label>
        <label>
          Target{" "}
          <input
            type="number"
            min="1"
            placeholder="none"
            value={start.target}
            onChange={edit("target")}
          />
        </label>
        <button className="btn sm" disabled={busy} onClick={() => run(start)}>
          Simulate
        </button>
      </div>
      <canvas
        ref={canvas}
        className="lab-canvas"
        style={{ height: HEIGHT }}
        role="img"
        aria-label="Simulated innings"
      />
      <p className="prose small">
        <Marked text={says} />
      </p>
    </div>
  );
}
