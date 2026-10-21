// Loading one match. Cached, so the page and its link preview share a single request.

import { cache } from "react";

import { api } from "@/lib/api";
import type { Sport } from "@/lib/sport";

import type { MatchPage } from "./types";

export const loadMatch = cache((sport: Sport, id: string) =>
  api<MatchPage>(`match/${sport}/${encodeURIComponent(id)}`),
);
