// The matchup forecast panel: two team pickers. The forecast itself is worked out by the
// page and arrives as children.

"use client";

import type { ReactNode } from "react";

import { Options, useSetQuery } from "@/components/controls";

interface MatchupProps {
  teams: string[];
  a: string;
  b: string;
  children: ReactNode;
}

function Picker({
  slot,
  label,
  teams,
  team,
}: {
  slot: "a" | "b";
  label: string;
  teams: string[];
  team: string;
}) {
  const setQuery = useSetQuery();
  return (
    <div className="filters flush">
      <select
        aria-label={`${label} team`}
        value={team}
        onChange={(event) => setQuery({ [slot]: event.target.value })}
      >
        <Options items={teams} />
      </select>
    </div>
  );
}

export function Matchup({ teams, a, b, children }: MatchupProps) {
  return (
    <div className="panel">
      <p className="kicker quiet">Matchup forecast</p>
      <Picker slot="a" label="First" teams={teams} team={a} />
      <Picker slot="b" label="Second" teams={teams} team={b} />
      {children}
    </div>
  );
}
