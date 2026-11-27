// The scorecard tab of a match: pick an innings, read its batting and bowling cards.

"use client";

import { useState } from "react";

import { Cards } from "./Cards";
import { InningsPills } from "./InningsPills";
import type { ScorecardData } from "./types";

export function Scorecard({ data }: { data: ScorecardData }) {
  const [chosen, setChosen] = useState(0);
  const innings = data.innings[chosen];
  if (!innings) return null;
  return (
    <section className="scorecard">
      <InningsPills all={data.innings} chosen={chosen} choose={setChosen} />
      <Cards innings={innings} />
    </section>
  );
}
