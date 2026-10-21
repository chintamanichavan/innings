// The sheet that asks for the reader's teams. It opens by itself on a first
// visit, and from the Following page after that.

"use client";

import { useEffect, useRef, useState } from "react";

import { Crest } from "@/components/teams";
import { api } from "@/lib/api";
import type { Sport } from "@/lib/sport";
import { type FollowedTeam, MAX_TEAMS, followedTeams, store } from "@/lib/store";
import { reducedMotion } from "@/lib/motion";
import { toast } from "@/lib/toast";

const INTRO_MS = 2000; // how long the opening animation in Intro.tsx runs
export const OPEN_TEAM_SHEET = "innings:team-sheet";

/** Open the sheet from anywhere. */
export function openTeamSheet(): void {
  dispatchEvent(new Event(OPEN_TEAM_SHEET));
}

type Team = FollowedTeam & { elo: number };

const teamKey = (team: { sport: Sport; team: string }) => `${team.sport}|${team.team}`;
const groupKey = (team: Team) => `${team.sport}|${team.pool}`;

function groupTitle(key: string): string {
  return key.split("|")[1].replace("T20I", "National teams").replace(" (W)", ", women");
}

export function TeamSheet() {
  const sheet = useRef<HTMLDialogElement>(null);
  const [teams, setTeams] = useState<Team[]>([]);
  const [chosen, setChosen] = useState<Set<string>>(new Set());

  useEffect(() => {
    const open = async () => {
      setTeams(await api<Team[]>("onboarding"));
      setChosen(new Set(followedTeams().map(teamKey)));
      sheet.current?.showModal();
    };
    addEventListener(OPEN_TEAM_SHEET, open);
    // A first-time reader sees the opening animation first, then the sheet.
    const greet = store.get("onboarded", false)
      ? undefined
      : setTimeout(open, reducedMotion() ? 0 : INTRO_MS);
    return () => {
      removeEventListener(OPEN_TEAM_SHEET, open);
      clearTimeout(greet);
    };
  }, []);

  const toggle = (key: string) => {
    const next = new Set(chosen);
    if (next.has(key)) next.delete(key);
    else if (next.size >= MAX_TEAMS) {
      toast("Twelve teams is the limit");
      return;
    } else next.add(key);
    setChosen(next);
  };

  const close = () => {
    store.set("onboarded", true);
    if (sheet.current?.returnValue !== "save") return;
    const picked = teams.filter((team) => chosen.has(teamKey(team)));
    store.set(
      "teams",
      picked.map(({ sport, team, pool }) => ({ sport, team, pool })),
    );
    toast(picked.length ? "Your edition is ready" : "No teams followed");
  };

  const groups = [...new Set(teams.map(groupKey))];
  return (
    <dialog id="sheet" ref={sheet} onClose={close}>
      <form method="dialog" className="sheet">
        <header>
          <p className="kicker quiet">Welcome to Innings</p>
          <h2>Make it yours</h2>
          <p className="sub">Tell us your teams. You can change them any time under Following.</p>
        </header>
        <div className="body">
          {groups.map((group) => (
            <div key={group}>
              <p className="kicker quiet">{groupTitle(group)}</p>
              <div className="teampick">
                {teams
                  .filter((team) => groupKey(team) === group)
                  .map((team) => (
                    <button
                      key={teamKey(team)}
                      type="button"
                      aria-pressed={chosen.has(teamKey(team))}
                      onClick={() => toggle(teamKey(team))}
                    >
                      <Crest team={team.team} size="sm" />
                      {team.team}
                    </button>
                  ))}
              </div>
            </div>
          ))}
        </div>
        <footer>
          <span className="sub">{chosen.size ? `${chosen.size} chosen` : "None chosen yet"}</span>
          <span className="row">
            <button className="btn alt" value="skip">
              Skip
            </button>
            <button className="btn" value="save">
              Done
            </button>
          </span>
        </footer>
      </form>
    </dialog>
  );
}
