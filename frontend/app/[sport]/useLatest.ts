// The newest match of each team the reader follows. Teams live on the device, so this runs in the browser.

"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { Sport } from "@/lib/sport";
import { type FollowedTeam, teamsParam, useStored } from "@/lib/store";

import type { TeamLatest } from "./types";

/** `undefined` until loaded. Pass a sport to keep only that sport's teams. */
export function useLatest(sport?: Sport): TeamLatest[] | undefined {
  const all = useStored<FollowedTeam[]>("teams", []);
  const wanted = teamsParam(sport ? all.filter((team) => team.sport === sport) : all);
  const [loaded, setLoaded] = useState<{ wanted: string; latest: TeamLatest[] }>();

  useEffect(() => {
    if (!wanted) return;
    let current = true;
    api<TeamLatest[]>("my", { teams: wanted })
      .then((latest) => current && setLoaded({ wanted, latest }))
      .catch(() => {});
    return () => {
      current = false;
    };
  }, [wanted]);

  if (!wanted) return [];
  return loaded?.wanted === wanted ? loaded.latest : undefined;
}
