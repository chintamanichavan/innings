// Records: the wildest games, the biggest comebacks, plays and single-game performances.

import type { Metadata } from "next";
import Link from "next/link";

import { Pills } from "@/components/controls";
import { Crest, PlayerLink } from "@/components/teams";
import { api } from "@/lib/api";
import { WORDS, day, num, pct, signed, yearOf } from "@/lib/format";
import { leaguesOf } from "@/lib/meta";
import { type PageProps, readPage } from "@/lib/page";
import { type Sport, link } from "@/lib/sport";

import { LeagueFilter } from "./LeagueFilter";
import type { Performance, RecordGame, RecordPlay } from "./types";

function kindsFor(sport: Sport): [key: string, label: string][] {
  return [
    ["thrillers", "Wildest games"],
    ["comebacks", "Biggest comebacks"],
    ["plays", "Biggest plays"],
    ["bat_games", "Best batting games"],
    ["bowl_games", `Best ${WORDS[sport].bowling.toLowerCase()} games`],
  ];
}

function GamesTable({ sport, games }: { sport: Sport; games: RecordGame[] }) {
  return (
    <div className="scroll">
      <table>
        <thead>
          <tr>
            <th className="l">#</th>
            <th className="l">Date</th>
            <th className="l">Match</th>
            <th className="l">Winner</th>
            <th>Thrill</th>
            <th>Winner&apos;s lowest chance</th>
            <th>Changes of favourite</th>
          </tr>
        </thead>
        <tbody>
          {games.map((game, index) => (
            <tr key={game.match_id}>
              <td className="l dim">{index + 1}</td>
              <td className="l">{day(game.date)}</td>
              <td className="l">
                <Link className="u" href={link(sport, "match", game.match_id)}>
                  {game.team1} {num(game.score1)}, {game.team2} {num(game.score2)}
                </Link>
              </td>
              <td className="l">
                <Crest team={game.winner} size="sm" />
                {game.winner}
              </td>
              <td>{num(game.thrill * 10, 1)}</td>
              <td>{num(game.winner_low * 100, 1)}%</td>
              <td>{game.lead_changes}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PlaysList({ sport, plays }: { sport: Sport; plays: RecordPlay[] }) {
  return (
    <div className="plays">
      {plays.map((play) => (
        <Link
          key={`${play.match_id}-${play.moment}-${play.text}`}
          className="play"
          href={link(sport, "match", play.match_id)}
        >
          <span className="when">
            {day(play.date).replace(/, \d+$/, "")}
            <br />
            {yearOf(play.date)}
          </span>
          <span className="what">
            {play.text}
            <small>
              {play.team1} v {play.team2} · {play.moment} · {play.league}
            </small>
          </span>
          <span className="swing">
            {pct(play.wp1)} → {pct(play.wp1_post)}
          </span>
        </Link>
      ))}
    </div>
  );
}

function PerformancesTable({ sport, games }: { sport: Sport; games: Performance[] }) {
  return (
    <div className="scroll">
      <table>
        <thead>
          <tr>
            <th className="l">#</th>
            <th className="l">Player</th>
            <th className="l">Date</th>
            <th className="l">Match</th>
            <th>Win chance added</th>
            <th>Runs above average</th>
          </tr>
        </thead>
        <tbody>
          {games.map((game, index) => (
            <tr key={`${game.player_id}-${game.match_id}`}>
              <td className="l dim">{index + 1}</td>
              <td className="l">
                <PlayerLink sport={sport} id={game.player_id} name={game.name} />
              </td>
              <td className="l">{day(game.date)}</td>
              <td className="l">
                <Link className="u" href={link(sport, "match", game.match_id)}>
                  {game.team1} v {game.team2}
                </Link>
              </td>
              <td>{signed(game.wpa * 100, 1)}%</td>
              <td>{signed(game.rae, 1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

async function RecordList({ sport, kind, league }: { sport: Sport; kind: string; league?: string }) {
  if (kind === "thrillers" || kind === "comebacks") {
    return (
      <GamesTable sport={sport} games={await api<RecordGame[]>("records", { sport, kind, league })} />
    );
  }
  if (kind === "plays") {
    return (
      <PlaysList sport={sport} plays={await api<RecordPlay[]>("records", { sport, kind, league })} />
    );
  }
  const games = await api<Performance[]>("records", { sport, kind, league });
  return <PerformancesTable sport={sport} games={games} />;
}

function titleOf(sport: Sport, kind: string): string {
  const kinds = kindsFor(sport);
  return kinds.find(([key]) => key === kind)?.[1] || kinds[0][1];
}

export async function generateMetadata(props: PageProps): Promise<Metadata> {
  const { sport, q } = await readPage(props);
  return { title: titleOf(sport, q.kind || "thrillers") };
}

export default async function Records(props: PageProps) {
  const { sport, q } = await readPage(props);
  const kind = q.kind || "thrillers";
  const kinds = kindsFor(sport);
  const tabs = kinds.map(([key, label]): [string, string, string] => [
    key,
    label,
    link(sport, "records", "", { ...q, kind: key }),
  ]);
  const leagues: ([string, string] | string)[] = [
    ["", "All"],
    ...(await leaguesOf(sport)).map((league) => league.league),
  ];

  return (
    <>
      <p className="kicker">Records</p>
      <h1 className="page">{titleOf(sport, kind)}</h1>
      <p className="standfirst">Ranked by how far the win chance moved. No opinions, only swings.</p>
      <Pills items={tabs} current={kind} />
      <div className="filters">
        <LeagueFilter leagues={leagues} current={q.league || ""} />
      </div>
      <RecordList sport={sport} kind={kind} league={q.league} />
    </>
  );
}
