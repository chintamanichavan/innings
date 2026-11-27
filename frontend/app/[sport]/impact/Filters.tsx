// The impact boards' controls: batting or bowling, league, year and phase.

"use client";

import { Options, useSetQuery } from "@/components/controls";
import { PHASES } from "@/lib/slices";

interface FiltersProps {
  role: "bat" | "bowl";
  leagues: string[];
  league: string;
  years: number[];
  year: string; // "all" for every year
  phase: string;
}

export function Filters({ role, leagues, league, years, year, phase }: FiltersProps) {
  const setQuery = useSetQuery();
  return (
    <div className="filters">
      <div className="seg">
        {(["bat", "bowl"] as const).map((key) => (
          <button
            key={key}
            className={key === role ? "on" : ""}
            onClick={() => setQuery({ role: key })}
          >
            {key === "bat" ? "Batters" : "Bowlers"}
          </button>
        ))}
      </div>
      <label>
        League{" "}
        <select value={league} onChange={(event) => setQuery({ league: event.target.value, year: "" })}>
          <Options items={leagues} />
        </select>
      </label>
      <label>
        Year{" "}
        <select value={year} onChange={(event) => setQuery({ year: event.target.value })}>
          <Options items={[["all", "All"], ...years]} />
        </select>
      </label>
      <label>
        Phase{" "}
        <select value={phase} onChange={(event) => setQuery({ phase: event.target.value })}>
          <Options items={[["", "Whole innings"], ...PHASES.slice(0, 3)]} />
        </select>
      </label>
    </div>
  );
}
