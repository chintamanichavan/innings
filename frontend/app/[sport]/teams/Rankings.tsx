// The power rankings table and the notes around it.

import Link from "next/link";

import { Crest, TeamLink } from "@/components/teams";
import { num, pct, signed } from "@/lib/format";
import { type Sport, link } from "@/lib/sport";

import type { Ratings } from "./types";

export function RankingsTable({
  sport,
  pool,
  rows,
}: {
  sport: Sport;
  pool: string;
  rows: Ratings["rows"];
}) {
  return (
    <div className="scroll">
      <table>
        <thead>
          <tr>
            <th className="l">#</th>
            <th className="l">Team</th>
            <th>Rating</th>
            <th>Last 10</th>
            <th>Batting</th>
            <th>Bowling</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((team, index) => (
            <tr key={team.team}>
              <td className="l dim">{index + 1}</td>
              <td className="l">
                <Crest team={team.team} size="sm" />
                <TeamLink sport={sport} league={pool} team={team.team} />
              </td>
              <td>{num(team.elo)}</td>
              <td>{pct(team.form)}</td>
              <td>{signed(team.bat, 2)}</td>
              <td>{signed(team.bowl, 2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** The note about member nations, which goes above the table. */
export function MembersNote({
  sport,
  ratings,
  q,
}: {
  sport: Sport;
  ratings: Ratings;
  q: Record<string, string>;
}) {
  if (!ratings.full_members_only) return null;
  return (
    <p className="note">
      Full member nations only. Ratings cannot compare teams that never meet.{" "}
      <Link className="u" href={link(sport, "teams", "", { ...q, all: "true" })}>
        Show all
      </Link>
    </p>
  );
}

/** What the columns mean, which goes below the table. */
export function ColumnsNote({ pool }: { pool: string }) {
  const tests = pool.startsWith("Test")
    ? "Test forecasts are the chance of winning if the match has a winner. Draws are left out. "
    : "";
  return (
    <p className="note">
      {tests}
      Batting and bowling are runs per game above average, from each player&apos;s past record.
    </p>
  );
}
