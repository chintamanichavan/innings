// The league picker above the power rankings.

"use client";

import { Options, useSetQuery } from "@/components/controls";

const CLEARED = { a: "", b: "", all: "" }; // the old league's picks do not carry over

export function PoolFilter({ pools, pool }: { pools: string[]; pool: string }) {
  const setQuery = useSetQuery();
  return (
    <div className="filters">
      <label>
        League{" "}
        <select value={pool} onChange={(event) => setQuery({ ...CLEARED, pool: event.target.value })}>
          <Options items={pools} />
        </select>
      </label>
    </div>
  );
}
