// The matchup's controls: the two players, how to split, and the slice of cricket.
// Each change goes into the address, so any matchup can be shared as a link.

"use client";

import { Options, useSetQuery } from "@/components/controls";
import { SearchBox } from "@/components/SearchBox";
import { BOWLING_TYPES, PHASES, type SliceQuery, splitsFor } from "@/lib/slices";
import type { Found } from "@/lib/types";

interface FiltersProps {
  slice: SliceQuery;
  role: "bat" | "bowl";
  names: { batter?: string; bowler?: string };
  leagues: string[];
  years: number[];
}

const FORMATS = ["T20", "ODI", "Test"];

export function Filters({ slice, role, names, leagues, years }: FiltersProps) {
  const setQuery = useSetQuery();
  const pick = (slot: "batter" | "bowler") => (found: Found) => {
    if (found.kind === "player") setQuery({ [slot]: found.player_id, role: "", sort: "" });
  };
  const select = (
    name: keyof SliceQuery,
    label: string,
    items: (string | number | [string, string])[],
  ) => (
    <label>
      {label}{" "}
      <select
        value={slice[name] ?? ""}
        onChange={(event) => setQuery({ [name]: event.target.value, sort: "" })}
      >
        <Options items={[["", "All"], ...items]} />
      </select>
    </label>
  );
  const yearItems = years.map((year): [string, string] => [String(year), String(year)]);
  return (
    <>
      <div className="filters">
        <SearchBox
          inline
          playersOnly
          placeholder="Batter"
          shown={names.batter}
          onPick={pick("batter")}
        />
        <SearchBox
          inline
          playersOnly
          placeholder="Bowler"
          shown={names.bowler}
          onPick={pick("bowler")}
        />
        {(slice.batter || slice.bowler) && (
          <button className="btn alt sm" onClick={() => setQuery({ batter: "", bowler: "", role: "" })}>
            Clear players
          </button>
        )}
      </div>
      <div className="filters">
        <label>
          Split by{" "}
          <select
            value={slice.by || "none"}
            onChange={(event) => setQuery({ by: event.target.value, sort: "" })}
          >
            <Options items={[["none", "Nothing"], ...splitsFor(role)]} />
          </select>
        </label>
        {role === "bat" ? select("type", "Bowling", BOWLING_TYPES) : select("hand", "Batters", HANDS)}
        {select("phase", "Phase", PHASES)}
        {select("fmt", "Format", FORMATS)}
        {select("league", "League", leagues)}
        {select("first", "From", yearItems)}
        {select("last", "To", yearItems)}
      </div>
    </>
  );
}

const HANDS: [string, string][] = [
  ["L", "Left-handers"],
  ["R", "Right-handers"],
];
