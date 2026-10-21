// The league, year and team drop-downs of the match list. They change the address, so the server redraws.

"use client";

import { Options, useSetQuery } from "@/components/controls";

interface FiltersProps {
  leagues: string[];
  league: string;
  years: number[];
  year: number | string;
  teams: string[];
  team: string;
  count: number;
}

export function Filters({ leagues, league, years, year, teams, team, count }: FiltersProps) {
  const setQuery = useSetQuery();
  return (
    <div className="filters">
      <label>
        League
        <select
          value={league}
          onChange={(e) => setQuery({ league: e.target.value, year: "", team: "" })}
        >
          <Options items={leagues} />
        </select>
      </label>
      <label>
        Year
        <select value={year} onChange={(e) => setQuery({ year: e.target.value })}>
          <Options items={years} />
        </select>
      </label>
      <label>
        Team
        <select value={team} onChange={(e) => setQuery({ team: e.target.value })}>
          <Options items={[["", "All"], ...teams]} />
        </select>
      </label>
      <span className="note flush">{count} matches</span>
    </div>
  );
}
