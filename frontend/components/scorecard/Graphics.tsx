// The three pictures a television broadcast shows of an innings: the worm (both sides' scores
// over by over), the Manhattan (runs in each over) and the partnerships.

"use client";

import { Svg, useWidth, xy } from "@/components/charts/base";
import { GrowBar } from "@/components/motion";
import { capital } from "@/lib/format";
import { tip } from "@/lib/toast";

import { type InningsCard, type Over, inningsName } from "./types";

const SERIES = ["var(--series-1)", "var(--series-2)"];
const PAD = { left: 40, right: 16, top: 14, bottom: 28 };
const HEIGHT = 250;
const BAR_STAGGER_MS = 18; // each Manhattan bar starts growing this long after the one before

/** The colour of an innings: one per side, so a side's two Test innings match. */
function colorOf(innings: InningsCard, all: InningsCard[]): string {
  const sides = [...new Set(all.map((other) => other.team))];
  return SERIES[sides.indexOf(innings.team) % SERIES.length];
}

const isSecondOfSide = (innings: InningsCard, all: InningsCard[]) =>
  all.find((other) => other.team === innings.team) !== innings;

/** "a wicket", or "3 wickets". */
const wicketsText = (count: number) => (count === 1 ? "a wicket" : `${count} wickets`);

/** Round marks along an axis: about `count` of them, from zero up to `highest`. */
function ticks(highest: number, count: number): number[] {
  const rough = highest / count;
  const size = 10 ** Math.floor(Math.log10(rough || 1));
  const step = [1, 2, 5, 10].map((times) => times * size).find((value) => value >= rough) ?? size;
  const marks = [];
  for (let value = 0; value <= highest; value += step) marks.push(value);
  return marks;
}

function Legend({ all }: { all: InningsCard[] }) {
  return (
    <div className="legend">
      {all.map((innings) => (
        <span key={innings.number}>
          <i
            style={{
              background: colorOf(innings, all),
              opacity: isSecondOfSide(innings, all) ? 0.5 : 1,
            }}
          />
          {inningsName(innings, all)}
        </span>
      ))}
      <span>
        <i className="wicket-dot" />
        Wicket
      </span>
    </div>
  );
}

/** Every innings' score, over by over, on one chart. A dot marks each wicket. */
export function Worm({ all }: { all: InningsCard[] }) {
  const [box, width] = useWidth();
  if (!width) return <div ref={box} className="chart-slot" />;
  const longest = Math.max(...all.map((innings) => innings.by_over.length));
  const highest = Math.max(...all.map((innings) => innings.runs)) * 1.05;
  const x = (over: number) => PAD.left + ((width - PAD.left - PAD.right) * over) / longest;
  const y = (score: number) =>
    HEIGHT - PAD.bottom - ((HEIGHT - PAD.top - PAD.bottom) * score) / highest;
  return (
    <div ref={box} className="chart-slot">
      <Svg width={width} height={HEIGHT} label="Each side's score, over by over">
        {ticks(highest, 4).map((score) => (
          <g key={score}>
            <line className="axis" x1={PAD.left} x2={width - PAD.right} y1={y(score)} y2={y(score)} />
            <text x={PAD.left - 7} y={y(score) + 4} textAnchor="end">
              {score}
            </text>
          </g>
        ))}
        {ticks(longest, 8)
          .filter(Boolean)
          .map((over) => (
            <text key={over} x={x(over)} y={HEIGHT - 8} textAnchor="middle">
              {over}
            </text>
          ))}
        {all.map((innings) => {
          const color = colorOf(innings, all);
          const points = [
            xy(x(0), y(0)),
            ...innings.by_over.map((over) => xy(x(over.over), y(over.score))),
          ];
          return (
            <g key={innings.number} opacity={isSecondOfSide(innings, all) ? 0.5 : 1}>
              <polyline
                className="draw"
                pathLength={1}
                points={points.join(" ")}
                fill="none"
                stroke={color}
                strokeWidth="2.5"
                strokeLinejoin="round"
              />
              {innings.by_over
                .filter((over) => over.wickets > 0)
                .map((over) => (
                  <circle
                    key={over.over}
                    cx={x(over.over)}
                    cy={y(over.score)}
                    r="4"
                    fill="var(--card)"
                    stroke={color}
                    strokeWidth="2"
                    {...tip(
                      `${innings.team}, over ${over.over}`,
                      `${capital(wicketsText(over.wickets))} fell. Score ${over.score}.`,
                    )}
                  />
                ))}
            </g>
          );
        })}
      </Svg>
      <Legend all={all} />
    </div>
  );
}

