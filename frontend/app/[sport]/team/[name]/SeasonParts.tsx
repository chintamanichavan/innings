// A team's latest season as a fan follows it: where it stands in the table, and who played.

import Link from "next/link";

import { Crest, Face, TeamLink } from "@/components/teams";
import { num } from "@/lib/format";
import { type Sport, link } from "@/lib/sport";

import type { SquadPlayer, TableRow } from "./types";

const PLAYOFF_PLACES = 4;
const ROLES: SquadPlayer["role"][] = ["Batters", "Wicketkeepers", "All-rounders", "Bowlers"];

interface TableProps {
  sport: Sport;
  pool: string;
  team: string;
  rows: TableRow[];
}

/** P W L NR Pts NRR, the top four marked as the playoff places, this team picked out. */
export function PointsTable({ sport, pool, team, rows }: TableProps) {
  return (
    <div className="scroll">
      <table className="points">
        <thead>
          <tr>
            <th>#</th>
            <th className="l">Team</th>
            <th>P</th>
            <th>W</th>
            <th>L</th>
            <th>NR</th>
            <th>Pts</th>
            <th>NRR</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr
              key={row.team}
              className={`${row.team === team ? "us" : ""} ${index === PLAYOFF_PLACES - 1 ? "cut" : ""}`}
            >
              <td>{index + 1}</td>
              <td className="l">
                <Crest team={row.team} size="sm" />
                <TeamLink sport={sport} league={pool} team={row.team} />
              </td>
              <td>{row.played}</td>
              <td>{row.won}</td>
              <td>{row.lost}</td>
              <td>{row.no_result}</td>
              <td>
                <b>{row.points}</b>
              </td>
              <td>
                {row.net_run_rate > 0 ? "+" : ""}
                {num(row.net_run_rate, 3)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Everyone the team picked, by role, with their matches, runs and wickets this season. */
export function Squad({ sport, players }: { sport: Sport; players: SquadPlayer[] }) {
  return (
    <div className="squad">
      {ROLES.filter((role) => players.some((player) => player.role === role)).map((role) => (
        <section key={role}>
          <p className="sb-label">{role}</p>
          {players
            .filter((player) => player.role === role)
            .map((player) => (
              <Link
                key={player.player_id}
                className="squad-row"
                href={link(sport, "player", player.player_id)}
              >
                <Face name={player.name} size="sm" />
                <span>{player.name}</span>
                <small>
                  {player.matches} m · {player.runs} r{player.wickets ? ` · ${player.wickets} w` : ""}
                </small>
              </Link>
            ))}
        </section>
      ))}
    </div>
  );
}
