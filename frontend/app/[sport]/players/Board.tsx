// The leaderboard table. A click on a column header sorts by it; a second click flips the order.

"use client";

import { StatTable, type Lead } from "@/components/StatTable";
import { Crest, PlayerLink, TeamLink } from "@/components/teams";
import { useSetQuery } from "@/components/controls";
import type { Sport } from "@/lib/sport";

import type { LeaderRow, Leaders } from "./types";

interface BoardProps {
  sport: Sport;
  league: string;
  data: Leaders;
  ascending: boolean;
}

export function Board({ sport, league, data, ascending }: BoardProps) {
  const setQuery = useSetQuery();
  if (!data.rows.length) {
    return <p className="empty">No players meet the minimum. Lower it or pick another year.</p>;
  }
  const lead: Lead<LeaderRow>[] = [
    { label: "#", render: (row) => <span className="dim">{data.rows.indexOf(row) + 1}</span> },
    {
      label: "Player",
      render: (row) => <PlayerLink sport={sport} id={row.player_id} name={row.name} />,
    },
    {
      label: "Team",
      render: (row) => (
        <>
          <Crest team={row.team} size="sm" />
          <TeamLink sport={sport} league={league} team={row.team} />
        </>
      ),
    },
  ];
  const sortBy = (key: string) => {
    const flip = data.sort === key && !ascending;
    setQuery({ sort: key, asc: flip ? "true" : "" });
  };
  return (
    <StatTable
      columns={data.columns}
      rows={data.rows}
      rowKey={(row) => row.player_id}
      lead={lead}
      sort={data.sort}
      ascending={ascending}
      onSort={sortBy}
    />
  );
}
