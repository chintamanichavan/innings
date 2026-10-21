// Follow and share, which sit under a team's name. Following lives on the device.

"use client";

import { FollowButton, ShareButton } from "@/components/controls";
import type { Sport } from "@/lib/sport";
import { followedTeams, toggleTeam } from "@/lib/store";

interface ActionsProps {
  sport: Sport;
  team: string; // as written in the address, which is how it is followed
  pool: string;
  title: string;
}

export function Actions({ sport, team, pool, title }: ActionsProps) {
  const isFollowing = () => followedTeams().some((item) => item.sport === sport && item.team === team);
  return (
    <p className="row spaced">
      <FollowButton isFollowing={isFollowing} toggle={() => toggleTeam({ sport, team, pool })} />
      <ShareButton title={title} />
    </p>
  );
}
