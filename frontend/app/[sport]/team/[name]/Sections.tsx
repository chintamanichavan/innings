// The team page's sections below the headline: best players and seasons.

import Link from "next/link";

import { PlayerRow } from "@/components/teams";
import { num, pct, signed } from "@/lib/format";
import { type Sport, link } from "@/lib/sport";

import type { BestPlayer, Season } from "./types";

const LEADERS_SHOWN = 5;

export function Leaders({
  sport,
  title,
  players,
}: {
  sport: Sport;
  title: string;
  players: BestPlayer[];
}) {
  return (
    <div>
      <p className="kicker">{title}</p>
      <div className="rows">
        {players.slice(0, LEADERS_SHOWN).map((player) => (
          <PlayerRow
            key={player.player_id}
            sport={sport}
            player={player}
            small=""
            value={signed(player.rae, 0)}
          />
        ))}
      </div>
    </div>
  );
}

export function SeasonsTable({
  sport,
  team,
  seasons,
}: {
  sport: Sport;
  team: string;
  seasons: Season[];
}) {
  return (
    <>
      <h2 className="label">Season by season</h2>
      <div className="scroll">
        <table>
          <thead>
            <tr>
              <th className="l">Year</th>
              <th className="l">League</th>
              <th>Won</th>
              <th>Lost</th>
              <th>Win %</th>
              <th>Runs for</th>
              <th>Runs against</th>
            </tr>
          </thead>
          <tbody>
            {seasons.map((season) => {
              const decided = season.w + season.l;
              const games = link(sport, "matches", "", {
                league: season.league,
                year: season.year,
                team,
              });
              return (
                <tr key={`${season.year}${season.league}`}>
                  <td className="l">
                    <Link className="u" href={games}>
                      {season.year}
                    </Link>
                  </td>
                  <td className="l sub">{season.league}</td>
                  <td>{season.w}</td>
                  <td>{season.l}</td>
                  <td>{decided ? pct(season.w / decided) : "–"}</td>
                  <td>{num(season.rf)}</td>
                  <td>{num(season.ra)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
