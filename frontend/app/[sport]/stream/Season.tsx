// The season played many times over. While the job is running the tally changes every
// second, so this asks again every two seconds and redraws.

"use client";

import { useEffect, useState } from "react";

import { Crest } from "@/components/teams";
import { api } from "@/lib/api";
import { num, pct } from "@/lib/format";
import { type Report, type SeasonData, type Tally, bigNumber, byTitle, diskSize } from "@/lib/season";

import { OddsChart } from "./OddsChart";

const ASK_EVERY_MS = 2000;
const LEAGUE_MATCHES = 70;

function useSeason(initial: SeasonData): SeasonData {
  const [data, setData] = useState(initial);
  const running = data.tally?.running ?? false;
  useEffect(() => {
    if (!running) return;
    const timer = setInterval(() => void api<SeasonData>("season").then(setData), ASK_EVERY_MS);
    return () => clearInterval(timer);
  }, [running]);
  return data;
}

function Tiles({ tally, report }: { tally: Tally; report: Report | null }) {
  const tiles: [value: string, text: string][] = [
    [num(tally.seasons), tally.running ? `of ${num(tally.target)} seasons played` : "seasons played"],
    [bigNumber(tally.matches), "matches"],
    [bigNumber(tally.balls), "balls bowled, every one sent through Kafka"],
    [bigNumber(report?.balls_per_second ?? tally.balls_per_second), "balls a second, start to finish"],
  ];
  if (report) tiles.push([diskSize(report.lake.bytes), `of Parquet files hold all of them`]);
  return (
    <div className="tiles">
      {tiles.map(([value, text]) => (
        <div className="tile" key={text}>
          <b>{value}</b>
          <span>{text}</span>
        </div>
      ))}
    </div>
  );
}

/**
 * The average simulated season as an IPL points table (played, won, lost, points), then each
 * team's chance of the playoffs, the final and the title. The last column is the real season.
 */
function TitleTable({ tally }: { tally: Tally }) {
  const most = Math.max(...tally.title);
  const played = (LEAGUE_MATCHES * 2) / tally.teams.length;
  return (
    <div className="scroll">
      <table className="odds-table">
        <thead>
          <tr>
            <th>#</th>
            <th className="l">Team</th>
            <th>P</th>
            <th>W</th>
            <th>L</th>
            <th>Pts</th>
            <th>Top 4</th>
            <th>Final</th>
            <th className="l wide">Title</th>
            <th></th>
            <th>Real W</th>
          </tr>
        </thead>
        <tbody>
          {byTitle(tally).map((team, place) => {
            const name = tally.teams[team];
            const wins = tally.league_wins[team];
            return (
              <tr key={name}>
                <td>{place + 1}</td>
                <td className="l">
                  <Crest team={name} size="sm" />
                  {name}
                  {tally.real.champion === name && <span className="chip">real champion</span>}
                </td>
                <td>{played}</td>
                <td>{num(wins, 1)}</td>
                <td>{num(played - wins, 1)}</td>
                <td>
                  <b>{num(wins * 2, 1)}</b>
                </td>
                <td>{pct(tally.playoffs[team])}</td>
                <td>{pct(tally.final[team])}</td>
                <td className="l wide">
                  <div className="odds-bar">
                    <i style={{ width: `${(tally.title[team] / most) * 100}%` }} />
                  </div>
                </td>
                <td>
                  <b>{pct(tally.title[team])}</b>
                </td>
                <td>{tally.real.league_wins[team]}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** The five stops the data makes, each with the number measured there. */
function DataPath({ report }: { report: Report }) {
  const slowest = Math.max(...report.findings.map((finding) => finding.seconds));
  const stops: [name: string, figure: string, does: string][] = [
    [
      "Graphics card",
      `${bigNumber(report.made.balls / report.made.playing_seconds)} balls a second`,
      "The network plays 70,000 innings at once",
    ],
    [
      "Kafka",
      `${bigNumber(report.made.matches)} messages`,
      "One finished match each, 729 bytes, in 6 lanes",
    ],
    [
      `${report.lake.writers} lake writers`,
      `${bigNumber(report.lake.rows_per_second)} rows a second`,
      "Unpack each match into one row a ball",
    ],
    [
      "Parquet lake",
      diskSize(report.lake.bytes),
      `${report.lake.files} files, ${bigNumber(report.lake.rows)} rows`,
    ],
    ["DuckDB", `${num(slowest, 1)} seconds at most`, "Answers a question over every ball"],
  ];
  const { simulator, tally, lake } = report.counts;
  const agree = simulator === tally && tally === lake;
  return (
    <div className="panel pipe">
      <ol>
        {stops.map(([name, figure, does]) => (
          <li key={name}>
            <b>{name}</b>
            <em>{figure}</em>
            <span>{does}</span>
          </li>
        ))}
      </ol>
      <p className="note">
        Three programs each counted the balls: the simulator {num(simulator)}, the tally {num(tally)},
        the lake {num(lake)}.{" "}
        {agree
          ? "They agree, so nothing was lost and nothing was counted twice."
          : "They do not agree."}{" "}
        The whole job took {num(report.seconds / 60, 1)} minutes.
      </p>
    </div>
  );
}

function Findings({ report }: { report: Report }) {
  return (
    <div className="cols3 findings">
      {report.findings.map((finding) => (
        <article className="card" key={finding.title}>
          <div className="body">
            <p className="kicker quiet">{finding.title}</p>
            <b className="finding-value">{finding.value}</b>
            <p className="dek">{finding.text}</p>
            <p className="note">
              Answered in {num(finding.seconds, 1)} seconds, from {bigNumber(report.lake.rows)} rows.
            </p>
          </div>
        </article>
      ))}
    </div>
  );
}

export function Season({ initial }: { initial: SeasonData }) {
  const { tally, report } = useSeason(initial);
  if (!tally) {
    return (
      <p className="note">
        No season has been played yet. <code>uv run innings season run</code> plays one 100,000 times.
      </p>
    );
  }
  // The report belongs to the last finished job. While a new one runs, show only what is live.
  const finished = tally.running ? null : report;
  return (
    <>
      <Tiles tally={tally} report={finished} />

      <h2 className="label">Who wins the title</h2>
      <p className="note pulled">
        {tally.running ? "The job is running now, and these numbers are moving. " : ""}
        The average of all the simulated seasons, as a points table. P, W, L and Pts are per season.
        Every match kept its real ground, batting order and bowlers; only the balls were played again.
        Real W is what each team really won.
      </p>
      <TitleTable tally={tally} />

      <h2 className="label">Watch the odds settle</h2>
      <OddsChart tally={tally} />

      {finished && (
        <>
          <h2 className="label">The path of the data</h2>
          <DataPath report={finished} />

          <h2 className="label">Asked of the lake</h2>
          <p className="note pulled">
            With every ball of every season on disk, some questions become easy. Each answer below is
            one query over all {bigNumber(finished.lake.rows)} rows.
          </p>
          <Findings report={finished} />
        </>
      )}
    </>
  );
}
