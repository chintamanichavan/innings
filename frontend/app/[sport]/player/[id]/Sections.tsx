// The player page's skill profile.

import { SkillBars } from "@/components/charts/small";
import { WORDS } from "@/lib/format";
import type { Sport } from "@/lib/sport";

import type { Profile, Role } from "./types";

export const roleName = (sport: Sport, role: Role) =>
  role === "bat" ? "Batting" : WORDS[sport].bowling;

export function SkillProfile({ sport, profiles }: { sport: Sport; profiles: Profile[] }) {
  return (
    <section>
      <h2 className="label">Skill profile</h2>
      <div className="panel">
        {profiles.length === 0 && <p className="empty">Not enough games yet for a profile.</p>}
        {profiles.map((profile) => (
          <div key={`${profile.role}${profile.fmt}`}>
            <p className="kicker">
              {roleName(sport, profile.role)}
              <span className="sep">{profile.fmt}</span>
            </p>
            <SkillBars skills={profile.dims} />
          </div>
        ))}
        <p className="note">
          Each bar is a rank from 0 to 100 against every qualified player in the same format. Red is
          high, blue is low.
        </p>
      </div>
    </section>
  );
}
