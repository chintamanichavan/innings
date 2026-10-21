// The league drop-down on the records page. It changes the address so the server redraws the list.

"use client";

import { Options, useSetQuery } from "@/components/controls";

type Leagues = ([string, string] | string)[];

export function LeagueFilter({ leagues, current }: { leagues: Leagues; current: string }) {
  const setQuery = useSetQuery();
  return (
    <label>
      League
      <select value={current} onChange={(event) => setQuery({ league: event.target.value })}>
        <Options items={leagues} />
      </select>
    </label>
  );
}
