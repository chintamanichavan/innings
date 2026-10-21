// The league drop-down of the cricket model; choosing one reloads the page with that league.

"use client";

import { Options, useSetQuery } from "@/components/controls";

export function LeaguePicker({ leagues, current }: { leagues: string[]; current: string }) {
  const setQuery = useSetQuery();
  return (
    <div className="filters">
      <label>
        League
        <select value={current} onChange={(event) => setQuery({ league: event.target.value })}>
          <Options items={leagues} />
        </select>
      </label>
    </div>
  );
}
