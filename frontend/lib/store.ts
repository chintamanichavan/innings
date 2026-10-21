// What this device remembers: the reader's teams, players, streaks and calls.
// Browsers can block storage, so every read has a fallback and every write may be dropped.

"use client";

import { useSyncExternalStore } from "react";

import type { Sport } from "./sport";
import { toast } from "./toast";

const PREFIX = "innings.";
const CHANGED = "innings:stored";
const MAX_PLAYERS = 40;
export const MAX_TEAMS = 12;

export const store = {
  get<T>(key: string, fallback: T): T {
    try {
      return (JSON.parse(localStorage.getItem(PREFIX + key) ?? "null") as T | null) ?? fallback;
    } catch {
      return fallback;
    }
  },
  set(key: string, value: unknown): void {
    try {
      localStorage.setItem(PREFIX + key, JSON.stringify(value));
    } catch {
      // Storage is blocked. The page still works; it just forgets.
    }
    dispatchEvent(new Event(CHANGED));
  },
};

function subscribe(onChange: () => void): () => void {
  addEventListener(CHANGED, onChange);
  addEventListener("storage", onChange);
  return () => {
    removeEventListener(CHANGED, onChange);
    removeEventListener("storage", onChange);
  };
}

const rawValue = (key: string) => {
  try {
    return localStorage.getItem(PREFIX + key);
  } catch {
    return null;
  }
};

/**
 * A stored value that redraws the component when it changes. The server, which cannot see
 * the device, renders the fallback; the browser swaps in the real value once it has loaded.
 */
export function useStored<T>(key: string, fallback: T): T {
  const raw = useSyncExternalStore(
    subscribe,
    () => rawValue(key),
    () => null,
  );
  if (raw == null) return fallback;
  try {
    return (JSON.parse(raw) as T | null) ?? fallback;
  } catch {
    return fallback;
  }
}

/** True once the page is running in the browser, so device-only parts can be shown. */
export function useOnDevice(): boolean {
  return useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
}

// ---- following ----

export interface FollowedPlayer {
  sport: Sport;
  id: string;
  name: string;
}

export interface FollowedTeam {
  sport: Sport;
  team: string;
  pool: string;
}

export function followedPlayers(): FollowedPlayer[] {
  return store.get<FollowedPlayer[]>("follows", []);
}

/** Follow or unfollow a player. Returns true if now following. */
export function togglePlayer(player: FollowedPlayer): boolean {
  const list = followedPlayers();
  const at = list.findIndex((p) => p.sport === player.sport && p.id === player.id);
  const nowFollowing = at < 0;
  if (nowFollowing) list.unshift(player);
  else list.splice(at, 1);
  store.set("follows", list.slice(0, MAX_PLAYERS));
  toast(nowFollowing ? `Following ${player.name}` : `Stopped following ${player.name}`);
  return nowFollowing;
}

export function followedTeams(): FollowedTeam[] {
  return store.get<FollowedTeam[]>("teams", []);
}

/** Follow or unfollow a team. Returns true if now following. */
export function toggleTeam(team: FollowedTeam): boolean {
  const list = followedTeams();
  const at = list.findIndex((t) => t.sport === team.sport && t.team === team.team);
  const nowFollowing = at < 0;
  if (nowFollowing) list.push(team);
  else list.splice(at, 1);
  store.set("teams", list.slice(0, MAX_TEAMS));
  toast(nowFollowing ? `Following ${team.team}` : `Stopped following ${team.team}`);
  return nowFollowing;
}

/** The followed teams as the server's `teams` parameter: 'ck|India;ck|Australia'. */
export function teamsParam(teams: FollowedTeam[]): string {
  return teams.map((t) => `${t.sport}|${t.team}`).join(";");
}

/** Today's date as the reader's own calendar has it: 2026-10-08. */
export function today(): string {
  return new Date().toLocaleDateString("en-CA");
}
