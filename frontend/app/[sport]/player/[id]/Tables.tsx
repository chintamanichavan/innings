// The player page's tables: season by season, splits, and the last games.

import Link from "next/link";
import { Fragment } from "react";

import { StatTable } from "@/components/StatTable";
import { Crest, TeamLink } from "@/components/teams";
import { WORDS, day, num, signed } from "@/lib/format";
import { type Sport, link } from "@/lib/sport";

import { roleName } from "./Sections";
import type { GameLine, Role, RoleTable, SeasonRow, Split } from "./types";

const ROLES: Role[] = ["bat", "bowl"];
const PER = 100; // splits show runs added per this many balls
const EXTRA_COLUMNS = 4; // Split label, RAE, RAE/n, WPA, beside the other columns
const PERCENT = 100;
const BALLS_PER_OVER = 6;

export function SeasonTables({
  sport,
  roles,
}: {
  sport: Sport;
  roles: Partial<Record<Role, RoleTable>>;
}) {
  const lead = [
    { label: "Year", render: (row: SeasonRow) => row.year },
    { label: "League", render: (row: SeasonRow) => row.league },
    {
      label: "Team",
      render: (row: SeasonRow) =>
        row.team && (
          <>
            <Crest team={row.team} size="sm" />
            <TeamLink sport={sport} league={row.league} team={row.team} />
          </>
        ),
    },
  ];
  return (
    <>
      {ROLES.map((role) => {
        const table = roles[role];
        if (!table) return null;
        const total = { ...table.total, year: "Career", league: "", team: "" };
        return (
          <Fragment key={role}>
            <h2 className="label">{roleName(sport, role)}, season by season</h2>
            <StatTable
              columns={table.columns}
              rows={table.rows}
              lead={lead}
              total={total}
              rowKey={(row) => `${row.year}${row.league}${row.team}`}
            />
          </Fragment>
        );
      })}
    </>
  );
}

type SplitColumn = [label: string, compute: (split: Split) => string];

function splitColumns(role: Role): SplitColumn[] {
  const rate =
    (top: keyof Split, bottom: keyof Split, digits: number, scale = 1) =>
    (split: Split) =>
      num((scale * Number(split[top])) / Number(split[bottom]), digits);
  return [
    ["Balls", (split) => num(split.n)],
    ["Runs", (split) => num(split.runs)],
    [role === "bat" ? "Outs" : "Wkts", (split) => num(split.outs)],
    role === "bat"
      ? ["SR", rate("runs", "n", 1, PERCENT)]
      : ["Econ", rate("runs", "n", 2, BALLS_PER_OVER)],
  ];
}

function SplitsTable({ role, splits }: { role: Role; splits: Split[] }) {
  const columns = splitColumns(role);
  return (
    <div className="scroll">
      <table>
        <thead>
          <tr>
            <th className="l">Split</th>
            {columns.map(([label]) => (
              <th key={label}>{label}</th>
            ))}
            <th>RAE</th>
            <th>RAE/{PER}</th>
            <th>WPA</th>
          </tr>
        </thead>
        <tbody>
          {splits.map((split, index) => (
            <Fragment key={`${split.dim}${split.key}`}>
              {split.dim !== splits[index - 1]?.dim && (
                <tr>
                  <td className="l group" colSpan={columns.length + EXTRA_COLUMNS}>
                    {split.dim}
                  </td>
                </tr>
              )}
              <tr>
                <td className="l">{split.key}</td>
                {columns.map(([label, compute]) => (
                  <td key={label}>{split.n ? compute(split) : "–"}</td>
                ))}
                <td>{signed(split.rae, 1)}</td>
                <td>{signed((PER * split.rae) / split.n, 1)}</td>
                <td>{signed(split.wpa, 2)}</td>
              </tr>
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface SplitsProps {
  sport: Sport;
  roles: Partial<Record<Role, RoleTable>>;
  splits: Split[];
}

export function SplitsSections({ sport, roles, splits }: SplitsProps) {
  return (
    <>
      {ROLES.filter((role) => roles[role] && splits.some((split) => split.role === role)).map(
        (role) => (
          <Fragment key={role}>
            <h2 className="label">{roleName(sport, role)} splits</h2>
            <SplitsTable role={role} splits={splits.filter((split) => split.role === role)} />
          </Fragment>
        ),
      )}
    </>
  );
}

export function GameLog({ sport, log }: { sport: Sport; log: GameLine[] }) {
  const words = WORDS[sport];
  const played = (count: number, text: string) => (count ? text : "–");
  return (
    <>
      <h2 className="label">Last 15 games</h2>
      <div className="scroll">
        <table>
          <thead>
            <tr>
              <th className="l">Date</th>
              <th className="l">Match</th>
              <th>Balls</th>
              <th>Bat RAE</th>
              <th>Bat WPA</th>
              <th>Bowled</th>
              <th>{words.bowler} RAE</th>
              <th>{words.bowler} WPA</th>
            </tr>
          </thead>
          <tbody>
            {log.map((game) => (
              <tr key={game.match_id}>
                <td className="l">
                  <Link className="u" href={link(sport, "match", game.match_id)}>
                    {day(game.date)}
                  </Link>
                </td>
                <td className="l sub">
                  {game.team1} v {game.team2}
                </td>
                <td>{num(game.bat_n)}</td>
                <td>{played(game.bat_n, signed(game.bat_v, 1))}</td>
                <td>{played(game.bat_n, signed(game.bat_w, 2))}</td>
                <td>{num(game.bowl_n)}</td>
                <td>{played(game.bowl_n, signed(game.bowl_v, 1))}</td>
                <td>{played(game.bowl_n, signed(game.bowl_w, 2))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
