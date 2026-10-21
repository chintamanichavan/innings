// The calibration chart, drawn in the browser: its helpers live in a client module.

"use client";

import { CalibrationChart, CalibrationLegend } from "@/components/charts/small";

import type { Evaluation } from "./types";

export function Calibration({ bins, side }: { bins: Evaluation["calibration"]; side: string }) {
  return (
    <>
      <CalibrationLegend />
      <figure>
        <CalibrationChart bins={bins} side={side} />
      </figure>
    </>
  );
}
