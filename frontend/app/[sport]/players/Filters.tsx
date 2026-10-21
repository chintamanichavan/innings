// The leaderboard's filters: role, league, year and the minimum. Each change reloads the page.

"use client";

import { Options, useSetQuery } from "@/components/controls";
import { WORDS } from "@/lib/format";
import type { Sport } from "@/lib/sport";

interface FiltersProps {
  sport: Sport;
  role: string;
  leagues: string[];
  league: string;
  years: number[];
  year: string; // "" for all years
  minimum: number;
  minimumOf: string; // what the minimum counts, in words
}

export function Filters(props: FiltersProps) {
  const { sport, role, leagues, league, years, year, minimum, minimumOf } = props;
  const setQuery = useSetQuery();
  const words = WORDS[sport];
  const setMinimum = (value: string) => {
    if (value !== String(minimum)) setQuery({ min: value });
  };
  return (
    <div className="filters">
      <div className="seg">
        {["bat", "bowl"].map((key) => (
          <button
            key={key}
            className={key === role ? "on" : ""}
            onClick={() => setQuery({ role: key, sort: "", min: "" })}
          >
            {words[key]}
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
        <select
          value={year || "all"}
          onChange={(event) => setQuery({ year: event.target.value, min: "" })}
        >
          <Options items={[["all", "All"], ...years]} />
        </select>
      </label>
      <label>
        At least{" "}
        <input
          type="number"
          min="0"
          defaultValue={minimum}
          key={minimum}
          onBlur={(event) => setMinimum(event.target.value)}
          onKeyDown={(event) => event.key === "Enter" && setMinimum(event.currentTarget.value)}
        />{" "}
        {minimumOf}
      </label>
    </div>
  );
}
