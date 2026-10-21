// The forecaster: every call on the record, scored by one rule.

import type { Metadata } from "next";

import { LineChart } from "@/components/charts/LineChart";
import { Marked } from "@/components/Marked";
import { api } from "@/lib/api";
import { num } from "@/lib/format";
import { type PageProps, readPage } from "@/lib/page";

import { Calibration } from "./Calibration";
import { Market } from "./Market";
import { ByLeague, LatestCalls, RecordTiles, WorstMisses } from "./Record";
import type { Evaluation, ForecastPage, MarketPage } from "./types";

export const metadata: Metadata = {
  title: "Every call, on the record",
  description: "We name a winner before each game and score ourselves by one rule.",
};

const RULE =
  "Say a side has a 70% chance. If it wins, you score +16 points. If it loses, you score " +
  "−24 points. A coin-flip call always scores 0 points. Being sure and wrong costs −75 points.";

export default async function Forecasts(props: PageProps) {
  const { sport } = await readPage(props);
  const [page, evaluation, market] = await Promise.all([
    api<ForecastPage>("forecasts", { sport }),
    api<Evaluation>("eval", { sport }),
    api<MarketPage | null>("market", { sport }),
  ]);
  const { record } = page;
  const summary =
    "We name a winner before each game and score ourselves by one rule. " +
    `So far: ${num(record.n)} calls, ${num((100 * record.right) / record.n, 1)}% right.`;

  return (
    <>
      <p className="kicker">The forecaster</p>
      <h1>Every call, on the record</h1>
      <p className="standfirst">
        <Marked text={summary} />
      </p>
      <div className="panel puzzle narrow spaced">
        <p className="kicker quiet">The one rule</p>
        <p className="prose small">
          <Marked text={RULE} /> The same rule scores us and scores you. This is a game of judgement,
          not betting advice.
        </p>
      </div>
      <RecordTiles record={record} />
      <figure>
        <LineChart points={page.series} label="Points so far" reference={0} />
        <figcaption>
          Our running points total. It climbs when calls are good and falls when we are sure and wrong.
          A coin flip would stay flat at zero.
        </figcaption>
      </figure>
      <div className="cols2">
        <ByLeague leagues={page.by_league} />
        <section>
          <h2 className="label">Is a 70% call right 70% of the time?</h2>
          <Calibration bins={evaluation.calibration} side="batting first" />
        </section>
      </div>
      {market && <Market market={market} />}
      <WorstMisses sport={sport} misses={page.misses} />
      <LatestCalls sport={sport} calls={page.recent} />
    </>
  );
}