/** Runs in each over of one innings, as a row of bars. A dot above a bar is a wicket. */
export function Manhattan({ innings, all }: { innings: InningsCard; all: InningsCard[] }) {
  const [box, width] = useWidth();
  if (!width) return <div ref={box} className="chart-slot" />;
  const overs = innings.by_over;
  // One scale for the whole match, so two innings can be compared by eye.
  const highest = Math.max(6, ...all.flatMap((other) => other.by_over.map((over) => over.runs))) + 3;
  const slot = (width - PAD.left - PAD.right) / overs.length;
  const barWidth = Math.max(1, Math.min(22, slot * 0.72));
  const x = (index: number) => PAD.left + slot * (index + 0.5);
  const y = (runs: number) => HEIGHT - PAD.bottom - ((HEIGHT - PAD.top - PAD.bottom) * runs) / highest;
  const color = colorOf(innings, all);
  const wicketDots = (over: Over, index: number) =>
    Array.from({ length: over.wickets }, (_, nth) => (
      <circle key={nth} cx={x(index)} cy={y(over.runs) - 8 - nth * 9} r="3.5" className="wicket-dot" />
    ));
  return (
    <div ref={box} className="chart-slot">
      <Svg width={width} height={HEIGHT} label={`Runs in each over, ${innings.team}`}>
        {ticks(highest, 4).map((runs) => (
          <g key={runs}>
            <line className="axis" x1={PAD.left} x2={width - PAD.right} y1={y(runs)} y2={y(runs)} />
            <text x={PAD.left - 7} y={y(runs) + 4} textAnchor="end">
              {runs}
            </text>
          </g>
        ))}
        {ticks(overs.length, 8)
          .filter(Boolean)
          .map((over) => (
            <text key={over} x={x(over - 1)} y={HEIGHT - 8} textAnchor="middle">
              {over}
            </text>
          ))}
        {overs.map((over, index) => (
          <g
            key={over.over}
            {...tip(
              `Over ${over.over}`,
              `${over.runs} runs${over.wickets ? `, ${wicketsText(over.wickets)}` : ""}.` +
                ` Score ${over.score}.`,
            )}
          >
            <rect
              className="manhattan-bar"
              x={x(index) - barWidth / 2}
              y={y(over.runs)}
              width={barWidth}
              height={y(0) - y(over.runs)}
              fill={color}
              rx={Math.min(3, barWidth / 3)}
              style={{ animationDelay: `${index * BAR_STAGGER_MS}ms` }}
            />
            {wicketDots(over, index)}
          </g>
        ))}
      </Svg>
    </div>
  );
}

/** Each stand as a bar split between its two batters, widest for the biggest stand. */
export function Partnerships({ innings }: { innings: InningsCard }) {
  const largest = Math.max(1, ...innings.partnerships.map((stand) => stand.runs));
  return (
    <div className="stands">
      {innings.partnerships.map((stand) => {
        const [first, second] = stand.batters;
        const firstShare = stand.runs ? (100 * first.runs) / stand.runs : 50;
        return (
          <div
            className="stand"
            key={stand.wicket}
            {...tip(
              `${stand.runs} runs off ${stand.balls} balls`,
              `${first.name} ${first.runs}${second ? `, ${second.name} ${second.runs}` : ""}. ` +
                "The rest were extras.",
            )}
          >
            <span className="who l">
              {first.name} <b>{first.runs}</b>
            </span>
            <div className="split" style={{ width: `${Math.max(6, (100 * stand.runs) / largest)}%` }}>
              <GrowBar percent={firstShare} />
            </div>
            <span className="who">
              {second && (
                <>
                  <b>{second.runs}</b> {second.name}
                </>
              )}
            </span>
            <b className="sum">{stand.runs}</b>
          </div>
        );
      })}
    </div>
  );
}
