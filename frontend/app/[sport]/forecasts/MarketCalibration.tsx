// The calibration chart for the market comparison, drawn in the browser.

"use client";

import { type CalibrationBin, CalibrationChart, CalibrationLegend } from "@/components/charts/small";

const SERIES = [
  { model: "market", color: "var(--series-2)", name: "Betfair market" },
  { model: "innings", color: "var(--series-1)", name: "Innings" },
];

export function MarketCalibration({ bins }: { bins: CalibrationBin[] }) {
  return (
    <>
      <CalibrationLegend series={SERIES} />
      <figure>
        <CalibrationChart bins={bins} side="" series={SERIES} />
      </figure>
    </>
  );
}
