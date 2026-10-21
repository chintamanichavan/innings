// The forecast accuracy chart. It is drawn in the browser, as the shared chart helpers are.

"use client";

import { CalibrationChart } from "@/components/charts/small";

import type { Evaluation } from "./types";

export function Calibration({ bins, side }: { bins: Evaluation["calibration"]; side: string }) {
  return <CalibrationChart bins={bins} side={side} />;
}
