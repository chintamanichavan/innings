// Two search boxes for choosing the players to compare. A choice goes into the address.

"use client";

import { SearchBox } from "@/components/SearchBox";
import { useSetQuery } from "@/components/controls";
import type { Found } from "@/lib/types";

export function Pickers({ first, second }: { first?: string; second?: string }) {
  const setQuery = useSetQuery();
  const choose = (slot: "a" | "b") => (found: Found) => {
    if (found.kind === "player") setQuery({ [slot]: found.player_id });
  };
  return (
    <div className="filters">
      <SearchBox inline playersOnly placeholder="First player" shown={first} onPick={choose("a")} />
      <span className="sub">and</span>
      <SearchBox inline playersOnly placeholder="Second player" shown={second} onPick={choose("b")} />
    </div>
  );
}
